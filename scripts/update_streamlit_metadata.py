#!/usr/bin/env python3
import os
import sys
import json
import logging
from datetime import datetime
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.train_day1_model import get_universe_tickers, fetch_ohlcv, normalize_ohlcv
from data.ml_features import prepare_training_data
from models.multiday_predictor import MultiDayPredictor

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

def main():
    tickers = get_universe_tickers()
    checkpoints_dir = "models/checkpoints"
    metadata_output = os.path.join(checkpoints_dir, "lgbm_multiday_meta.json")

    summaries = []
    errors = []

    for ticker in tickers:
        raw = fetch_ohlcv(ticker, "5y")
        ohlcv = normalize_ohlcv(raw)
        if ohlcv.empty:
            errors.append({"ticker": ticker, "error": "No OHLCV data"})
            continue

        try:
            X, Y = prepare_training_data(ohlcv, ticker=ticker)
        except Exception as e:
            errors.append({"ticker": ticker, "error": f"prepare_training_data failed: {e}"})
            continue

        if len(X) < 120:
            errors.append({"ticker": ticker, "error": "Rows too small"})
            continue

        # Holdout split 80% train / 20% test
        split_i = max(1, min(int(len(X) * 0.8), len(X) - 1))
        X_test = X.iloc[split_i:]
        Y_test = Y.iloc[split_i:]

        predictor = MultiDayPredictor(ticker=ticker, checkpoints_dir=checkpoints_dir)
        
        metrics = {}
        for h in predictor.horizons:
            model = predictor.models.get(h)
            col_name = f"target_{h}"
            if model is None or col_name not in Y_test.columns:
                continue
            
            y_true_raw = Y_test[col_name]
            valid_idx = ~y_true_raw.isna()
            if not valid_idx.any():
                continue

            y_true = y_true_raw[valid_idx].values
            X_valid = X_test[valid_idx]

            try:
                model_cols = model.feature_name() if hasattr(model, "feature_name") else predictor.feature_cols
                X_aligned = X_valid.reindex(columns=model_cols, fill_value=0.0).fillna(0.0)
                preds = model.predict(X_aligned)
            except Exception as e:
                continue

            # FIXED (Fase 0.3): Baca threshold hasil training, bukan hardcode 0.55
            buy_threshold = predictor.thresholds.get(h, 0.55)
            binary_preds = (preds >= buy_threshold).astype(int)
            y_true_int = y_true.astype(int)

            acc = float(np.mean(binary_preds == y_true_int))
            true_positives = int(np.sum((binary_preds == 1) & (y_true_int == 1)))
            predicted_positives = int(np.sum(binary_preds == 1))
            actual_positives = int(np.sum(y_true_int == 1))

            prec = float(true_positives / predicted_positives) if predicted_positives > 0 else 0.0
            rec = float(true_positives / actual_positives) if actual_positives > 0 else 0.0

            metrics[h] = {
                "test_rows": int(len(y_true)),
                "accuracy": round(acc * 100, 2),
                "buy_precision": round(prec * 100, 2),
                "buy_recall": round(rec * 100, 2),
            }

        summaries.append({
            "ticker": ticker,
            "ohlcv_rows": len(ohlcv),
            "training_rows": len(X),
            "train_rows": split_i,
            "test_rows": len(X_test),
            "metrics": metrics,
        })

    horizons = ["1d", "3d", "5d", "7d"]
    global_metrics = {}
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
        "checkpoints_dir": checkpoints_dir,
        "config": {
            "period": "5y",
            "min_rows": 120,
            "test_size": 0.2,
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

    with open(metadata_output, "w") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    print(f"SUCCESS: Updated Streamlit metadata file at {metadata_output}")

if __name__ == "__main__":
    main()
