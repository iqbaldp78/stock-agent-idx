#!/usr/bin/env python3
"""
Train/validate pooled ML Multi-Day Predictor for selected low-sample/outlier tickers.

Purpose (Fase 2 Track B):
- Keep existing per-ticker MultiDayPredictor intact as fallback.
- Train one pooled model per horizon over multiple tickers.
- Include ticker_id as a categorical-ish numeric feature so the model can learn ticker-specific offsets.

Usage:
    python scripts/train_multiday_pooled_model.py --tickers PADI BNBR BIPI --validate-only --walk-forward --n-folds 4
"""
import argparse
import json
import logging
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config  # noqa: F401
import numpy as np
import pandas as pd

from data.ml_features import ML_TRAIN_FEATURES, prepare_training_data
from models.multiday_predictor import MultiDayPredictor
from scripts.train_day1_model import fetch_ohlcv, normalize_ohlcv
from scripts.train_multiday_model import evaluate_multiday_model

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger(__name__)

POOLED_FEATURES = ["ticker_id"] + [c for c in ML_TRAIN_FEATURES if c != "ticker_id"]
HORIZONS = ["1d", "3d", "5d", "7d"]


def make_pooled_predictor(name: str, checkpoints_dir: str) -> MultiDayPredictor:
    predictor = MultiDayPredictor(ticker=name, checkpoints_dir=checkpoints_dir)
    predictor.feature_cols = POOLED_FEATURES
    predictor.selected_features = {h: POOLED_FEATURES for h in predictor.horizons}
    return predictor


def load_dataset(ticker: str, period: str):
    raw = fetch_ohlcv(ticker, period)
    ohlcv = normalize_ohlcv(raw)
    if ohlcv.empty:
        raise ValueError("No OHLCV data")
    X, Y = prepare_training_data(ohlcv, ticker=ticker)
    return ohlcv, X, Y


def aggregate_metrics(ticker_summaries):
    out = {}
    for h in HORIZONS:
        vals = [s["metrics"][h] for s in ticker_summaries if h in s.get("metrics", {})]
        if not vals:
            continue
        total_rows = sum(v["test_rows"] for v in vals)
        def weighted(key):
            return round(sum(v[key] * v["test_rows"] for v in vals) / total_rows, 2) if total_rows else 0.0
        acc = [v["accuracy"] for v in vals]
        prec = [v["buy_precision"] for v in vals]
        rec = [v["buy_recall"] for v in vals]
        out[h] = {
            "test_rows": total_rows,
            "accuracy": round(float(np.mean(acc)), 2),
            "buy_precision": round(float(np.mean(prec)), 2),
            "buy_recall": round(float(np.mean(rec)), 2),
            "accuracy_weighted": weighted("accuracy"),
            "buy_precision_weighted": weighted("buy_precision"),
            "buy_recall_weighted": weighted("buy_recall"),
            "p10_buy_precision": round(float(np.percentile(prec, 10)), 2),
            "p50_buy_precision": round(float(np.percentile(prec, 50)), 2),
            "p90_buy_precision": round(float(np.percentile(prec, 90)), 2),
        }
    return out


def evaluate_by_ticker(predictor, test_sets):
    summaries = []
    for ticker, payload in test_sets.items():
        X_test = payload["X_test"]
        Y_test = payload["Y_test"]
        metrics = evaluate_multiday_model(predictor, X_test, Y_test)
        summaries.append({
            "ticker": ticker,
            "test_rows": int(len(X_test)),
            "metrics": metrics,
        })
    return summaries


def single_holdout_validate(datasets, test_size, checkpoints_dir, validate_only):
    train_X, train_Y = [], []
    test_sets = {}
    for ticker, payload in datasets.items():
        X, Y = payload["X"], payload["Y"]
        split_i = max(1, min(int(len(X) * (1 - test_size)), len(X) - 1))
        train_X.append(X.iloc[:split_i].copy())
        train_Y.append(Y.iloc[:split_i].copy())
        test_sets[ticker] = {"X_test": X.iloc[split_i:].copy(), "Y_test": Y.iloc[split_i:].copy()}

    predictor = make_pooled_predictor("POOLED_SMALLCAP", checkpoints_dir)
    predictor.train_incremental(pd.concat(train_X), pd.concat(train_Y),
                                X_val=pd.concat([v["X_test"] for v in test_sets.values()]),
                                Y_targets_val=pd.concat([v["Y_test"] for v in test_sets.values()]))
    ticker_summaries = evaluate_by_ticker(predictor, test_sets)
    return ticker_summaries


def walk_forward_validate(datasets, n_folds, checkpoints_dir, validate_only):
    # Accumulate per-ticker fold metrics, then average across folds per ticker/horizon.
    ticker_fold_metrics = {ticker: {h: [] for h in HORIZONS} for ticker in datasets}

    for fold_idx in range(n_folds):
        train_X, train_Y = [], []
        test_sets = {}
        for ticker, payload in datasets.items():
            X, Y = payload["X"], payload["Y"]
            fold_size = len(X) // (n_folds + 1)
            train_end = fold_size * (fold_idx + 1)
            test_end = min(fold_size * (fold_idx + 2), len(X))
            if test_end <= train_end or train_end < 120:
                continue
            train_X.append(X.iloc[:train_end].copy())
            train_Y.append(Y.iloc[:train_end].copy())
            test_sets[ticker] = {"X_test": X.iloc[train_end:test_end].copy(), "Y_test": Y.iloc[train_end:test_end].copy()}

        if not train_X or not test_sets:
            logger.warning("Fold %s skipped: insufficient data", fold_idx)
            continue

        predictor = make_pooled_predictor(f"POOLED_SMALLCAP_WF_F{fold_idx}", checkpoints_dir)
        predictor.train_incremental(pd.concat(train_X), pd.concat(train_Y),
                                    X_val=pd.concat([v["X_test"] for v in test_sets.values()]),
                                    Y_targets_val=pd.concat([v["Y_test"] for v in test_sets.values()]))
        fold_summaries = evaluate_by_ticker(predictor, test_sets)
        for s in fold_summaries:
            ticker = s["ticker"]
            for h, metrics in s.get("metrics", {}).items():
                ticker_fold_metrics[ticker][h].append(metrics)

    ticker_summaries = []
    for ticker, hmap in ticker_fold_metrics.items():
        metrics_out = {}
        total_test_rows = 0
        for h, rows in hmap.items():
            if not rows:
                continue
            total_test_rows += sum(r["test_rows"] for r in rows)
            metrics_out[h] = {
                "test_rows": sum(r["test_rows"] for r in rows),
                "accuracy": round(float(np.mean([r["accuracy"] for r in rows])), 2),
                "buy_precision": round(float(np.mean([r["buy_precision"] for r in rows])), 2),
                "buy_recall": round(float(np.mean([r["buy_recall"] for r in rows])), 2),
                "n_folds_evaluated": len(rows),
            }
        ticker_summaries.append({"ticker": ticker, "test_rows": total_test_rows, "metrics": metrics_out})
    return ticker_summaries


def main():
    parser = argparse.ArgumentParser(description="Train pooled ML Multi-Day Predictor")
    parser.add_argument("--tickers", nargs="+", required=True, help="Tickers to pool, e.g. PADI BNBR BIPI")
    parser.add_argument("--period", default=os.getenv("ML_AUTO_TRAIN_PERIOD", "max"))
    parser.add_argument("--checkpoints-dir", default="models/checkpoints_pooled")
    parser.add_argument("--metadata-output", default="models/checkpoints_pooled/lgbm_multiday_pooled_meta.json")
    parser.add_argument("--test-size", type=float, default=0.2)
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--walk-forward", action="store_true")
    parser.add_argument("--n-folds", type=int, default=4)
    args = parser.parse_args()

    tickers = [t.upper() for t in args.tickers]
    datasets = {}
    errors = []
    for ticker in tickers:
        try:
            ohlcv, X, Y = load_dataset(ticker, args.period)
            datasets[ticker] = {"ohlcv_rows": len(ohlcv), "X": X, "Y": Y}
            logger.info("Loaded %s: ohlcv=%s, training_rows=%s", ticker, len(ohlcv), len(X))
        except Exception as e:
            logger.warning("%s skipped: %s", ticker, e)
            errors.append({"ticker": ticker, "error": str(e)})

    if not datasets:
        raise SystemExit("No pooled datasets available")

    if args.walk_forward:
        ticker_summaries = walk_forward_validate(datasets, args.n_folds, args.checkpoints_dir, args.validate_only)
    else:
        ticker_summaries = single_holdout_validate(datasets, args.test_size, args.checkpoints_dir, args.validate_only)

    metrics = aggregate_metrics(ticker_summaries)
    metadata = {
        "run_date": datetime.now().isoformat(),
        "model_type": "pooled_smallcap",
        "tickers": tickers,
        "checkpoints_dir": args.checkpoints_dir,
        "config": {
            "period": args.period,
            "test_size": args.test_size,
            "validate_only": args.validate_only,
            "walk_forward": args.walk_forward,
            "n_folds": args.n_folds,
            "features": POOLED_FEATURES,
        },
        "rows": {
            "tickers_requested": len(tickers),
            "tickers_loaded": len(datasets),
            "total_training_rows": sum(len(v["X"]) for v in datasets.values()),
            "total_test_rows": sum(s.get("test_rows", 0) for s in ticker_summaries),
        },
        "holdout_metrics_macro_avg": metrics,
        "holdout_metrics_weighted_avg": metrics,
        "ticker_metrics": ticker_summaries,
        "errors": errors,
    }

    if args.validate_only:
        out_path = args.metadata_output.replace(".json", "_val.json")
    else:
        out_path = args.metadata_output
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 72)
    print("  POOLED SMALLCAP MULTI-DAY VALIDATION SUMMARY")
    print("=" * 72)
    print(f"Tickers pooled : {', '.join(tickers)}")
    print(f"Tickers loaded : {len(datasets)} / {len(tickers)}")
    print(f"Metadata       : {out_path}")
    print("-" * 72)
    for h, m in metrics.items():
        print(f"Horizon [{h.upper()}]: rows={m['test_rows']} acc={m['accuracy']:.2f}% prec={m['buy_precision']:.2f}% recall={m['buy_recall']:.2f}%")
    print("=" * 72)


if __name__ == "__main__":
    main()
