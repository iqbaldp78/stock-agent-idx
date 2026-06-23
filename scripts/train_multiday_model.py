#!/usr/bin/env python3
"""
Train ML Multi-Day Predictor (T+1, T+3, T+5, T+7).

Mengambil OHLCV historis, membuat fitur dan target, melatih 4 model LightGBM secara mandiri,
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

def build_multiday_dataset(
    tickers: list[str],
    period: str,
    min_rows: int,
    test_size: float,
):
    from data.ml_features import prepare_training_data

    train_x_parts = []
    train_y_parts = []
    test_x_parts = []
    test_y_parts = []
    all_x_parts = []
    all_y_parts = []
    summaries = []
    errors = []

    for ticker in tickers:
        logger.info(f"📊 {ticker} — loading OHLCV ({period})...")
        raw = fetch_ohlcv(ticker, period)
        ohlcv = normalize_ohlcv(raw)
        if ohlcv.empty:
            errors.append({"ticker": ticker, "error": "No OHLCV data"})
            logger.warning(f"  {ticker}: no OHLCV data")
            continue

        try:
            X, Y = prepare_training_data(ohlcv, ticker=ticker)
        except Exception as e:
            errors.append({"ticker": ticker, "error": f"prepare_training_data failed: {e}"})
            logger.warning(f"  {ticker}: feature prep failed: {e}")
            continue

        if len(X) < min_rows:
            errors.append({"ticker": ticker, "error": f"Training rows terlalu sedikit ({len(X)} < {min_rows})"})
            logger.warning(f"  {ticker}: rows too small ({len(X)} < {min_rows})")
            continue

        split_i = int(len(X) * (1 - test_size))
        split_i = max(1, min(split_i, len(X) - 1))

        X_train = X.iloc[:split_i].copy()
        Y_train = Y.iloc[:split_i].copy()
        X_test = X.iloc[split_i:].copy()
        Y_test = Y.iloc[split_i:].copy()

        train_x_parts.append(X_train)
        train_y_parts.append(Y_train)
        test_x_parts.append(X_test)
        test_y_parts.append(Y_test)
        all_x_parts.append(X)
        all_y_parts.append(Y)

        summaries.append({
            "ticker": ticker,
            "ohlcv_rows": len(ohlcv),
            "training_rows": len(X),
            "train_rows": len(X_train),
            "test_rows": len(X_test),
        })

    if not all_x_parts:
        empty_x = pd.DataFrame()
        empty_y = pd.DataFrame()
        return empty_x, empty_y, empty_x, empty_y, empty_x, empty_y, summaries, errors

    return (
        pd.concat(train_x_parts, ignore_index=True),
        pd.concat(train_y_parts, ignore_index=True),
        pd.concat(test_x_parts, ignore_index=True),
        pd.concat(test_y_parts, ignore_index=True),
        pd.concat(all_x_parts, ignore_index=True),
        pd.concat(all_y_parts, ignore_index=True),
        summaries,
        errors,
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

        preds = model.predict(X_valid[predictor.feature_cols].fillna(0.0))
        buy_prec, buy_rec = precision_recall_buy(y_true, preds)

        results[h] = {
            "test_rows": int(len(y_true)),
            "directional_accuracy": round(directional_accuracy(y_true, preds) * 100, 2),
            "mae_pct": round(mae(y_true, preds) * 100, 4),
            "buy_precision": round(buy_prec * 100, 2),
            "buy_recall": round(buy_rec * 100, 2),
        }
    return results

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

    X_train, Y_train, X_test, Y_test, X_all, Y_all, ticker_summaries, errors = build_multiday_dataset(
        tickers=tickers,
        period=args.period,
        min_rows=args.min_rows,
        test_size=args.test_size,
    )

    if X_train.empty or X_all.empty:
        raise SystemExit("Tidak ada data training yang valid.")

    from models.multiday_predictor import MultiDayPredictor

    logger.info(f"Training holdout models for evaluation: train_rows={len(X_train)} test_rows={len(X_test)}")
    holdout_predictor = MultiDayPredictor(checkpoints_dir="/tmp/checkpoints_holdout")
    holdout_predictor.train_incremental(X_train, Y_train)

    holdout_metrics = evaluate_multiday_model(holdout_predictor, X_test, Y_test)

    logger.info(f"Training final models with all data: rows={len(X_all)}")
    final_predictor = MultiDayPredictor(checkpoints_dir=args.checkpoints_dir)
    final_predictor.train_incremental(X_all, Y_all)

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
            "tickers_trained": len(ticker_summaries),
            "holdout_train_rows": len(X_train),
            "holdout_test_rows": len(X_test),
            "final_train_rows": len(X_all),
        },
        "holdout_metrics": holdout_metrics,
        "tickers": ticker_summaries,
        "errors": errors,
    }

    os.makedirs(os.path.dirname(args.metadata_output), exist_ok=True)
    with open(args.metadata_output, "w") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 72)
    print("  ML MULTI-DAY TRAINING SUMMARY")
    print("=" * 72)
    print(f"Tickers trained : {len(ticker_summaries)} / {len(tickers)}")
    print(f"Final rows      : {len(X_all)}")
    print(f"Models saved to : {args.checkpoints_dir}")
    print(f"Metadata        : {args.metadata_output}")
    print("-" * 72)
    for h, metrics in holdout_metrics.items():
        print(f"Horizon [{h.upper()}]:")
        print(f"  Holdout rows  : {metrics['test_rows']}")
        print(f"  Dir Accuracy  : {metrics['directional_accuracy']:.2f}%")
        print(f"  MAE           : {metrics['mae_pct']:.4f}%")
        print(f"  Buy Precision : {metrics['buy_precision']:.2f}%")
    print("=" * 72)

if __name__ == "__main__":
    main()
