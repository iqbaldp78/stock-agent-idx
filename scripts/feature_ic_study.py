#!/usr/bin/env python3
"""
Ukur Information Coefficient (IC) cross-sectional tiap fitur terhadap forward return.

Kenapa cross-sectional dan bukan time-series: log live menunjukkan win rate harian
berkorelasi +0.91 dengan breadth pasar, artinya model sekarang cuma menangkap arah
pasar, bukan pemilihan saham. IC cross-sectional mengukur hal yang kita betulan mau:
pada SATU hari yang sama, apakah fitur ini bisa mengurutkan saham mana yang lebih
unggul dari yang lain. Komponen market-wide otomatis hilang karena semua saham di
satu tanggal kena kondisi pasar yang sama.

Dijalankan atas SELURUH FEATURE_COLUMNS (89), bukan cuma ML_TRAIN_FEATURES (58),
supaya kelihatan apakah 31 fitur yang tidak pernah dilatih itu membawa informasi.

Output: mean IC, t-stat, dan cakupan per fitur per horizon.
Pakai:
    python scripts/feature_ic_study.py --all --period 5y --out scratch/feature_ic.json
"""
import sys, os, json, argparse, logging, math
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
import pandas as pd

from data.ml_features import FEATURE_COLUMNS, ML_TRAIN_FEATURES, TARGET_HORIZON_DAYS
from scripts.train_day1_model import get_universe_tickers, fetch_ohlcv, normalize_ohlcv

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ic")

# Minimal jumlah saham pada satu tanggal supaya IC cross-sectional punya arti.
MIN_TICKERS_PER_DATE = 10
# Fitur yang variansnya nol dalam satu tanggal tidak bisa mengurutkan apa pun.
EPS = 1e-12


def build_panel(tickers, period):
    """Kumpulkan panel (tanggal, ticker) -> fitur + forward return per horizon."""
    from data.ml_features import prepare_training_data

    frames = []
    for i, tk in enumerate(tickers, 1):
        try:
            raw = fetch_ohlcv(tk, period)
            ohlcv = normalize_ohlcv(raw)
            if ohlcv.empty or len(ohlcv) < 60:
                logger.warning("%s: OHLCV kurang, dilewati", tk)
                continue
            X, _ = prepare_training_data(ohlcv, ticker=tk)
            if X.empty:
                continue

            close = pd.to_numeric(ohlcv["Close"], errors="coerce")
            close.index = pd.to_datetime(close.index)
            close = close.reindex(X.index)

            df = X.copy()
            for hz, n in TARGET_HORIZON_DAYS.items():
                # forward return murni (bukan label biner) — IC butuh besaran kontinu
                df[f"fwd_{hz}"] = (close.shift(-n) - close) / close
            df["ticker"] = tk
            df.index.name = "date"
            frames.append(df.reset_index().set_index(["date", "ticker"]))
            logger.info("[%d/%d] %s: %d baris", i, len(tickers), tk, len(X))
        except Exception as e:
            logger.error("%s gagal: %s", tk, e)

    if not frames:
        raise SystemExit("Tidak ada data panel yang berhasil dibangun.")
    return pd.concat(frames).sort_index()


def cross_sectional_ic(panel, feats, fwd_col):
    """Spearman IC per tanggal, dihitung sebagai Pearson atas rank."""
    ics, n_used = [], []
    for _, grp in panel.groupby(level=0, sort=True):
        sub = grp[feats + [fwd_col]].dropna(subset=[fwd_col])
        if len(sub) < MIN_TICKERS_PER_DATE:
            continue
        Ar = sub[feats].rank().to_numpy(dtype=float)
        yr = sub[fwd_col].rank().to_numpy(dtype=float)
        Ac = Ar - Ar.mean(axis=0)
        yc = yr - yr.mean()
        denom = np.sqrt((Ac ** 2).sum(axis=0) * (yc ** 2).sum())
        with np.errstate(invalid="ignore", divide="ignore"):
            ic = np.where(denom > EPS, (Ac * yc[:, None]).sum(axis=0) / denom, np.nan)
        ics.append(ic)
        n_used.append(len(sub))
    if not ics:
        return None
    return np.vstack(ics), n_used


def summarise(ic_matrix, feats):
    out = {}
    for j, f in enumerate(feats):
        col = ic_matrix[:, j]
        ok = col[~np.isnan(col)]
        if len(ok) < 20:
            out[f] = {"mean_ic": None, "t_stat": None, "n_dates": int(len(ok)),
                      "coverage": round(len(ok) / len(col), 3) if len(col) else 0.0}
            continue
        m, s = float(ok.mean()), float(ok.std(ddof=1))
        out[f] = {
            "mean_ic": m,
            "t_stat": (m / (s / math.sqrt(len(ok)))) if s > EPS else None,
            "n_dates": int(len(ok)),
            "coverage": round(len(ok) / len(col), 3),
        }
    return out


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--tickers", nargs="+")
    g.add_argument("--all", action="store_true")
    ap.add_argument("--period", default="5y")
    ap.add_argument("--out", default="scratch/feature_ic.json")
    ap.add_argument("--dump-panel", default=None,
                    help="Simpan panel fitur ke parquet supaya studi lanjutan tidak "
                         "perlu menghitung ulang fitur (bagian termahal).")
    args = ap.parse_args()

    tickers = get_universe_tickers() if args.all else [t.upper() for t in args.tickers]
    logger.info("IC study atas %d ticker, periode %s", len(tickers), args.period)

    panel = build_panel(tickers, args.period)
    feats = [c for c in FEATURE_COLUMNS if c in panel.columns]
    logger.info("Panel: %d baris, %d tanggal, %d fitur",
                len(panel), panel.index.get_level_values(0).nunique(), len(feats))

    if args.dump_panel:
        os.makedirs(os.path.dirname(args.dump_panel) or ".", exist_ok=True)
        panel.to_parquet(args.dump_panel)
        logger.info("Panel disimpan -> %s", args.dump_panel)

    trained = set(ML_TRAIN_FEATURES)
    results = {}
    for hz in TARGET_HORIZON_DAYS:
        res = cross_sectional_ic(panel, feats, f"fwd_{hz}")
        if res is None:
            logger.warning("%s: tidak ada tanggal yang memenuhi syarat", hz)
            continue
        ic_matrix, n_used = res
        results[hz] = {
            "n_dates": int(ic_matrix.shape[0]),
            "avg_tickers_per_date": round(float(np.mean(n_used)), 1),
            "features": summarise(ic_matrix, feats),
        }
        logger.info("%s: IC dihitung atas %d tanggal", hz, ic_matrix.shape[0])

    payload = {
        "period": args.period,
        "tickers": tickers,
        "n_rows": int(len(panel)),
        "min_tickers_per_date": MIN_TICKERS_PER_DATE,
        "trained_features": sorted(trained),
        "untrained_features": sorted(set(feats) - trained),
        "horizons": results,
    }
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    # Ringkasan ke stdout: |t| >= 2 dianggap punya sinyal yang bisa dipertanggungjawabkan
    for hz, r in results.items():
        rows = [(f, d) for f, d in r["features"].items() if d["t_stat"] is not None]
        rows.sort(key=lambda kv: -abs(kv[1]["t_stat"]))
        print("\n" + "=" * 78)
        print(f"  HORIZON {hz.upper()}  ({r['n_dates']} tanggal, rata-rata "
              f"{r['avg_tickers_per_date']} saham/tanggal)")
        print("=" * 78)
        print(f"{'fitur':<28}{'mean IC':>10}{'t-stat':>9}{'dilatih?':>10}")
        for f, d in rows[:20]:
            flag = "ya" if f in trained else "TIDAK"
            print(f"{f:<28}{d['mean_ic']:>+10.4f}{d['t_stat']:>+9.2f}{flag:>10}")
        sig = [f for f, d in rows if abs(d["t_stat"]) >= 2]
        sig_untrained = [f for f in sig if f not in trained]
        print(f"\n  |t| >= 2 : {len(sig)} fitur, {len(sig_untrained)} di antaranya BELUM dilatih")
        if sig_untrained:
            print(f"  belum dilatih tapi signifikan: {', '.join(sig_untrained[:14])}")

    print(f"\nDetail lengkap -> {args.out}")


if __name__ == "__main__":
    main()
