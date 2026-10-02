#!/usr/bin/env python3
"""
Sweep threshold BUY di atas log prediksi live (ml_prediction_log), TANPA retrain.

Kolom pred_return_pct pada baris era-lama berisi probabilitas mentah [0,1]
(lihat readme/ML_MODEL_REPORT.md dan cron_ml_predict.py); baris legacy yang
tersimpan sebagai persen dinormalkan dengan aturan yang sama dengan UI
(>1.0 -> /100). Label dihitung ulang dari actual_return_pct memakai
TARGET_THRESHOLDS — sumber yang sama dengan training dan cron_ml_validate.

Untuk tiap horizon, sweep threshold 0.35..0.85: berapa precision sinyal BUY
yang akan terjadi kalau threshold-nya segitu, dibanding base rate baris yang
sama. Output utamanya: threshold terendah yang mencapai
precision >= base_rate + margin, plus berapa sinyal yang tersisa di situ.

Pakai:
    POSTGRES_HOST=localhost POSTGRES_PORT=5121 \
        venv/bin/python scripts/ml_log_threshold_sweep.py --days 120
"""
import sys, os, argparse, math

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from sqlalchemy import text
from db import engine
from data.ml_features import TARGET_THRESHOLDS
from scripts.ml_scorecard import fetch, wilson_halfwidth

HORIZONS = ["1d", "3d", "5d", "7d"]
GRID = np.arange(0.35, 0.86, 0.01)
MIN_TICKER_ROWS = 30


def load_rows(conn, horizon, days):
    rows = fetch(conn, """
        SELECT ticker,
               COALESCE(pred_prob,
                        CASE WHEN pred_return_pct <= 1.0 THEN pred_return_pct
                             ELSE pred_return_pct / 100.0 END) AS prob,
               actual_return_pct
        FROM ml_prediction_log
        WHERE horizon = :hz AND actual_return_pct IS NOT NULL
          AND trade_date >= (SELECT max(trade_date) FROM ml_prediction_log
                             WHERE is_correct IS NOT NULL) - CAST(:days AS int)
    """, hz=horizon, days=days)
    thr_pct = TARGET_THRESHOLDS[horizon] * 100
    tickers = np.array([r[0] for r in rows])
    probs = np.array([float(r[1]) for r in rows])
    labels = np.array([float(r[2]) >= thr_pct for r in rows])
    return tickers, probs, labels


def sweep(probs, labels, margin):
    """Kembalikan (list baris grid, threshold feasible terendah atau None)."""
    base = labels.mean() if len(labels) else float("nan")
    out, feasible = [], None
    for thr in GRID:
        mask = probs >= thr
        n = int(mask.sum())
        prec = labels[mask].mean() if n else None
        rec = (labels & mask).sum() / labels.sum() if labels.sum() else None
        row = {"thr": float(thr), "n": n, "prec": prec, "rec": rec}
        out.append(row)
        if feasible is None and n >= 5 and prec is not None and prec >= base + margin:
            feasible = row
    return base, out, feasible


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=120)
    ap.add_argument("--margin", type=float, default=0.05,
                    help="Margin precision di atas base rate (fraksi, default 0.05 = 5pp).")
    args = ap.parse_args()

    with engine.connect() as conn:
        for hz in HORIZONS:
            tickers, probs, labels = load_rows(conn, hz, args.days)
            if not len(probs):
                print(f"\n== {hz}: tidak ada baris matang ==")
                continue
            base, grid, feas = sweep(probs, labels, args.margin)
            print(f"\n== {hz} | {len(probs)} baris matang | base rate {base*100:.1f}% "
                  f"| threshold label +{TARGET_THRESHOLDS[hz]*100:.1f}% ==")

            shown = [r for r in grid if r["thr"] in
                     {0.35, 0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80}
                     or (abs(round(r["thr"] * 100) % 5) < 1e-9)]
            for r in grid:
                if round(r["thr"] * 100) % 5:  # tampilkan tiap 0.05 saja
                    continue
                if r["prec"] is None:
                    print(f"   thr {r['thr']:.2f}: n=0")
                    continue
                ci = wilson_halfwidth(r["prec"], r["n"])
                print(f"   thr {r['thr']:.2f}: n={r['n']:5d} "
                      f"prec={r['prec']*100:5.1f}% ±{ci:4.1f} "
                      f"edge={100*(r['prec']-base):+5.1f}pp rec={100*(r['rec'] or 0):5.1f}%")
            if feas:
                ci = wilson_halfwidth(feas["prec"], feas["n"])
                print(f"   >> FEASIBLE terendah: thr={feas['thr']:.2f} "
                      f"prec={feas['prec']*100:.1f}% ±{ci:.1f} (base {base*100:.1f}%) "
                      f"n={feas['n']} sinyal, recall {100*feas['rec']:.1f}%")
            else:
                print(f"   >> TIDAK ADA threshold yang mencapai base+{args.margin*100:.0f}pp "
                      f"dengan n>=5 -> kandidat NO-TRADE")

            # Per ticker: apakah ada subset ticker yang feasible sendiri?
            feas_t = []
            for tk in np.unique(tickers):
                m = tickers == tk
                if m.sum() < MIN_TICKER_ROWS:
                    continue
                b, _, f = sweep(probs[m], labels[m], args.margin)
                if f:
                    feas_t.append((tk, f["thr"], f["prec"], b, f["n"]))
            feas_t.sort(key=lambda x: -(x[2] - x[3]))
            print(f"   ticker feasible sendiri (>= {MIN_TICKER_ROWS} baris): {len(feas_t)}")
            for tk, thr, prec, b, n in feas_t[:10]:
                print(f"      {tk:6s} thr={thr:.2f} prec={prec*100:5.1f}% "
                      f"base={b*100:5.1f}% (+{100*(prec-b):4.1f}pp) n={n}")


if __name__ == "__main__":
    main()
