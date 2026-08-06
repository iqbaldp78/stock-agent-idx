#!/usr/bin/env python3
"""
Cek paritas fitur: training vs live inference.

Membandingkan baris TERAKHIR dari prepare_training_data() dengan output
extract_features() untuk OHLCV yang sama. Keduanya seharusnya menghasilkan angka
identik — kalau tidak, model menerima nilai yang berbeda dari yang dipelajarinya.

Kenapa script ini ada: bug kelas ini TIDAK PERNAH memunculkan error. Sebelum
compute_ohlcv_features() dijadikan satu sumber kebenaran, 13 fitur diam-diam
melenceng — vol_trend_5d beda skala ~200x, close_to_high terbalik tanda, dan
rsi/vol_ratio/is_bullish_trend di live diparse dari teks agent. Semuanya berjalan
"normal" selama berbulan-bulan sambil menghasilkan prediksi yang salah.

Usage:
    python scripts/check_feature_parity.py                          # default 3 ticker
    python scripts/check_feature_parity.py --tickers BBCA BMRI
    python scripts/check_feature_parity.py --tickers BBCA --show-all
    python scripts/check_feature_parity.py --tickers BBCA --period 2y

Exit code 0 kalau semua fitur cocok, 1 kalau ada yang melenceng.
"""
import argparse
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config  # noqa: F401  (memuat .env)

import numpy as np
import pandas as pd

from data.ml_features import (
    MIN_HISTORY_ROWS,
    ML_TRAIN_FEATURES,
    extract_features,
    prepare_training_data,
)
from scripts.train_day1_model import fetch_ohlcv, normalize_ohlcv

logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Fitur yang memang TIDAK bisa punya paritas, karena sumbernya berbeda secara
# fundamental antara training dan live — bukan karena bug. Setiap entri wajib
# punya alasan; jangan tambahkan hanya supaya test hijau.
PARITY_EXEMPT = {
    "dist_avg_7d":
        "training dari rolling BrokerAccumulation di DB; live dari "
        "price_analysis['distance_from_7d'] milik agent bandarmologi",
    "bandar_accum_ratio":
        "turunan dari dist_avg_1m yang juga tidak punya paritas (definisinya sendiri "
        "sudah disatukan lewat _bandar_accum_ratio())",
}

DEFAULT_TICKERS = ["BBCA", "BMRI", "TLKM"]
# Toleransi relatif. Longgar sedikit karena jalur training vectorized dan jalur live
# memakai frame yang lebih pendek, sehingga bisa beda di digit terakhir float.
RTOL = 1e-6
ATOL = 1e-9


def compare_ticker(ticker: str, period: str, show_all: bool = False,
                   live_rows: int | None = None) -> list[dict]:
    """
    Return daftar fitur yang melenceng untuk satu ticker.

    live_rows: kalau diisi, jalur live hanya diberi N baris TERAKHIR sementara
    training tetap memakai riwayat penuh. Ini mensimulasikan kondisi produksi
    sebenarnya, di mana pemanggil mengambil window pendek. Tanpa mode ini, skew
    akibat riwayat kurang panjang (mis. ma_dist_200 yang butuh 200 baris) TIDAK
    akan terdeteksi karena kedua sisi memakai data yang sama.
    """
    raw = fetch_ohlcv(ticker, period)
    ohlcv = normalize_ohlcv(raw)
    if ohlcv.empty:
        raise ValueError(f"OHLCV kosong untuk {ticker}")

    X, _ = prepare_training_data(ohlcv, ticker=ticker)
    if X.empty:
        raise ValueError(f"prepare_training_data mengembalikan 0 baris untuk {ticker}")

    # Live inference dipanggil dengan scores/macro kosong: yang diuji adalah fitur
    # turunan data pasar, dan justru fitur itulah yang harus identik tanpa bantuan
    # agent. Fitur bersumber agent ada di PARITY_EXEMPT.
    live_ohlcv = ohlcv.tail(live_rows) if live_rows else ohlcv
    live = extract_features(ticker, scores={}, macro_data={}, ohlcv=live_ohlcv)

    # Baris terakhir training dan baris live merujuk tanggal yang sama.
    # NaN di sisi training diperlakukan 0.0 karena itu yang dilakukan
    # MultiDayPredictor._align_feature_frame() sebelum fit/predict.
    train_row = X.iloc[-1].reindex(ML_TRAIN_FEATURES).astype(float).fillna(0.0)
    live_row = live.iloc[0].reindex(ML_TRAIN_FEATURES).astype(float).fillna(0.0)

    rows = []
    for feat in ML_TRAIN_FEATURES:
        t, l = float(train_row[feat]), float(live_row[feat])
        ok = bool(np.isclose(t, l, rtol=RTOL, atol=ATOL))
        exempt = feat in PARITY_EXEMPT
        if show_all or (not ok and not exempt):
            rows.append({
                "feature": feat, "train": t, "live": l,
                "ok": ok, "exempt": exempt,
                "diff": l - t,
                # Rasio memperlihatkan bug beda-skala (mis. 200x) yang selisih
                # absolutnya terlihat kecil padahal fatal.
                "ratio": (l / t) if t not in (0.0,) else float("nan"),
            })
    return rows


def main():
    ap = argparse.ArgumentParser(description="Cek paritas fitur training vs live")
    ap.add_argument("--tickers", nargs="+", default=DEFAULT_TICKERS)
    ap.add_argument("--period", default="max", help="Periode OHLCV (default: max)")
    ap.add_argument("--show-all", action="store_true",
                    help="Tampilkan semua fitur, bukan hanya yang melenceng")
    ap.add_argument("--live-rows", type=int, default=None, metavar="N",
                    help="Batasi jalur live ke N baris terakhir untuk mensimulasikan "
                         "window pendek di produksi (mis. 60 untuk period=3mo). "
                         "Tanpa ini, skew akibat riwayat kurang panjang tidak terdeteksi.")
    args = ap.parse_args()

    print("=" * 78)
    print("  CEK PARITAS FITUR — training (baris terakhir) vs live inference")
    print("=" * 78)
    print(f"Fitur diperiksa : {len(ML_TRAIN_FEATURES)} di ML_TRAIN_FEATURES")
    print(f"Dikecualikan    : {len(PARITY_EXEMPT)} (sumber berbeda secara sah)")
    print(f"Toleransi       : rtol={RTOL}, atol={ATOL}")
    print(f"Window minimum  : {MIN_HISTORY_ROWS} baris (ditentukan ma_dist_200)")
    if args.live_rows:
        print(f"Simulasi live   : jalur live dibatasi {args.live_rows} baris terakhir")
        if args.live_rows < MIN_HISTORY_ROWS:
            print(f"                  ({args.live_rows} < {MIN_HISTORY_ROWS} -> "
                  f"fitur berwindow panjang DIHARAPKAN melenceng)")
    print("-" * 78)

    total_bad = 0
    errors = []
    for ticker in [t.upper() for t in args.tickers]:
        try:
            rows = compare_ticker(ticker, args.period, args.show_all, args.live_rows)
        except Exception as e:
            print(f"\n[{ticker}] ERROR: {e}")
            errors.append(ticker)
            continue

        bad = [r for r in rows if not r["ok"] and not r["exempt"]]
        total_bad += len(bad)

        if args.show_all:
            print(f"\n[{ticker}] semua fitur:")
            print(f"  {'fitur':<26}{'training':>16}{'live':>16}{'rasio':>10}  status")
            for r in rows:
                status = "exempt" if r["exempt"] else ("ok" if r["ok"] else "MELENCENG")
                print(f"  {r['feature']:<26}{r['train']:>16.8f}{r['live']:>16.8f}"
                      f"{r['ratio']:>10.3f}  {status}")
        elif bad:
            print(f"\n[{ticker}] {len(bad)} fitur MELENCENG:")
            print(f"  {'fitur':<26}{'training':>16}{'live':>16}{'rasio':>10}")
            for r in bad:
                print(f"  {r['feature']:<26}{r['train']:>16.8f}{r['live']:>16.8f}"
                      f"{r['ratio']:>10.3f}")
        else:
            print(f"\n[{ticker}] OK — semua fitur cocok.")

    print("\n" + "=" * 78)
    if errors:
        print(f"GAGAL: {len(errors)} ticker error: {', '.join(errors)}")
        sys.exit(1)
    if total_bad:
        print(f"GAGAL: {total_bad} ketidakcocokan fitur ditemukan.")
        print()
        print("Fitur yang melenceng berarti model menerima nilai berbeda dari yang")
        print("dipelajarinya saat training. Perbaiki dengan memastikan fitur tersebut")
        print("hanya dihitung di data/ml_features.py::compute_ohlcv_features() — jangan")
        print("dihitung ulang di extract_features(). Kalau perbedaannya memang sah")
        print("(sumber datanya beda), daftarkan di PARITY_EXEMPT beserta alasannya.")
        sys.exit(1)
    print("LULUS: semua fitur training dan live inference cocok.")
    print("=" * 78)


if __name__ == "__main__":
    main()
