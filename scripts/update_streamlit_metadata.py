#!/usr/bin/env python3
import os
import sys
import json
import logging
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.train_day1_model import get_universe_tickers, fetch_ohlcv, normalize_ohlcv
from scripts.train_multiday_model import aggregate_metrics, evaluate_multiday_model
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

        # Dulu blok evaluasi di sini diduplikasi dari train_multiday_model.py dan
        # membawa tiga bug: model.predict() dipakai seolah hasilnya probabilitas
        # (padahal label 0/1, sehingga threshold hasil tuning tidak pernah terpakai),
        # model.feature_name() yang tidak ada di CalibratedClassifierCV sehingga
        # kolom tidak cocok lalu error ditelan `except: continue`, dan default
        # threshold 0.55 yang beda dari 0.50 di seluruh kode lain.
        # Sekarang memakai satu implementasi yang sudah benar.
        metrics = evaluate_multiday_model(predictor, X_test, Y_test)
        if not metrics:
            # Instrumentasi yang selama ini hilang: versi lama diam saja lalu
            # menulis metadata kosong, sehingga model yang tidak ter-load
            # tampak seperti model yang metriknya memang nol.
            logging.warning(
                "%s: tidak ada metrik — model tidak ter-load dari %s "
                "(cek keberadaan lgbm_%s_<horizon>.pkl)",
                ticker, checkpoints_dir, ticker.upper(),
            )

        summaries.append({
            "ticker": ticker,
            "ohlcv_rows": len(ohlcv),
            "training_rows": len(X),
            "train_rows": split_i,
            "test_rows": len(X_test),
            "metrics": metrics,
        })

    total_train_rows = sum(s["train_rows"] for s in summaries)
    total_test_rows = sum(s["test_rows"] for s in summaries)
    total_final_rows = sum(s["training_rows"] for s in summaries)

    global_metrics = aggregate_metrics(summaries)

    # "tickers_trained" dulu menghitung ticker yang diproses, bukan yang benar-benar
    # punya model — jadi metadata bisa mengklaim 64 model terlatih walau tidak ada
    # satu pun .pkl yang ter-load. Pisahkan keduanya secara eksplisit.
    tickers_with_models = sum(1 for s in summaries if s.get("metrics"))

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
            "tickers_evaluated": len(summaries),
            "tickers_with_models": tickers_with_models,
            # Key lama dipertahankan supaya ui/app.py tidak pecah, tapi kini diisi
            # jumlah yang benar-benar punya model.
            "tickers_trained": tickers_with_models,
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

    print(f"Metadata ditulis ke {metadata_output}")
    print(f"Ticker dievaluasi   : {len(summaries)} / {len(tickers)}")
    print(f"Ticker punya model  : {tickers_with_models}")
    if tickers_with_models == 0:
        # Jangan pernah melaporkan SUCCESS untuk metadata tanpa satu pun model —
        # itu justru kondisi yang selama ini lolos tanpa terdeteksi.
        print(f"GAGAL: tidak ada model yang ter-load dari {checkpoints_dir}.")
        print("       Metadata ditulis tapi metriknya kosong. Jalankan training dulu.")
        sys.exit(1)
    if tickers_with_models < len(summaries):
        print(f"PERINGATAN: {len(summaries) - tickers_with_models} ticker tanpa model.")
    for h, v in global_metrics.items():
        print(
            f"  [{h}] acc={v['accuracy']:.2f}% baseline={v.get('majority_baseline', 0):.2f}% "
            f"lift={v.get('lift', 0):.3f} usable={v.get('n_usable', 0)} "
            f"degenerate={v.get('n_degenerate', 0)}"
        )

if __name__ == "__main__":
    main()
