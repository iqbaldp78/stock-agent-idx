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

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config  # Load .env variables

import numpy as np
import pandas as pd

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

        selected_cols = predictor.selected_features.get(h, predictor.feature_cols)
        aligned = X_valid.copy()
        for col in selected_cols:
            if col not in aligned.columns:
                aligned[col] = 0.0

        if hasattr(model, "predict_proba"):
            preds = model.predict_proba(aligned[selected_cols].fillna(0.0))[:, 1]
        else:
            preds = model.predict(aligned[selected_cols].fillna(0.0))

        thr = predictor.thresholds.get(h, 0.50)
        binary_preds = (preds >= thr).astype(int)
        y_true_int = y_true.astype(int)

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
            "optimal_threshold": round(thr, 3),
            "n_features": len(selected_cols)
        }
    return results

# Purge gap = horizon terpanjang (7d). Mencegah label overlap antar blok,
# konsisten dengan PurgedTimeSeriesSplit di models/multiday_predictor.py.
# Dapat di-override via --purge-days CLI arg.
GAP_DAYS = 7
MIN_VAL_ROWS = 10  # train_incremental hanya mengkalibrasi kalau val >= 10 baris


def make_purged_split(train_end, min_rows, val_size, gap=GAP_DAYS, trailing_gap=None):
    """
    Bagi data jadi 3 blok kronologis: [train][gap][val][gap][test]

    Val diambil dari EKOR blok train (bukan memotong test), supaya ukuran dan posisi
    blok test tidak berubah — hasil tetap sebanding dengan run sebelumnya, bedanya
    hanya bias leakage-nya hilang.

    train_end   : indeks awal blok test (atau len(X) untuk model final tanpa test).
    trailing_gap: purge antara val dan test. Default = gap. Pakai 0 untuk model final.

    Return (train_stop, val_start, val_end), atau None kalau data tidak cukup.
    """
    tg = gap if trailing_gap is None else trailing_gap
    val_end = train_end - tg
    val_start = max(0, val_end - val_size)
    train_stop = max(0, val_start - gap)
    if train_stop < min_rows or (val_end - val_start) < MIN_VAL_ROWS:
        return None
    return train_stop, val_start, val_end


def find_constant_features(X: pd.DataFrame) -> list:
    """
    Deteksi fitur ML yang variansnya nol di matriks training.

    Fitur konstan otomatis dibuang feature-selection stage-1 (importance == 0),
    jadi ia tidak pernah dipakai model walau terdaftar di ML_TRAIN_FEATURES.
    Ini biasanya gejala bug pipeline (nama kolom tidak cocok, data source kosong,
    fitur cuma diisi saat live inference) — bukan sifat wajar dari fiturnya.
    """
    from data.ml_features import ML_TRAIN_FEATURES

    constant = []
    for col in ML_TRAIN_FEATURES:
        if col not in X.columns:
            constant.append(col)
            continue
        try:
            if X[col].nunique(dropna=False) <= 1:
                constant.append(col)
        except Exception:
            continue
    return constant


def fit_final_model(predictor, X, Y, min_rows):
    """
    Latih model produksi dengan val terpisah yang TIDAK ikut dilatih, supaya
    threshold & kalibrasi yang tersimpan tidak in-sample.
    Konsekuensi: model produksi tidak memakai ~15% baris terakhir.
    """
    val_size = max(30, int(len(X) * 0.15))
    split = make_purged_split(len(X), min_rows, val_size, trailing_gap=0)
    if split is None:
        # Data minim: latih apa adanya, train_incremental akan fallback ke threshold in-sample.
        predictor.train_incremental(X, Y)
        return
    train_stop, val_start, val_end = split
    predictor.train_incremental(
        X.iloc[:train_stop], Y.iloc[:train_stop],
        X_val=X.iloc[val_start:val_end], Y_targets_val=Y.iloc[val_start:val_end],
    )


def walk_forward_evaluate_ticker(ticker, ohlcv, min_rows, n_folds, holdout_dir, final_dir, validate_only=False, purge_days=7):
    """Walk-forward validation dengan expanding train window."""
    from data.ml_features import prepare_training_data
    from models.multiday_predictor import MultiDayPredictor

    try:
        X, Y = prepare_training_data(ohlcv, ticker=ticker)
    except Exception as e:
        return None, {"ticker": ticker, "error": f"prepare_training_data failed: {e}"}

    if len(X) < min_rows:
        return None, {"ticker": ticker, "error": f"Training rows terlalu sedikit ({len(X)} < {min_rows})"}

    constant_features = find_constant_features(X)
    if constant_features:
        logger.warning(
            f"{ticker}: {len(constant_features)} fitur konstan (akan dibuang feature-selection): "
            f"{', '.join(constant_features)}"
        )

    fold_results = {"1d": [], "3d": [], "5d": [], "7d": []}
    fold_row_counts = []
    total_rows = len(X)
    fold_size = total_rows // (n_folds + 1)

    for fold_idx in range(n_folds):
        train_end = fold_size * (fold_idx + 1)
        test_end = min(fold_size * (fold_idx + 2), total_rows)
        if test_end <= train_end:
            continue

        # Carve val dari ekor blok train — test tidak boleh dipakai saat training.
        val_size = max(30, int(fold_size * 0.2))
        split = make_purged_split(train_end, min_rows, val_size, gap=purge_days)
        if split is None:
            logger.debug(f"{ticker} fold {fold_idx} dilewati: data kurang untuk split train/val/test")
            continue
        train_stop, val_start, val_end = split

        X_train = X.iloc[:train_stop].copy()
        Y_train = Y.iloc[:train_stop].copy()
        X_val = X.iloc[val_start:val_end].copy()
        Y_val = Y.iloc[val_start:val_end].copy()
        X_test = X.iloc[train_end:test_end].copy()
        Y_test = Y.iloc[train_end:test_end].copy()
        if X_test.empty:
            continue

        logger.debug(
            f"{ticker} fold {fold_idx}: train 0..{train_stop} ({len(X_train)}) | "
            f"val {val_start}..{val_end} ({len(X_val)}) | test {train_end}..{test_end} ({len(X_test)})"
        )

        fold_predictor = MultiDayPredictor(ticker=f"{ticker}_wf_f{fold_idx}", checkpoints_dir=holdout_dir)
        fold_predictor.train_incremental(X_train, Y_train, X_val=X_val, Y_targets_val=Y_val)
        fold_metrics = evaluate_multiday_model(fold_predictor, X_test, Y_test)
        fold_row_counts.append({"train": len(X_train), "val": len(X_val), "test": len(X_test)})
        for h in ["1d", "3d", "5d", "7d"]:
            if h in fold_metrics:
                fold_results[h].append(fold_metrics[h])

    if not fold_row_counts:
        return None, {
            "ticker": ticker,
            "error": f"Tidak ada fold yang bisa dievaluasi ({len(X)} baris kurang untuk split train/val/test)",
        }

    horizons_avg = {}
    for h in ["1d", "3d", "5d", "7d"]:
        fold_data = fold_results[h]
        if fold_data:
            horizons_avg[h] = {
                "test_rows": sum(m["test_rows"] for m in fold_data),
                "accuracy": round(np.mean([m["accuracy"] for m in fold_data]), 2),
                "buy_precision": round(np.mean([m["buy_precision"] for m in fold_data]), 2),
                "buy_recall": round(np.mean([m["buy_recall"] for m in fold_data]), 2),
                "n_folds_evaluated": len(fold_data),
            }

    if not validate_only:
        final_predictor = MultiDayPredictor(ticker=ticker, checkpoints_dir=final_dir)
        fit_final_model(final_predictor, X, Y, min_rows)

    summary = {
        "ticker": ticker,
        "ohlcv_rows": len(ohlcv),
        "training_rows": len(X),
        # Baris train/val/test sebenarnya (dijumlah lintas fold, bukan lintas horizon).
        "train_rows": sum(f["train"] for f in fold_row_counts),
        "val_rows": sum(f["val"] for f in fold_row_counts),
        "test_rows": sum(f["test"] for f in fold_row_counts),
        "constant_features": constant_features,
        "metrics": horizons_avg,
        "walk_forward": True,
        "n_folds": n_folds,
        "folds_evaluated": len(fold_row_counts),
    }
    return summary, None


def train_and_evaluate_ticker(ticker, ohlcv, min_rows, test_size, holdout_dir, final_dir, validate_only=False):
    from data.ml_features import prepare_training_data
    from models.multiday_predictor import MultiDayPredictor
    
    try:
        X, Y = prepare_training_data(ohlcv, ticker=ticker)
    except Exception as e:
        return None, {"ticker": ticker, "error": f"prepare_training_data failed: {e}"}

    if len(X) < min_rows:
        return None, {"ticker": ticker, "error": f"Training rows terlalu sedikit ({len(X)} < {min_rows})"}

    constant_features = find_constant_features(X)
    if constant_features:
        logger.warning(
            f"{ticker}: {len(constant_features)} fitur konstan (akan dibuang feature-selection): "
            f"{', '.join(constant_features)}"
        )

    split_i = int(len(X) * (1 - test_size))
    split_i = max(1, min(split_i, len(X) - 1))

    # Carve val dari ekor blok train — test hanya dipakai untuk melapor metrik.
    val_size = max(30, int(split_i * 0.2))
    split = make_purged_split(split_i, min_rows, val_size)
    if split is None:
        return None, {"ticker": ticker, "error": "Data tidak cukup untuk split train/val/test"}
    train_stop, val_start, val_end = split

    X_train = X.iloc[:train_stop].copy()
    Y_train = Y.iloc[:train_stop].copy()
    X_val = X.iloc[val_start:val_end].copy()
    Y_val = Y.iloc[val_start:val_end].copy()
    X_test = X.iloc[split_i:].copy()
    Y_test = Y.iloc[split_i:].copy()

    logger.debug(
        f"{ticker}: train 0..{train_stop} ({len(X_train)}) | "
        f"val {val_start}..{val_end} ({len(X_val)}) | test {split_i}..{len(X)} ({len(X_test)})"
    )

    # Train Holdout (for evaluation)
    holdout_predictor = MultiDayPredictor(ticker=ticker, checkpoints_dir=holdout_dir)
    holdout_predictor.train_incremental(X_train, Y_train, X_val=X_val, Y_targets_val=Y_val)
    holdout_metrics = evaluate_multiday_model(holdout_predictor, X_test, Y_test)

    if not validate_only:
        # Train Final
        final_predictor = MultiDayPredictor(ticker=ticker, checkpoints_dir=final_dir)
        fit_final_model(final_predictor, X, Y, min_rows)

    summary = {
        "ticker": ticker,
        "ohlcv_rows": len(ohlcv),
        "training_rows": len(X),
        "train_rows": len(X_train),
        "val_rows": len(X_val),
        "test_rows": len(X_test),
        "constant_features": constant_features,
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
    parser.add_argument("--validate-only", action="store_true", help="Only validate accuracy on holdout, do not save production models")
    parser.add_argument("--walk-forward", action="store_true", help="Use expanding walk-forward validation instead of single holdout split")
    parser.add_argument("--n-folds", type=int, default=4, help="Number of walk-forward folds")
    parser.add_argument("--purge-days", type=int, default=7, help="Purge gap days between train/val/test (default: 7)")
    parser.add_argument("--exclude-tickers", nargs="*", default=[], help="Ticker(s) to exclude from per-ticker training/validation")
    args = parser.parse_args()

    tickers = get_universe_tickers() if args.all else [t.upper() for t in args.tickers]
    excluded = {t.upper() for t in args.exclude_tickers}
    if excluded:
        before_count = len(tickers)
        tickers = [t for t in tickers if t.upper() not in excluded]
        logger.info(f"Excluded {before_count - len(tickers)} ticker(s): {', '.join(sorted(excluded))}")
    logger.info(f"Training universe: {len(tickers)} ticker(s): {', '.join(tickers)}")
    logger.info(f"Purge gap: {args.purge_days} days")

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

        if args.walk_forward:
            summary, err = walk_forward_evaluate_ticker(
                ticker, ohlcv, args.min_rows, args.n_folds, holdout_dir, args.checkpoints_dir, 
                validate_only=args.validate_only, purge_days=args.purge_days
            )
        else:
            summary, err = train_and_evaluate_ticker(
                ticker, ohlcv, args.min_rows, args.test_size, holdout_dir, args.checkpoints_dir, validate_only=args.validate_only
            )

        if err:
            logger.warning(f"{ticker} skipped: {err['error']}")
            errors.append(err)
        if summary:
            summaries.append(summary)

    if not summaries:
        raise SystemExit("Tidak ada data training yang berhasil diproses.")

    def aggregate_metrics(items):
        out = {}
        for h in ['1d', '3d', '5d', '7d']:
            h_metrics = [s["metrics"][h] for s in items if h in s.get("metrics", {})]
            if not h_metrics:
                continue
            total_rows = sum(m["test_rows"] for m in h_metrics)
            weighted = lambda key: round(sum(m[key] * m["test_rows"] for m in h_metrics) / total_rows, 2) if total_rows else 0.0
            acc_vals = [m["accuracy"] for m in h_metrics]
            prec_vals = [m["buy_precision"] for m in h_metrics]
            rec_vals = [m["buy_recall"] for m in h_metrics]
            out[h] = {
                "test_rows": total_rows,
                "accuracy": round(sum(acc_vals) / len(acc_vals), 2),
                "buy_precision": round(sum(prec_vals) / len(prec_vals), 2),
                "buy_recall": round(sum(rec_vals) / len(rec_vals), 2),
                "accuracy_weighted": weighted("accuracy"),
                "buy_precision_weighted": weighted("buy_precision"),
                "buy_recall_weighted": weighted("buy_recall"),
                "p10_accuracy": round(np.percentile(acc_vals, 10), 2),
                "p50_accuracy": round(np.percentile(acc_vals, 50), 2),
                "p90_accuracy": round(np.percentile(acc_vals, 90), 2),
                "p10_buy_precision": round(np.percentile(prec_vals, 10), 2),
                "p50_buy_precision": round(np.percentile(prec_vals, 50), 2),
                "p90_buy_precision": round(np.percentile(prec_vals, 90), 2),
            }
        return out

    global_metrics = aggregate_metrics(summaries)
    total_train_rows = sum(s.get("train_rows", 0) for s in summaries)
    total_test_rows = sum(s.get("test_rows", 0) for s in summaries)
    total_final_rows = sum(s.get("training_rows", 0) for s in summaries)

    # Fitur yang konstan di SEMUA ticker = indikasi bug pipeline, bukan sifat fiturnya.
    constant_everywhere = sorted(
        set.intersection(*(set(s.get("constant_features", [])) for s in summaries))
    ) if summaries else []

    metadata = {
        "run_date": datetime.now().isoformat(),
        "checkpoints_dir": args.checkpoints_dir,
        "config": {
            "period": args.period,
            "min_rows": args.min_rows,
            "test_size": args.test_size,
            "walk_forward": args.walk_forward,
            "n_folds": args.n_folds,
        },
        "rows": {
            "tickers_requested": len(tickers),
            "tickers_trained": len(summaries),
            "holdout_train_rows": total_train_rows,
            "holdout_test_rows": total_test_rows,
            "final_train_rows": total_final_rows,
        },
        # Satu payload per horizon; sudah memuat varian macro (accuracy/buy_*),
        # varian weighted (*_weighted), dan percentile sekaligus. Nama key
        # dipertahankan karena dibaca ui/app.py dan compare_multiday_metrics.py.
        "holdout_metrics_macro_avg": global_metrics,
        "constant_features_all_tickers": constant_everywhere,
        "tickers": summaries,
        "errors": errors,
    }

    metadata_path = args.metadata_output
    if args.validate_only:
        metadata_path = args.metadata_output.replace("lgbm_multiday_meta.json", "lgbm_multiday_val_meta.json")

    os.makedirs(os.path.dirname(metadata_path), exist_ok=True)
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 72)
    if args.validate_only:
        print("  ML MULTI-DAY VALIDATION SUMMARY")
    else:
        print("  ML MULTI-DAY PER-TICKER TRAINING SUMMARY")
    print("=" * 72)
    if args.validate_only:
        print(f"Tickers validated: {len(summaries)} / {len(tickers)}")
    else:
        print(f"Tickers trained  : {len(summaries)} / {len(tickers)}")
    print(f"Final rows       : {total_final_rows}")
    if args.validate_only:
        print("Models saved to  : (Validation mode - no production models saved)")
    else:
        print(f"Models saved to  : {args.checkpoints_dir} (lgbm_<ticker>_<horizon>.pkl)")
    print(f"Metadata         : {metadata_path}")
    if constant_everywhere:
        print("-" * 72)
        print(f"⚠️  {len(constant_everywhere)} FITUR KONSTAN di SEMUA ticker (dibuang feature-selection,")
        print("    biasanya gejala bug pipeline — bukan sifat wajar fiturnya):")
        for feat in constant_everywhere:
            print(f"      - {feat}")
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
