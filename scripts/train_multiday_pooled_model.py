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
from scripts.train_multiday_model import (
    AVG_METRIC_KEYS,
    aggregate_metrics,
    evaluate_multiday_model,
    make_purged_split,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger(__name__)

POOLED_FEATURES = ["ticker_id"] + [c for c in ML_TRAIN_FEATURES if c != "ticker_id"]
HORIZONS = ["1d", "3d", "5d", "7d"]
MIN_TRAIN_ROWS = 120


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
    val_X, val_Y = [], []
    test_sets = {}
    for ticker, payload in datasets.items():
        X, Y = payload["X"], payload["Y"]
        split_i = max(1, min(int(len(X) * (1 - test_size)), len(X) - 1))

        # Carve val dari ekor blok train — test tidak boleh dilihat saat training.
        val_size = max(30, int(split_i * 0.2))
        split = make_purged_split(split_i, MIN_TRAIN_ROWS, val_size)
        if split is None:
            logger.warning("%s dilewati: data kurang untuk split train/val/test", ticker)
            continue
        train_stop, val_start, val_end = split

        train_X.append(X.iloc[:train_stop].copy())
        train_Y.append(Y.iloc[:train_stop].copy())
        val_X.append(X.iloc[val_start:val_end].copy())
        val_Y.append(Y.iloc[val_start:val_end].copy())
        test_sets[ticker] = {"X_test": X.iloc[split_i:].copy(), "Y_test": Y.iloc[split_i:].copy()}

    if not train_X or not test_sets:
        logger.warning("Tidak ada ticker dengan data cukup untuk holdout validate")
        return []

    predictor = make_pooled_predictor("POOLED_SMALLCAP", checkpoints_dir)
    predictor.train_incremental(pd.concat(train_X), pd.concat(train_Y),
                                X_val=pd.concat(val_X),
                                Y_targets_val=pd.concat(val_Y))
    ticker_summaries = evaluate_by_ticker(predictor, test_sets)
    return ticker_summaries


def walk_forward_validate(datasets, n_folds, checkpoints_dir, validate_only):
    # Accumulate per-ticker fold metrics, then average across folds per ticker/horizon.
    ticker_fold_metrics = {ticker: {h: [] for h in HORIZONS} for ticker in datasets}

    for fold_idx in range(n_folds):
        train_X, train_Y = [], []
        val_X, val_Y = [], []
        test_sets = {}
        for ticker, payload in datasets.items():
            X, Y = payload["X"], payload["Y"]
            fold_size = len(X) // (n_folds + 1)
            train_end = fold_size * (fold_idx + 1)
            test_end = min(fold_size * (fold_idx + 2), len(X))
            if test_end <= train_end:
                continue

            # Carve val dari ekor blok train — test tidak boleh dilihat saat training.
            val_size = max(30, int(fold_size * 0.2))
            split = make_purged_split(train_end, MIN_TRAIN_ROWS, val_size)
            if split is None:
                continue
            train_stop, val_start, val_end = split

            train_X.append(X.iloc[:train_stop].copy())
            train_Y.append(Y.iloc[:train_stop].copy())
            val_X.append(X.iloc[val_start:val_end].copy())
            val_Y.append(Y.iloc[val_start:val_end].copy())
            test_sets[ticker] = {"X_test": X.iloc[train_end:test_end].copy(), "Y_test": Y.iloc[train_end:test_end].copy()}

        if not train_X or not test_sets:
            logger.warning("Fold %s skipped: insufficient data", fold_idx)
            continue

        predictor = make_pooled_predictor(f"POOLED_SMALLCAP_WF_F{fold_idx}", checkpoints_dir)
        predictor.train_incremental(pd.concat(train_X), pd.concat(train_Y),
                                    X_val=pd.concat(val_X),
                                    Y_targets_val=pd.concat(val_Y))
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
            merged = {
                "test_rows": sum(r["test_rows"] for r in rows),
                "n_folds_evaluated": len(rows),
                "n_predicted_positive": sum(r.get("n_predicted_positive", 0) for r in rows),
            }
            for key in AVG_METRIC_KEYS:
                vals = [r[key] for r in rows if key in r]
                merged[key] = round(float(np.mean(vals)), 3 if key == "lift" else 2) if vals else 0.0
            merged["degenerate"] = bool(merged["buy_recall"] < 5.0 or merged["buy_recall"] > 95.0)
            metrics_out[h] = merged
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
        # Satu payload per horizon; sudah memuat varian macro (accuracy/buy_*)
        # sekaligus varian weighted (*_weighted) dan percentile.
        "holdout_metrics": metrics,
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
        base = m.get("majority_baseline", 0.0)
        lift = m.get("lift", 0.0)
        print(
            f"Horizon [{h.upper()}]: rows={m['test_rows']} "
            f"acc={m['accuracy']:.2f}% (baseline {base:.2f}%, {m['accuracy'] - base:+.2f} pp) "
            f"prec={m['buy_precision']:.2f}% recall={m['buy_recall']:.2f}% "
            f"lift={lift:.3f} usable={m.get('n_usable', 0)}/degen={m.get('n_degenerate', 0)}"
        )
    print("=" * 72)


if __name__ == "__main__":
    main()
