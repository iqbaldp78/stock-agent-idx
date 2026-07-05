#!/usr/bin/env python3
"""
Train ML Day-1 Predictor.
Mengambil OHLCV historis, membuat fitur/target T+1 secara per-ticker,
melatih LightGBM, lalu menyimpan model ke path yang dipakai workflow utama:
models/checkpoints/lgbm_day1.pkl + meta JSON.

Usage:
    python scripts/train_day1_model.py --all
    python scripts/train_day1_model.py --tickers BBCA BMRI TLKM
    python scripts/train_day1_model.py --all --period 5y --min-rows 120
"""
import argparse
import json
import logging
import os
import sys
from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

from data.ml_features import prepare_training_data
from models.day1_predictor import Day1Predictor


def get_universe_tickers() -> list[str]:
    from config import get_universe
    return get_universe()


def fetch_ohlcv(ticker: str, period: str) -> pd.DataFrame:
    """Ambil OHLCV historis panjang dari Stockbit/yfinance fallback."""
    try:
        from data.fetcher_stockbit import get_ohlcv
        df = get_ohlcv(ticker, period=period)
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


def _pick_buy_threshold(y_true: np.ndarray, y_pred: np.ndarray, min_precision: float = 0.25) -> float:
    """
    Pilih threshold yang memaksimalkan F1 sinyal BUY, dengan batas minimum precision.
    Default fallback: 0.003 jika tidak ada kandidat memenuhi syarat.
    """
    candidates = []
    for thr in np.linspace(0.0005, 0.014, 30):
        pred_buy = y_pred >= thr
        actual_up = y_true > 0
        tp = int((pred_buy & actual_up).sum())
        fp = int((pred_buy & ~actual_up).sum())
        fn = int((~pred_buy & actual_up).sum())
        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        if precision >= min_precision:
            f1 = tp / (tp + 0.5 * (fp + fn)) if (tp + 0.5 * (fp + fn)) else 0.0
            candidates.append((f1, precision, recall, thr))
    if not candidates:
        return 0.003
    candidates.sort(reverse=True)
    return float(candidates[0][3])


def main():
    parser = argparse.ArgumentParser(description="Train ML Day-1 Predictor")
    parser.add_argument("--tickers", nargs="+", help="Ticker(s), e.g. BBCA BMRI")
    parser.add_argument("--all", action="store_true", help="Semua ticker di universe")
    parser.add_argument("--period", default=os.getenv("ML_AUTO_TRAIN_PERIOD", "5y"), help="Periode OHLCV historis (default: env/5y)")
    parser.add_argument("--min-rows", type=int, default=120, help="Minimum training rows per ticker")
    parser.add_argument("--test-size", type=float, default=0.2, help="Holdout ratio per ticker (default: 0.2)")
    parser.add_argument("--model-dir", default="models/checkpoints", help="Direktori model output")
    parser.add_argument(
        "--target",
        default="target_1d",
        help="Target horizon model (default: target_1d)",
    )
    args = parser.parse_args()

    if not 0 < args.test_size < 0.5:
        raise SystemExit("--test-size harus di antara 0 dan 0.5")

    tickers = get_universe_tickers() if args.all else [t.upper() for t in args.tickers]
    logger.info(f"Training universe: {len(tickers)} ticker(s): {', '.join(tickers)}")

    os.makedirs(args.model_dir, exist_ok=True)

    metrics_list = []
    errors_list = []

    for ticker in tickers:
        logger.info(f"📊 {ticker} — loading OHLCV ({args.period})...")
        raw = fetch_ohlcv(ticker, period=args.period)
        ohlcv = normalize_ohlcv(raw)

        if ohlcv.empty:
            errors_list.append({"ticker": ticker, "error": "No OHLCV data"})
            logger.warning(f"  {ticker}: no OHLCV data")
            continue

        try:
            X, y = prepare_training_data(ohlcv, ticker=ticker)
        except Exception as e:
            errors_list.append({"ticker": ticker, "error": f"prepare_training_data failed: {e}"})
            logger.warning(f"  {ticker}: feature prep failed: {e}")
            continue

        if len(X) < args.min_rows:
            errors_list.append({"ticker": ticker, "error": f"Training rows terlalu sedikit ({len(X)} < {args.min_rows})"})
            logger.warning(f"  {ticker}: rows too small ({len(X)} < {args.min_rows})")
            continue

        if isinstance(y, pd.DataFrame):
            if args.target in y.columns:
                y = y[args.target]
            else:
                y = y.iloc[:, 0]

        split = max(1, int(len(X) * (1 - args.test_size)))
        X_train, X_test = X.iloc[:split], X.iloc[split:]
        y_train, y_test = y.iloc[:split], y.iloc[split:]

        if len(X_test) < 5:
            errors_list.append({"ticker": ticker, "error": "Holdout too small"})
            logger.warning(f"  {ticker}: holdout too small")
            continue

        model_path = os.path.join(args.model_dir, f"lgbm_{ticker.lower()}.pkl")
        predictor = Day1Predictor(model_path=model_path, target_col=args.target)
        predictor.model = None
        predictor.train_incremental(X_train, y_train)

        if predictor.model is None:
            errors_list.append({"ticker": ticker, "error": "train_incremental returned None"})
            logger.warning(f"  {ticker}: training failed")
            continue

        preds = predictor.model.predict(X_test[predictor.feature_cols].fillna(0.0))
        actuals = y_test.values

        # ── Dynamic buy threshold ────────────────────────────────────────
        # Pilih threshold yang memaksimalkan F1 sinyal BUY dari validation set
        buy_threshold = _pick_buy_threshold(actuals, preds)
        buy_prec, buy_rec = precision_recall_buy(actuals, preds, threshold=buy_threshold)

        # Save threshold for inference
        threshold_path = os.path.join(args.model_dir, f"lgbm_{ticker.lower()}_threshold.json")
        try:
            with open(threshold_path, "w") as f:
                json.dump({"buy_threshold": float(buy_threshold)}, f)
        except Exception as e:
            logger.warning(f"Failed to save threshold for {ticker}: {e}")

        da = directional_accuracy(actuals, preds)
        mae_val = mae(actuals, preds)

        metrics_list.append({
            "ticker": ticker,
            "train_rows": int(len(X_train)),
            "test_rows": int(len(X_test)),
            "directional_accuracy": round(da * 100, 2),
            "mae_pct": round(mae_val * 100, 4),
            "buy_precision": round(buy_prec * 100, 2),
            "buy_recall": round(buy_rec * 100, 2),
            "buy_threshold_pct": round(float(buy_threshold) * 100, 4),
            "avg_pred_return_pct": round(float(np.mean(preds)) * 100, 4),
            "avg_actual_return_pct": round(float(np.mean(actuals)) * 100, 4),
        })

        logger.info(
            f"  ✅ {ticker}: DirAcc={da*100:.1f}% MAE={mae_val*100:.3f}% "
            f"Prec={buy_prec*100:.1f}% Rec={buy_rec*100:.1f}% thr={buy_threshold*100:.3f}%"
        )

    print()
    print("=" * 72)
    print("  ML DAY-1 TRAINING SUMMARY")
    print("=" * 72)
    print(f"Trained tickers : {len(metrics_list)} / {len(tickers)}")
    print(f"Model directory : {args.model_dir}")
    print("-" * 72)
    if metrics_list:
        header = f"{'Ticker':<8} {'DirAcc':>8} {'MAE%':>8} {'BuyPrec':>9} {'BuyRec':>8} {'Train':>7}"
        print(header)
        print("-" * 72)
        for m in sorted(metrics_list, key=lambda x: -x["directional_accuracy"]):
            da_icon = "✅" if m["directional_accuracy"] >= 55 else "⚠️ " if m["directional_accuracy"] >= 50 else "❌"
            print(
                f"{m['ticker']:<8} {m['directional_accuracy']:>7.1f}% {m['mae_pct']:>7.3f}% "
                f"{m['buy_precision']:>8.1f}% {m['buy_recall']:>7.1f}% {m['train_rows']:>7}  {da_icon}"
            )
        print("-" * 72)
        avg_da = float(np.mean([m["directional_accuracy"] for m in metrics_list]))
        avg_mae = float(np.mean([m["mae_pct"] for m in metrics_list]))
        avg_prec = float(np.mean([m["buy_precision"] for m in metrics_list]))
        print(f"{'AVERAGE':<8} {avg_da:>7.1f}% {avg_mae:>7.3f}% {avg_prec:>8.1f}%")
        print()
        print("  DirAcc ≥55% ✅ | 50-55% ⚠️  | <50% ❌ (random = 50%)")
    else:
        print("  Tidak ada ticker yang berhasil dilatih.")

    if errors_list:
        print()
        print("  Errors:")
        for err in errors_list:
            print(f"    - {err['ticker']}: {err['error']}")

    print("=" * 72)


if __name__ == "__main__":
    main()
