#!/usr/bin/env python3
"""
Train ML Day-1 Predictor.

Mengambil OHLCV historis, membuat fitur/target T+1, melatih LightGBM,
lalu menyimpan model ke path yang dipakai workflow utama:
models/checkpoints/lgbm_day1.pkl

Usage:
    python scripts/train_day1_model.py --all
    python scripts/train_day1_model.py --tickers BBCA BMRI TLKM
    python scripts/train_day1_model.py --all --period 1y --min-rows 120
"""
import argparse
import json
import logging
import os
import sys
from datetime import datetime

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def get_universe_tickers() -> list[str]:
    """Ambil daftar ticker dari DB universe, fallback ke LQ45 subset."""
    try:
        from db import SessionLocal
        from db.models import Universe

        db = SessionLocal()
        rows = db.query(Universe.ticker).filter(Universe.active == True).all()
        db.close()
        tickers = [r.ticker for r in rows]
        if tickers:
            return tickers
    except Exception as e:
        logger.warning(f"Tidak bisa ambil universe dari DB: {e}")

    return [
        "BBCA", "BBRI", "BMRI", "TLKM", "ASII",
        "UNVR", "ICBP", "KLBF", "ANTM", "INDF",
    ]


def fetch_ohlcv(ticker: str, period: str) -> pd.DataFrame:
    """Ambil OHLCV historis panjang dari Stockbit range, fallback ke yfinance."""
    try:
        from data.fetcher_stockbit import get_ohlcv, get_ohlcv_range

        if period in {"1mo", "3mo", "6mo", "1y"}:
            df = get_ohlcv(ticker, period=period)
        else:
            from db.cache import _period_to_dates

            start_date, end_date = _period_to_dates(period)
            df = get_ohlcv_range(ticker, start_date, end_date)
        if df is not None and not df.empty:
            return df
    except Exception as e:
        logger.debug(f"Stockbit OHLCV failed for {ticker}: {e}")

    try:
        from data.fetcher_yfinance import get_ohlcv

        df = get_ohlcv(ticker, period=period)
        if df is not None and not df.empty:
            return df
    except Exception as e:
        logger.debug(f"yfinance cached fetcher failed for {ticker}: {e}")

    try:
        import yfinance as yf

        df = yf.download(f"{ticker}.JK", period=period, auto_adjust=True, progress=False)
        if df is not None and not df.empty:
            return df
    except Exception as e:
        logger.warning(f"yfinance fallback failed for {ticker}: {e}")

    return pd.DataFrame()


def normalize_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()

    out = df.copy()
    out.columns = [str(c).title() for c in out.columns]
    required = ["Open", "High", "Low", "Close", "Volume"]
    for col in required:
        if col not in out.columns:
            return pd.DataFrame()
        out[col] = pd.to_numeric(out[col], errors="coerce")

    out = out.dropna(subset=required).sort_index()
    return out


def directional_accuracy(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    if len(y_true) == 0:
        return 0.0
    return float(((y_true > 0) == (y_pred > 0)).mean())


def mae(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    if len(y_true) == 0:
        return 0.0
    return float(np.mean(np.abs(y_true - y_pred)))


def precision_recall_buy(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    threshold: float = 0.003,
) -> tuple[float, float]:
    pred_buy = y_pred >= threshold
    actual_up = y_true > 0
    tp = int((pred_buy & actual_up).sum())
    fp = int((pred_buy & ~actual_up).sum())
    fn = int((~pred_buy & actual_up).sum())

    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    return float(precision), float(recall)


def build_dataset(
    tickers: list[str],
    period: str,
    min_rows: int,
    test_size: float,
) -> tuple[pd.DataFrame, pd.Series, pd.DataFrame, pd.Series, pd.DataFrame, pd.Series, list[dict], list[dict]]:
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
            X, y = prepare_training_data(ohlcv)
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
        y_train = y.iloc[:split_i].copy()
        X_test = X.iloc[split_i:].copy()
        y_test = y.iloc[split_i:].copy()

        train_x_parts.append(X_train)
        train_y_parts.append(y_train)
        test_x_parts.append(X_test)
        test_y_parts.append(y_test)
        all_x_parts.append(X)
        all_y_parts.append(y)

        summaries.append({
            "ticker": ticker,
            "ohlcv_rows": len(ohlcv),
            "training_rows": len(X),
            "train_rows": len(X_train),
            "test_rows": len(X_test),
        })
        logger.info(f"  rows={len(X)} train={len(X_train)} test={len(X_test)}")

    if not all_x_parts:
        empty_x = pd.DataFrame()
        empty_y = pd.Series(dtype=float)
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


def evaluate_model(model, X_test: pd.DataFrame, y_test: pd.Series, feature_cols: list[str]) -> dict:
    if model is None or X_test.empty:
        return {
            "test_rows": 0,
            "directional_accuracy": 0.0,
            "mae_pct": 0.0,
            "buy_precision": 0.0,
            "buy_recall": 0.0,
        }

    preds = model.predict(X_test[feature_cols].fillna(0.0))
    actuals = y_test.values
    buy_prec, buy_rec = precision_recall_buy(actuals, preds)

    return {
        "test_rows": int(len(y_test)),
        "directional_accuracy": round(directional_accuracy(actuals, preds) * 100, 2),
        "mae_pct": round(mae(actuals, preds) * 100, 4),
        "buy_precision": round(buy_prec * 100, 2),
        "buy_recall": round(buy_rec * 100, 2),
        "avg_pred_return_pct": round(float(np.mean(preds)) * 100, 4),
        "avg_actual_return_pct": round(float(np.mean(actuals)) * 100, 4),
    }


def main():
    parser = argparse.ArgumentParser(description="Train ML Day-1 Predictor")
    grp = parser.add_mutually_exclusive_group(required=True)
    grp.add_argument("--tickers", nargs="+", help="Ticker(s), e.g. BBCA BMRI")
    grp.add_argument("--all", action="store_true", help="Semua ticker di universe")
    parser.add_argument("--period", default="1y", help="Periode OHLCV historis (default: 1y)")
    parser.add_argument("--min-rows", type=int, default=120, help="Minimum training rows per ticker")
    parser.add_argument("--test-size", type=float, default=0.2, help="Holdout ratio per ticker (default: 0.2)")
    parser.add_argument("--model-path", default="models/checkpoints/lgbm_day1.pkl", help="Output model path")
    parser.add_argument("--metadata-output", default="models/checkpoints/lgbm_day1_meta.json", help="Output metadata JSON")
    parser.add_argument(
        "--min-dir-acc",
        type=float,
        default=50.0,
        help="Minimum holdout directional accuracy untuk menyimpan model aktif (default: 50.0)",
    )
    parser.add_argument(
        "--force-save",
        action="store_true",
        help="Tetap simpan model walaupun holdout directional accuracy di bawah threshold.",
    )
    parser.add_argument(
        "--save-holdout-model",
        action="store_true",
        help="Simpan model yang dilatih hanya dari train split. Default: retrain final model dengan semua data.",
    )
    args = parser.parse_args()

    if not 0 < args.test_size < 0.5:
        raise SystemExit("--test-size harus di antara 0 dan 0.5")

    tickers = get_universe_tickers() if args.all else [t.upper() for t in args.tickers]
    logger.info(f"Training universe: {len(tickers)} ticker(s): {', '.join(tickers)}")

    X_train, y_train, X_test, y_test, X_all, y_all, ticker_summaries, errors = build_dataset(
        tickers=tickers,
        period=args.period,
        min_rows=args.min_rows,
        test_size=args.test_size,
    )

    if X_train.empty or X_all.empty:
        raise SystemExit("Tidak ada data training yang valid.")

    from models.day1_predictor import Day1Predictor

    logger.info(f"Training holdout model: train_rows={len(X_train)} test_rows={len(X_test)}")
    holdout_model_path = "/tmp/lgbm_day1_train_holdout.pkl"
    holdout_predictor = Day1Predictor(model_path=holdout_model_path)
    holdout_predictor.model = None
    holdout_predictor.train_incremental(X_train, y_train)
    holdout_metrics = evaluate_model(
        holdout_predictor.model,
        X_test,
        y_test,
        holdout_predictor.feature_cols,
    )

    model_passed_gate = holdout_metrics["directional_accuracy"] >= args.min_dir_acc
    model_saved = False
    final_train_rows = 0

    if not model_passed_gate and not args.force_save:
        logger.warning(
            "Model tidak disimpan: holdout directional accuracy %.2f%% < %.2f%%. "
            "Gunakan --force-save jika tetap ingin menyimpan.",
            holdout_metrics["directional_accuracy"],
            args.min_dir_acc,
        )
    elif args.save_holdout_model:
        logger.info(f"Saving holdout-trained model to {args.model_path}")
        final_predictor = Day1Predictor(model_path=args.model_path)
        final_predictor.model = None
        final_predictor.train_incremental(X_train, y_train)
        final_train_rows = len(X_train)
        model_saved = True
    else:
        logger.info(f"Training final model with all rows: rows={len(X_all)}")
        final_predictor = Day1Predictor(model_path=args.model_path)
        final_predictor.model = None
        final_predictor.train_incremental(X_all, y_all)
        final_train_rows = len(X_all)
        model_saved = True

    metadata = {
        "run_date": datetime.now().isoformat(),
        "model_path": args.model_path,
        "model_saved": model_saved,
        "model_passed_gate": model_passed_gate,
        "config": {
            "period": args.period,
            "min_rows": args.min_rows,
            "test_size": args.test_size,
            "min_dir_acc": args.min_dir_acc,
            "force_save": args.force_save,
            "save_holdout_model": args.save_holdout_model,
        },
        "rows": {
            "tickers_requested": len(tickers),
            "tickers_trained": len(ticker_summaries),
            "holdout_train_rows": len(X_train),
            "holdout_test_rows": len(X_test),
            "final_train_rows": final_train_rows,
        },
        "holdout_metrics": holdout_metrics,
        "tickers": ticker_summaries,
        "errors": errors,
    }

    os.makedirs(os.path.dirname(args.metadata_output), exist_ok=True)
    with open(args.metadata_output, "w") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    print()
    print("=" * 72)
    print("  ML DAY-1 TRAINING SUMMARY")
    print("=" * 72)
    print(f"Tickers trained : {len(ticker_summaries)} / {len(tickers)}")
    print(f"Final rows      : {final_train_rows}")
    print(f"Model saved     : {model_saved}")
    print(f"Model path      : {args.model_path}")
    print(f"Metadata        : {args.metadata_output}")
    print("-" * 72)
    print(f"Holdout rows    : {holdout_metrics['test_rows']}")
    print(f"Dir Accuracy    : {holdout_metrics['directional_accuracy']:.2f}%")
    print(f"MAE             : {holdout_metrics['mae_pct']:.4f}%")
    print(f"Buy Precision   : {holdout_metrics['buy_precision']:.2f}%")
    print(f"Buy Recall      : {holdout_metrics['buy_recall']:.2f}%")
    print("=" * 72)


if __name__ == "__main__":
    main()
