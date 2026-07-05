"""
ML Day-1 Accuracy Validator
Walk-forward time-series cross-validation untuk Day1Predictor.

Metrics yang dihitung:
- Directional Accuracy: seberapa sering prediksi arah (naik/turun) benar
- MAE: rata-rata absolute error antara predicted vs actual return
- Precision/Recall untuk sinyal BUY (pred_return >= 0.3%)
- Confusion Matrix (arah: UP vs DOWN)

Usage:
    python scripts/validate_ml_accuracy.py --ticker BBCA
    python scripts/validate_ml_accuracy.py --ticker BBCA BMRI TLKM
    python scripts/validate_ml_accuracy.py --all --folds 3 --min-rows 120
"""
import argparse
import json
import logging
import sys
import os
from datetime import datetime

import numpy as np
import pandas as pd

# Allow running from repo root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.ml_features import prepare_training_data
from models.day1_predictor import Day1Predictor

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _directional_accuracy(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Berapa % prediksi arah (naik/turun) yang benar."""
    correct = ((y_true > 0) == (y_pred > 0)).sum()
    return correct / len(y_true) if len(y_true) > 0 else 0.0


def _mae(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(np.mean(np.abs(y_true - y_pred)))


def _precision_recall_buy(
    y_true: np.ndarray, y_pred: np.ndarray, threshold: float = 0.003
) -> tuple[float, float]:
    """
    Precision & recall untuk sinyal BUY (pred_return >= threshold).
    TP = model prediksi BUY & aktual naik
    FP = model prediksi BUY & aktual turun
    FN = model prediksi HOLD/AVOID & aktual naik
    Threshold 0.003 (0.3%) cocok untuk horizon Day-1.
    """
    pred_buy = y_pred >= threshold
    actual_up = y_true > 0

    tp = (pred_buy & actual_up).sum()
    fp = (pred_buy & ~actual_up).sum()
    fn = (~pred_buy & actual_up).sum()

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    return float(precision), float(recall)


def _confusion_matrix_str(y_true: np.ndarray, y_pred: np.ndarray) -> str:
    """Simple 2x2 confusion matrix string (UP vs DOWN)."""
    tp = ((y_pred > 0) & (y_true > 0)).sum()
    fp = ((y_pred > 0) & (y_true <= 0)).sum()
    fn = ((y_pred <= 0) & (y_true > 0)).sum()
    tn = ((y_pred <= 0) & (y_true <= 0)).sum()
    return (
        f"         Pred UP   Pred DOWN\n"
        f"Actual UP    {tp:5d}     {fn:5d}\n"
        f"Actual DOWN  {fp:5d}     {tn:5d}"
    )


# ─── Walk-forward CV ──────────────────────────────────────────────────────────

def walk_forward_validate_dataset(
    X_all: pd.DataFrame,
    y_all: pd.Series,
    n_folds: int = 5,
    min_train_rows: int = 60,
    target_col: str = "target_1d",
) -> dict:
    """
    Time-series walk-forward cross-validation over a pre-built dataset.
    """
    n = len(X_all)
    if n < min_train_rows + n_folds * 10:
        return {"error": f"Data terlalu sedikit ({n} baris) untuk {n_folds} fold"}

    fold_size = n // (n_folds + 1)
    all_true, all_pred = [], []
    fold_results = []

    for fold in range(n_folds):
        train_end = fold_size * (fold + 1)
        test_start = train_end
        test_end = min(train_end + fold_size, n)

        if train_end < min_train_rows:
            logger.debug(f"Fold {fold+1}: train terlalu kecil ({train_end}), skip")
            continue

        X_train = X_all.iloc[:train_end]
        y_train = y_all.iloc[:train_end]
        X_test = X_all.iloc[test_start:test_end]
        y_test = y_all.iloc[test_start:test_end]

        if len(X_test) < 5:
            continue

        predictor = Day1Predictor(model_path="/tmp/lgbm_val_tmp.pkl", target_col=target_col)
        predictor.model = None
        predictor.train_incremental(X_train, y_train)

        if predictor.model is None:
            continue

        preds = predictor.model.predict(X_test[predictor.feature_cols].fillna(0.0))
        actuals = y_test.values

        dir_acc = _directional_accuracy(actuals, preds)
        mae = _mae(actuals, preds)
        prec, rec = _precision_recall_buy(actuals, preds)

        fold_results.append({
            "fold": fold + 1,
            "train_rows": train_end,
            "test_rows": len(X_test),
            "directional_accuracy": round(dir_acc * 100, 2),
            "mae_pct": round(mae * 100, 4),
            "buy_precision": round(prec * 100, 2),
            "buy_recall": round(rec * 100, 2),
        })

        all_true.extend(actuals.tolist())
        all_pred.extend(preds.tolist())

        logger.info(
            f"  Fold {fold+1}/{n_folds}: "
            f"DirAcc={dir_acc*100:.1f}% MAE={mae*100:.3f}% "
            f"Prec={prec*100:.1f}% Rec={rec*100:.1f}%"
        )

    if not all_true:
        return {"error": "Tidak ada fold yang berhasil"}

    all_true_arr = np.array(all_true)
    all_pred_arr = np.array(all_pred)

    aggregate = {
        "total_test_rows": len(all_true),
        "directional_accuracy": round(_directional_accuracy(all_true_arr, all_pred_arr) * 100, 2),
        "mae_pct": round(_mae(all_true_arr, all_pred_arr) * 100, 4),
        "buy_precision": round(_precision_recall_buy(all_true_arr, all_pred_arr)[0] * 100, 2),
        "buy_recall": round(_precision_recall_buy(all_true_arr, all_pred_arr)[1] * 100, 2),
        "confusion_matrix": _confusion_matrix_str(all_true_arr, all_pred_arr),
    }

    return {
        "folds": fold_results,
        "aggregate": aggregate,
    }


# ─── Ticker list ──────────────────────────────────────────────────────────────

def get_universe_tickers() -> list[str]:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from config import get_universe
    return get_universe()


def fetch_ohlcv(ticker: str, period: str = "max") -> pd.DataFrame:
    """Ambil OHLCV dari Stockbit/yfinance fallback."""
    try:
        from data.fetcher_stockbit import get_ohlcv
        df = get_ohlcv(ticker, period=period)
        if df is not None and not df.empty:
            return df
    except Exception as e:
        logger.debug(f"fetcher_stockbit.get_ohlcv failed for {ticker}: {e}")

    # Fallback yfinance
    try:
        import yfinance as yf
        df = yf.download(f"{ticker}.JK", period=period, auto_adjust=True, progress=False)
        if df is not None and not df.empty:
            return df
    except Exception as e:
        logger.warning(f"yfinance fallback juga gagal untuk {ticker}: {e}")

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


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Validate ML Day-1 Predictor accuracy")
    parser.add_argument("--ticker", nargs="+", metavar="TICKER", help="Ticker(s) spesifik")
    parser.add_argument("--all", action="store_true", help="Semua ticker di universe")
    parser.add_argument("--folds", type=int, default=3, help="Jumlah fold walk-forward (default: 3)")
    parser.add_argument("--min-rows", type=int, default=60, help="Min baris training per fold (default: 60)")
    parser.add_argument("--period", default="max", help="Periode data OHLCV (default: max)")
    parser.add_argument("--target", default="target_1d", help="Target horizon model (default: target_1d)")
    parser.add_argument("--output", default="validate_ml_result.json", help="File output JSON")
    args = parser.parse_args()

    tickers = args.ticker if args.ticker else get_universe_tickers()

    logger.info(f"Validating {len(tickers)} ticker(s): {', '.join(tickers)}")
    logger.info(f"Walk-forward: {args.folds} folds | Min train rows: {args.min_rows} | Period: {args.period}")
    print()

    results = {}
    summary_rows = []

    for ticker in tickers:
        logger.info(f"📊 {ticker} — Fetching OHLCV ({args.period})...")
        raw = fetch_ohlcv(ticker, period=args.period)
        ohlcv = normalize_ohlcv(raw)

        if ohlcv.empty:
            logger.warning(f"  ⚠️  {ticker}: No OHLCV data, skip")
            results[ticker] = {"error": "No OHLCV data"}
            continue

        logger.info(f"  Data: {len(ohlcv)} rows")

        try:
            X, y = prepare_training_data(ohlcv, ticker=ticker)
            if isinstance(y, pd.DataFrame):
                if args.target in y.columns:
                    y = y[args.target]
                else:
                    y = y.iloc[:, 0]
        except Exception as e:
            logger.warning(f"  ⚠️  {ticker}: feature prep failed: {e}")
            results[ticker] = {"error": f"prepare_training_data failed: {e}"}
            continue

        if len(X) < args.min_rows:
            logger.warning(f"  ⚠️  {ticker}: rows too small ({len(X)} < {args.min_rows})")
            results[ticker] = {"error": f"Training rows terlalu sedikit ({len(X)})"}
            continue

        res = walk_forward_validate_dataset(
            X, y, n_folds=args.folds, min_train_rows=args.min_rows, target_col=args.target
        )
        results[ticker] = res

        if "error" in res:
            logger.warning(f"  ⚠️  {ticker}: {res['error']}")
            continue

        agg = res["aggregate"]
        summary_rows.append({
            "ticker": ticker,
            "dir_acc": agg["directional_accuracy"],
            "mae_pct": agg["mae_pct"],
            "buy_prec": agg["buy_precision"],
            "buy_rec": agg["buy_recall"],
            "test_rows": agg["total_test_rows"],
        })

        logger.info(
            f"  ✅ {ticker}: DirAcc={agg['directional_accuracy']:.1f}% "
            f"MAE={agg['mae_pct']:.3f}% Prec={agg['buy_precision']:.1f}% Rec={agg['buy_recall']:.1f}%"
        )

    print()
    print("=" * 72)
    print("  ML DAY-1 PER-TICKER VALIDATION SUMMARY")
    print("=" * 72)
    if summary_rows:
        header = f"{'Ticker':<8} {'DirAcc':>8} {'MAE%':>8} {'BuyPrec':>9} {'BuyRec':>8} {'Rows':>6}"
        print(header)
        print("-" * 72)
        for r in sorted(summary_rows, key=lambda x: -x["dir_acc"]):
            da_icon = "✅" if r["dir_acc"] >= 55 else "⚠️ " if r["dir_acc"] >= 50 else "❌"
            print(
                f"{r['ticker']:<8} {r['dir_acc']:>7.1f}% {r['mae_pct']:>7.3f}% "
                f"{r['buy_prec']:>8.1f}% {r['buy_rec']:>7.1f}% {r['test_rows']:>6}  {da_icon}"
            )
        print("-" * 72)

        avg_da = float(np.mean([r["dir_acc"] for r in summary_rows]))
        avg_mae = float(np.mean([r["mae_pct"] for r in summary_rows]))
        avg_prec = float(np.mean([r["buy_prec"] for r in summary_rows]))
        print(f"{'AVERAGE':<8} {avg_da:>7.1f}% {avg_mae:>7.3f}% {avg_prec:>8.1f}%")
        print()
        print("  DirAcc ≥55% ✅ | 50-55% ⚠️  | <50% ❌ (random = 50%)")
    else:
        print("  Tidak ada ticker yang berhasil divalidasi.")

    print("=" * 72)

    output = {
        "run_date": datetime.now().isoformat(),
        "tickers": results,
        "summary": summary_rows,
        "config": {
            "folds": args.folds,
            "min_rows": args.min_rows,
            "period": args.period,
            "target": args.target,
        },
    }
    with open(args.output, "w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"\n✅ Hasil disimpan ke: {args.output}")


if __name__ == "__main__":
    main()
