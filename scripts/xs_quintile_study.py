#!/usr/bin/env python3
"""
Uji apakah IC cross-sectional itu benar-benar bisa ditradingin.

IC yang signifikan belum berarti uang. Studi ini mengubah IC jadi angka yang
langsung terbaca: tiap hari bursa, urutkan saham pakai skor komposit, lalu ukur
selisih forward return antara kuintil teratas dan terbawah. Kalau spread-nya
positif dan konsisten, sinyalnya bisa dipakai; kalau tidak, IC itu cuma statistik.

Skornya dibangun dari fitur yang IC-nya signifikan, dengan tanda IC sebagai arah
bobot — jadi tidak ada model yang di-fit dan tidak ada parameter yang di-tune.
Ini sengaja: kalau strategi tanpa fitting sekalipun sudah punya spread, sinyalnya
nyata. Kalau butuh fitting untuk muncul, kemungkinan besar itu overfit.

Semua fitur hanya memakai data masa lalu, dan ranking dilakukan per tanggal, jadi
tidak ada informasi masa depan yang bocor. Bobot IC diambil dari periode IN-SAMPLE
pertama saja (--is-frac) dan diuji pada sisanya, supaya seleksi fiturnya tidak
melihat data uji.

Pakai:
    python scripts/xs_quintile_study.py --panel scratch/panel.parquet \
        --ic scratch/feature_ic.json --out scratch/xs_quintile.json
"""
import sys, os, json, argparse, logging, math

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
import pandas as pd

from data.ml_features import FEATURE_COLUMNS
from scripts.feature_ic_study import cross_sectional_ic, summarise

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("xs")

MIN_TICKERS_PER_DATE = 10
T_GATE = 2.0          # ambang |t| untuk memasukkan fitur ke skor komposit
EPS = 1e-12


def zscore_by_date(df, cols):
    """Standardisasi per tanggal — bikin fitur dengan skala beda bisa dijumlah."""
    g = df.groupby(level=0)
    mu = g[cols].transform("mean")
    sd = g[cols].transform("std")
    return (df[cols] - mu) / sd.where(sd > EPS)


def run(panel, hz, is_frac, n_quantiles, feature_pool):
    fwd = f"fwd_{hz}"
    if fwd not in panel.columns:
        return None

    dates = panel.index.get_level_values(0).unique().sort_values()
    split_at = dates[int(len(dates) * is_frac)]

    # Seleksi fitur HANYA dari bagian in-sample. IC-nya DIHITUNG ULANG di sini
    # atas slice in-sample — bukan dibaca dari feature_ic_study.py, karena IC di
    # sana dihitung atas seluruh periode dan memakainya untuk memilih fitur akan
    # membocorkan data uji ke tahap seleksi (look-ahead bias).
    is_panel = panel[panel.index.get_level_values(0) <= split_at]
    ic_res = cross_sectional_ic(is_panel, feature_pool, fwd)
    if ic_res is None:
        return None
    feats_ic = summarise(ic_res[0], feature_pool)
    picks = {}
    for f, d in feats_ic.items():
        if d.get("t_stat") is None or abs(d["t_stat"]) < T_GATE:
            continue
        if f not in panel.columns or f.startswith("fwd_"):
            continue
        col = is_panel[f]
        if col.notna().sum() < 100 or col.std(skipna=True) <= EPS:
            continue
        picks[f] = -1.0 if d["t_stat"] < 0 else 1.0   # arah = tanda IC
    if not picks:
        return None

    cols = sorted(picks)
    z = zscore_by_date(panel, cols)
    signs = pd.Series({c: picks[c] for c in cols})
    score = (z[cols] * signs).mean(axis=1, skipna=True)

    work = pd.DataFrame({"score": score, "fwd": panel[fwd]}).dropna()
    oos = work[work.index.get_level_values(0) > split_at]

    def spread(frame):
        rows = []
        for dt, grp in frame.groupby(level=0):
            if len(grp) < MIN_TICKERS_PER_DATE:
                continue
            q = pd.qcut(grp["score"].rank(method="first"), n_quantiles,
                        labels=False, duplicates="drop")
            if q.nunique() < n_quantiles:
                continue
            top = grp["fwd"][q == n_quantiles - 1].mean()
            bot = grp["fwd"][q == 0].mean()
            rows.append({"date": dt, "top": top, "bottom": bot,
                         "spread": top - bot, "all": grp["fwd"].mean()})
        return pd.DataFrame(rows)

    out = {}
    for label, frame in (("in_sample", work[work.index.get_level_values(0) <= split_at]),
                         ("out_of_sample", oos)):
        s = spread(frame)
        if s.empty:
            out[label] = None
            continue
        sp = s["spread"]
        # t-stat atas rata-rata spread harian; hari saling tumpang tindih untuk
        # horizon > 1d, jadi t-stat di-deflate dengan akar horizon (Newey-West kasar).
        overlap = max(int(hz[0]), 1)
        t = (sp.mean() / (sp.std(ddof=1) / math.sqrt(len(sp)))) / math.sqrt(overlap) \
            if sp.std(ddof=1) > EPS else None
        out[label] = {
            "n_days": int(len(s)),
            "mean_top_pct": float(s["top"].mean() * 100),
            "mean_bottom_pct": float(s["bottom"].mean() * 100),
            "mean_all_pct": float(s["all"].mean() * 100),
            "mean_spread_pct": float(sp.mean() * 100),
            "t_stat_overlap_adj": float(t) if t is not None else None,
            "hit_rate_pct": float((sp > 0).mean() * 100),
            "top_beats_avg_pct": float((s["top"] > s["all"]).mean() * 100),
        }
    out["features_used"] = {c: ("+" if picks[c] > 0 else "-") for c in cols}
    out["n_features"] = len(cols)
    out["split_date"] = str(split_at.date() if hasattr(split_at, "date") else split_at)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--panel", required=True)
    ap.add_argument("--ic", default=None,
                    help="Opsional. Hanya dicatat sebagai pembanding; TIDAK dipakai "
                         "untuk memilih fitur (itu dihitung ulang dari slice in-sample).")
    ap.add_argument("--out", default="scratch/xs_quintile.json")
    ap.add_argument("--is-frac", type=float, default=0.5,
                    help="Porsi awal data untuk seleksi fitur (default 0.5)")
    ap.add_argument("--quantiles", type=int, default=5)
    args = ap.parse_args()

    panel = pd.read_parquet(args.panel)
    logger.info("Panel %d baris, %d tanggal", len(panel),
                panel.index.get_level_values(0).nunique())

    feature_pool = [c for c in FEATURE_COLUMNS
                    if c in panel.columns and not c.startswith("fwd_")]
    logger.info("Kolam fitur: %d", len(feature_pool))

    results = {}
    for hz in ["1d", "3d", "5d", "7d"]:
        r = run(panel, hz, args.is_frac, args.quantiles, feature_pool)
        if r:
            results[hz] = r
            logger.info("%s: %d fitur dipakai", hz, r["n_features"])

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print("\n" + "=" * 86)
    print("  SPREAD KUINTIL CROSS-SECTIONAL (tanpa model, tanpa tuning)")
    print("=" * 86)
    for hz, r in results.items():
        print(f"\n--- {hz.upper()} | {r['n_features']} fitur | split {r['split_date']} ---")
        print(f"{'':<16}{'hari':>7}{'top Q':>9}{'bottom Q':>10}{'rata2':>9}"
              f"{'spread':>9}{'t':>7}{'hit':>7}")
        for label in ("in_sample", "out_of_sample"):
            d = r.get(label)
            if not d:
                continue
            t = d["t_stat_overlap_adj"]
            print(f"{label:<16}{d['n_days']:>7}{d['mean_top_pct']:>+8.2f}%"
                  f"{d['mean_bottom_pct']:>+9.2f}%{d['mean_all_pct']:>+8.2f}%"
                  f"{d['mean_spread_pct']:>+8.2f}%{(t if t is not None else float('nan')):>+7.2f}"
                  f"{d['hit_rate_pct']:>6.0f}%")
    print(f"\nDetail -> {args.out}")


if __name__ == "__main__":
    main()
