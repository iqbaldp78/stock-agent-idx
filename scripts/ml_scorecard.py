#!/usr/bin/env python3
"""
Bikin scorecard HTML untuk ml_prediction_log.

Metrik utamanya BUY win rate: dari sinyal yang benar-benar bilang BELI, berapa
persen yang kena target threshold horizon-nya. Overall accuracy sengaja ikut
dihitung tapi diberi label "vanity" — mayoritas prediksi berisi TURUN dan
"benar kalau tidak naik" gampang terpenuhi, jadi angkanya naik tanpa model
harus punya kemampuan apa pun.

Pembandingnya base rate: berapa persen SELURUH baris (tanpa peduli prediksi)
yang naik di atas threshold pada periode itu. Edge = BUY win rate - base rate.
Kalau edge ~0, model cuma ikut arah pasar hari itu.

Pakai:
    python scripts/ml_scorecard.py --days 14 --out scratch/ml_scorecard.html
"""
import sys, os, json, argparse, math
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sqlalchemy import text
from db import engine
from data.ml_features import TARGET_THRESHOLDS

META_PATH = "models/checkpoints/lgbm_multiday_meta.json"
TPL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates", "ml_scorecard.html.tpl")
HORIZONS = ["1d", "3d", "5d", "7d"]
# Minimal sinyal BUY dalam satu hari sebelum hari itu dipakai untuk korelasi.
# Di bawah ini rasio harian terlalu berisik (1 sinyal -> 0% atau 100%).
MIN_BUY_PER_DAY = 5


def thr_pct(horizon):
    return TARGET_THRESHOLDS[horizon] * 100


def wilson_halfwidth(p, n):
    """Setengah lebar interval kepercayaan 95% (normal approx), dalam poin persen."""
    if not n:
        return None
    return 1.96 * math.sqrt(max(p * (1 - p), 0.0) / n) * 100


def pearson(xs, ys):
    n = len(xs)
    if n < 3:
        return None
    mx, my = sum(xs) / n, sum(ys) / n
    num = sum((a - mx) * (b - my) for a, b in zip(xs, ys))
    dx = math.sqrt(sum((a - mx) ** 2 for a in xs))
    dy = math.sqrt(sum((b - my) ** 2 for b in ys))
    if dx == 0 or dy == 0:
        return None
    return num / (dx * dy)


def fetch(conn, sql, **params):
    return conn.execute(text(sql), params).fetchall()


def build(days):
    with engine.connect() as conn:
        latest = fetch(conn, "SELECT max(trade_date) FROM ml_prediction_log WHERE is_correct IS NOT NULL")[0][0]
        if latest is None:
            raise SystemExit("Belum ada log tervalidasi.")
        start = latest - timedelta(days=days - 1)

        horizons = []
        for hz in HORIZONS:
            t = thr_pct(hz)
            row = fetch(conn, """
                SELECT count(*) AS matured,
                       count(*) FILTER (WHERE predicted_direction='NAIK') AS buy,
                       count(*) FILTER (WHERE predicted_direction='NAIK' AND is_correct) AS buy_win,
                       count(*) FILTER (WHERE actual_return_pct > :t) AS base_up,
                       count(*) FILTER (WHERE is_correct) AS acc_n,
                       avg(actual_return_pct) FILTER (WHERE predicted_direction='NAIK') AS ret_buy,
                       avg(actual_return_pct) AS ret_all
                FROM ml_prediction_log
                WHERE horizon=:hz AND is_correct IS NOT NULL
                  AND trade_date BETWEEN :a AND :b
            """, t=t, hz=hz, a=start, b=latest)[0]
            matured, buy, buy_win, base_up, acc_n, ret_buy, ret_all = row
            bw = 100.0 * buy_win / buy if buy else None
            base = 100.0 * base_up / matured if matured else None
            horizons.append({
                "horizon": hz,
                "threshold_pct": t,
                "matured": matured,
                "buy": buy,
                "buy_win": bw,
                "ci": wilson_halfwidth(buy_win / buy, buy) if buy else None,
                "base": base,
                "edge": (bw - base) if (bw is not None and base is not None) else None,
                "overall_acc": 100.0 * acc_n / matured if matured else None,
                "ret_buy": float(ret_buy) if ret_buy is not None else None,
                "ret_all": float(ret_all) if ret_all is not None else None,
            })

        # Headline: gabungan seluruh horizon di dalam window.
        tot_buy = sum(h["buy"] for h in horizons)
        tot_win = sum(round((h["buy_win"] or 0) / 100 * h["buy"]) for h in horizons)
        tot_matured = sum(h["matured"] for h in horizons)
        tot_base = sum(round((h["base"] or 0) / 100 * h["matured"]) for h in horizons)

        # Deret harian dipakai untuk korelasi. Diambil dari SELURUH histori log
        # (bukan cuma window) supaya titiknya cukup untuk korelasi yang berarti.
        daily = []
        for hz in HORIZONS:
            t = thr_pct(hz)
            for td, nbuy, nwin, nrow, nup in fetch(conn, """
                SELECT trade_date,
                       count(*) FILTER (WHERE predicted_direction='NAIK'),
                       count(*) FILTER (WHERE predicted_direction='NAIK' AND is_correct),
                       count(*), count(*) FILTER (WHERE actual_return_pct > :t)
                FROM ml_prediction_log
                WHERE horizon=:hz AND is_correct IS NOT NULL
                GROUP BY 1 ORDER BY 1
            """, t=t, hz=hz):
                if nbuy < MIN_BUY_PER_DAY:
                    continue
                daily.append({
                    "horizon": hz, "date": str(td), "buy": nbuy,
                    "buy_win": 100.0 * nwin / nbuy,
                    "base": 100.0 * nup / nrow if nrow else None,
                    "in_window": start <= td <= latest,
                })

        for h in horizons:
            pts = [d for d in daily if d["horizon"] == h["horizon"]]
            h["corr"] = pearson([d["base"] for d in pts], [d["buy_win"] for d in pts])
            h["corr_days"] = len(pts)

        pooled_corr = pearson([d["base"] for d in daily], [d["buy_win"] for d in daily])
        pooled_edge = (sum(d["buy_win"] - d["base"] for d in daily) / len(daily)) if daily else None

        tickers = [{"ticker": tk, "buy": b, "win": 100.0 * w / b}
                   for tk, b, w in fetch(conn, """
                SELECT ticker,
                       count(*) FILTER (WHERE predicted_direction='NAIK'),
                       count(*) FILTER (WHERE predicted_direction='NAIK' AND is_correct)
                FROM ml_prediction_log
                WHERE is_correct IS NOT NULL AND trade_date BETWEEN :a AND :b
                GROUP BY 1
                HAVING count(*) FILTER (WHERE predicted_direction='NAIK') >= :m
                ORDER BY 3.0 / NULLIF(count(*) FILTER (WHERE predicted_direction='NAIK'),0) DESC
           """, a=start, b=latest, m=MIN_BUY_PER_DAY)]
        tickers.sort(key=lambda r: -r["win"])

        pend = fetch(conn, """
            SELECT count(*) FILTER (WHERE is_correct IS NULL),
                   min(trade_date) FILTER (WHERE is_correct IS NULL),
                   max(trade_date), max(validated_at)
            FROM ml_prediction_log
        """)[0]
        n_days = fetch(conn, """
            SELECT count(DISTINCT trade_date) FROM ml_prediction_log
            WHERE is_correct IS NOT NULL AND trade_date BETWEEN :a AND :b
        """, a=start, b=latest)[0][0]

    holdout = {}
    try:
        with open(META_PATH, encoding="utf-8") as f:
            meta = json.load(f)
        hm = meta.get("holdout_metrics_macro_avg", {})
        for hz in HORIZONS:
            x = hm.get(hz, {})
            holdout[hz] = {
                "buy_precision": x.get("buy_precision"),
                "base_rate": x.get("base_rate"),
                "edge": (x.get("buy_precision") - x.get("base_rate"))
                        if x.get("buy_precision") is not None and x.get("base_rate") is not None else None,
                "n_usable": x.get("n_usable"),
                "n_degenerate": x.get("n_degenerate"),
            }
        train_cfg = {"run_date": meta.get("run_date"), **meta.get("config", {})}
    except Exception as e:
        train_cfg = {"error": str(e)}

    for h in horizons:
        h["holdout"] = holdout.get(h["horizon"], {})

    return {
        "window": {"start": str(start), "end": str(latest), "days": days, "trading_days": n_days},
        "headline": {
            "buy_signals": tot_buy,
            "buy_win_rate": 100.0 * tot_win / tot_buy if tot_buy else None,
            "ci": wilson_halfwidth(tot_win / tot_buy, tot_buy) if tot_buy else None,
            "base_rate": 100.0 * tot_base / tot_matured if tot_matured else None,
            "matured": tot_matured,
            "pooled_corr": pooled_corr,
            "pooled_edge": pooled_edge,
            "corr_days": len(daily),
        },
        "horizons": horizons,
        "daily": daily,
        "tickers": tickers,
        "freshness": {
            "pending": pend[0], "pending_from": str(pend[1]) if pend[1] else None,
            "max_trade_date": str(pend[2]) if pend[2] else None,
            "last_validated": str(pend[3]) if pend[3] else None,
        },
        "training": train_cfg,
        "thresholds": {h: thr_pct(h) for h in HORIZONS},
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=14)
    ap.add_argument("--out", default="scratch/ml_scorecard.html")
    ap.add_argument("--json", default=None, help="Tulis juga data mentahnya ke path ini.")
    args = ap.parse_args()

    data = build(args.days)
    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)

    with open(TPL_PATH, encoding="utf-8") as f:
        tpl = f.read()
    payload = json.dumps(data, default=str)
    if "/*__SCORECARD_DATA__*/" not in tpl:
        raise SystemExit(f"Placeholder tidak ada di {TPL_PATH}")
    html = tpl.replace("/*__SCORECARD_DATA__*/", payload)

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(html)
    h = data["headline"]
    print(f"OK -> {args.out}")
    print(f"   window {data['window']['start']}..{data['window']['end']} "
          f"({data['window']['trading_days']} hari bursa)")
    print(f"   BUY win rate {h['buy_win_rate']:.1f}% dari {h['buy_signals']} sinyal | "
          f"base {h['base_rate']:.1f}% | corr {h['pooled_corr']:+.3f} ({h['corr_days']} hari)")


if __name__ == "__main__":
    main()
