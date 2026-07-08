#!/usr/bin/env python3
"""
Train ML Multi-Day Predictor (T+1, T+3, T+5, T+7).

Mengambil OHLCV historis, membuat fitur dan target, melatih 4 model LightGBM per-ticker,
lalu menyimpan model ke folder models/checkpoints/.

Usage:
    python scripts/train_multiday_model.py --all
    python scripts/train_multiday_model.py --tickers BBCA BMRI TLKM
"""
import argparse
import json
import logging
import os
import sys
from datetime import datetime

import config  # Load .env variables

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

from scripts.train_day1_model import (
    get_universe_tickers,
    fetch_ohlcv,
    normalize_ohlcv,
    directional_accuracy,
    mae,
    precision_recall_buy
)

def evaluate_multiday_model(predictor, X_test: pd.DataFrame, Y_test: pd.DataFrame) -> dict:
    results = {}
    if X_test.empty:
        return results

    for h in predictor.horizons:
        model = predictor.models.get(h)
        col_name = f'target_{h}'

        if model is None or col_name not in Y_test.columns:
            continue

        y_true_raw = Y_test[col_name]
        valid_idx = ~y_true_raw.isna()

        if not valid_idx.any():
            continue

        y_true = y_true_raw[valid_idx].values
        X_valid = X_test[valid_idx]

        # preds is now probabilities
        preds = model.predict(X_valid[predictor.feature_cols].fillna(0.0))
        
        binary_preds = (preds > 0.5).astype(int)
        y_true_int = y_true.astype(int)
        
        # Manual metrics
        acc = np.mean(binary_preds == y_true_int)
        
        true_positives = np.sum((binary_preds == 1) & (y_true_int == 1))
        predicted_positives = np.sum(binary_preds == 1)
        actual_positives = np.sum(y_true_int == 1)
        
        prec = true_positives / predicted_positives if predicted_positives > 0 else 0.0
        rec = true_positives / actual_positives if actual_positives > 0 else 0.0

        results[h] = {
            "test_rows": int(len(y_true)),
            "accuracy": round(acc * 100, 2),
            "buy_precision": round(prec * 100, 2),
            "buy_recall": round(rec * 100, 2),
        }
    return results

def train_and_evaluate_ticker(ticker, ohlcv, min_rows, test_size, holdout_dir, final_dir):
    from data.ml_features import prepare_training_data
    from models.multiday_predictor import MultiDayPredictor
    
    try:
        X, Y = prepare_training_data(ohlcv, ticker=ticker)
    except Exception as e:
        return None, {"ticker": ticker, "error": f"prepare_training_data failed: {e}"}

    if len(X) < min_rows:
        return None, {"ticker": ticker, "error": f"Training rows terlalu sedikit ({len(X)} < {min_rows})"}

    split_i = int(len(X) * (1 - test_size))
    split_i = max(1, min(split_i, len(X) - 1))

    X_train = X.iloc[:split_i].copy()
    Y_train = Y.iloc[:split_i].copy()
    X_test = X.iloc[split_i:].copy()
    Y_test = Y.iloc[split_i:].copy()

    # Train Holdout (for evaluation)
    holdout_predictor = MultiDayPredictor(ticker=ticker, checkpoints_dir=holdout_dir)
    holdout_predictor.train_incremental(X_train, Y_train, X_val=X_test, Y_targets_val=Y_test)
    holdout_metrics = evaluate_multiday_model(holdout_predictor, X_test, Y_test)

    # Train Final
    final_predictor = MultiDayPredictor(ticker=ticker, checkpoints_dir=final_dir)
    final_predictor.train_incremental(X, Y, X_val=X_test, Y_targets_val=Y_test)
    
    summary = {
        "ticker": ticker,
        "ohlcv_rows": len(ohlcv),
        "training_rows": len(X),
        "train_rows": len(X_train),
        "test_rows": len(X_test),
        "metrics": holdout_metrics
    }
    return summary, None

def main():
    parser = argparse.ArgumentParser(description="Train ML Multi-Day Predictor")
    grp = parser.add_mutually_exclusive_group(required=True)
    grp.add_argument("--tickers", nargs="+", help="Ticker(s), e.g. BBCA BMRI")
    grp.add_argument("--all", action="store_true", help="Semua ticker di universe")
    parser.add_argument("--period", default=os.getenv("ML_AUTO_TRAIN_PERIOD", "1y"), help="Periode OHLCV historis (default: dari env atau 1y)")
    parser.add_argument("--min-rows", type=int, default=120, help="Minimum training rows per ticker")
    parser.add_argument("--test-size", type=float, default=0.2, help="Holdout ratio per ticker (default: 0.2)")
    parser.add_argument("--checkpoints-dir", default="models/checkpoints", help="Output model directory")
    parser.add_argument("--metadata-output", default="models/checkpoints/lgbm_multiday_meta.json", help="Output metadata JSON")
    args = parser.parse_args()

    tickers = get_universe_tickers() if args.all else [t.upper() for t in args.tickers]
    logger.info(f"Training universe: {len(tickers)} ticker(s): {', '.join(tickers)}")

    summaries = []
    errors = []
    holdout_dir = "/tmp/checkpoints_holdout"

    for ticker in tickers:
        logger.info(f"========== Training {ticker} ==========")
        raw = fetch_ohlcv(ticker, args.period)
        ohlcv = normalize_ohlcv(raw)
        if ohlcv.empty:
            errors.append({"ticker": ticker, "error": "No OHLCV data"})
            continue
            
        summary, err = train_and_evaluate_ticker(
            ticker, ohlcv, args.min_rows, args.test_size, holdout_dir, args.checkpoints_dir
        )
        
        if err:
            logger.warning(f"{ticker} skipped: {err['error']}")
            errors.append(err)
        if summary:
            summaries.append(summary)

    if not summaries:
        raise SystemExit("Tidak ada data training yang berhasil diproses.")

    # Aggregate global metrics (macro average)
    global_metrics = {}
    horizons = ['1d', '3d', '5d', '7d']
    
    total_train_rows = sum(s["train_rows"] for s in summaries)
    total_test_rows = sum(s["test_rows"] for s in summaries)
    total_final_rows = sum(s["training_rows"] for s in summaries)
    
    for h in horizons:
        h_metrics = [s["metrics"][h] for s in summaries if h in s["metrics"]]
        if h_metrics:
            global_metrics[h] = {
                "test_rows": sum(m["test_rows"] for m in h_metrics),
                "accuracy": round(sum(m["accuracy"] for m in h_metrics) / len(h_metrics), 2),
                "buy_precision": round(sum(m["buy_precision"] for m in h_metrics) / len(h_metrics), 2),
                "buy_recall": round(sum(m["buy_recall"] for m in h_metrics) / len(h_metrics), 2),
            }

    metadata = {
        "run_date": datetime.now().isoformat(),
        "checkpoints_dir": args.checkpoints_dir,
        "config": {
            "period": args.period,
            "min_rows": args.min_rows,
            "test_size": args.test_size,
        },
        "rows": {
            "tickers_requested": len(tickers),
            "tickers_trained": len(summaries),
            "holdout_train_rows": total_train_rows,
            "holdout_test_rows": total_test_rows,
            "final_train_rows": total_final_rows,
        },
        "holdout_metrics_macro_avg": global_metrics,
        "tickers": summaries,
        "errors": errors,
    }

    os.makedirs(os.path.dirname(args.metadata_output), exist_ok=True)
    with open(args.metadata_output, "w") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 72)
    print("  ML MULTI-DAY PER-TICKER TRAINING SUMMARY")
    print("=" * 72)
    print(f"Tickers trained : {len(summaries)} / {len(tickers)}")
    print(f"Final rows      : {total_final_rows}")
    print(f"Models saved to : {args.checkpoints_dir} (lgbm_<ticker>_<horizon>.pkl)")
    print(f"Metadata        : {args.metadata_output}")
    print("-" * 72)
    print("MACRO AVERAGE ACCURACY (Across all tickers):")
    for h, metrics in global_metrics.items():
        print(f"Horizon [{h.upper()}]:")
        print(f"  Holdout rows  : {metrics['test_rows']}")
        print(f"  Accuracy      : {metrics['accuracy']:.2f}%")
        print(f"  Buy Precision : {metrics['buy_precision']:.2f}%")
    print("=" * 72)

if __name__ == "__main__":
    main()
