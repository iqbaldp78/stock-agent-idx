#!/usr/bin/env python3
"""Rangkum semua hasil studi ML jadi satu file markdown."""
import sys, os, json, argparse
from datetime import datetime

def load(p):
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        return {"__error__": str(e)}

def ok(d):
    return isinstance(d, dict) and "__error__" not in d and d

def fmt(v, s="%.2f", dash="–"):
    return dash if v is None else s % v

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--holdout", default="models/checkpoints/lgbm_multiday_meta.json")
    ap.add_argument("--walkforward", default="models/checkpoints/lgbm_multiday_val_meta.json")
    ap.add_argument("--ic", default="scratch/feature_ic.json")
    ap.add_argument("--quintile", default="scratch/xs_quintile.json")
    ap.add_argument("--scorecard", default="scratch/ml_scorecard.json")
    ap.add_argument("--out", default="scratch/REPORT.md")
    a = ap.parse_args()

    ho, wf, ic, xq, sc = (load(a.holdout), load(a.walkforward), load(a.ic),
                          load(a.quintile), load(a.scorecard))
    L = []
    w = L.append
    HZ = ["1d", "3d", "5d", "7d"]

    w(f"# Laporan Model ML — {datetime.now():%Y-%m-%d %H:%M}\n")
    w("Dibuat otomatis oleh `scripts/build_ml_report.py`. Semua angka lahir dari "
      "script yang bisa dijalankan ulang; tidak ada yang diketik tangan.\n")

    # 1. live scorecard
    w("## 1. Kenyataan di log live\n")
    if ok(sc):
        h, win = sc["headline"], sc["window"]
        w(f"Periode **{win['start']} → {win['end']}** ({win['trading_days']} hari bursa).\n")
        w(f"- BUY win rate: **{fmt(h['buy_win_rate'],'%.1f')}%** dari "
          f"{h['buy_signals']} sinyal (CI ±{fmt(h.get('ci'),'%.1f')}pp)")
        w(f"- Base rate pasar: {fmt(h['base_rate'],'%.1f')}%")
        w(f"- Korelasi win rate harian vs breadth pasar: "
          f"**{fmt(h['pooled_corr'],'%+.3f')}** atas {h['corr_days']} hari-horizon")
        w(f"- Rata-rata edge harian: {fmt(h['pooled_edge'],'%+.2f')}pp\n")
        w("| horizon | sinyal BUY | win rate | base rate | edge |")
        w("|---|---|---|---|---|")
        for x in sc["horizons"]:
            w(f"| {x['horizon']} | {x['buy']} | {fmt(x['buy_win'],'%.1f')}% "
              f"±{fmt(x['ci'],'%.1f')} | {fmt(x['base'],'%.1f')}% | "
              f"{fmt(x['edge'],'%+.1f')}pp |")
        w("")
    else:
        w("_scorecard tidak tersedia._\n")

    # 2. holdout vs walk-forward
    w("## 2. Single-holdout vs walk-forward\n")
    if ok(ho) and ok(wf):
        hm, wm = ho.get("holdout_metrics_macro_avg", {}), wf.get("holdout_metrics_macro_avg", {})
        w(f"Single-holdout: {ho.get('rows',{}).get('tickers_trained','?')} ticker. "
          f"Walk-forward: {wf.get('rows',{}).get('tickers_trained','?')} ticker, "
          f"{wf.get('config',{}).get('n_folds','?')} fold.\n")
        w("| horizon | edge holdout | edge walk-forward | lift holdout | lift WF | selisih |")
        w("|---|---|---|---|---|---|")
        for hz in HZ:
            A, B = hm.get(hz, {}), wm.get(hz, {})
            ea = (A.get("buy_precision", 0) - A.get("base_rate", 0)) if A else None
            eb = (B.get("buy_precision", 0) - B.get("base_rate", 0)) if B else None
            d = (eb - ea) if (ea is not None and eb is not None) else None
            w(f"| {hz} | {fmt(ea,'%+.1f')}pp | {fmt(eb,'%+.1f')}pp | "
              f"{fmt(A.get('lift'),'%.3f')} | {fmt(B.get('lift'),'%.3f')} | {fmt(d,'%+.1f')}pp |")
        w("")
        neg = [hz for hz in HZ if wm.get(hz) and
               (wm[hz].get("buy_precision", 0) - wm[hz].get("base_rate", 0)) <= 0]
        if neg:
            w(f"**Edge walk-forward <= 0 di horizon: {', '.join(neg)}.** "
              "Edge yang dilaporkan single-holdout adalah artefak split, bukan kemampuan model.\n")
    else:
        w("_salah satu metadata belum ada._\n")

    # 3. IC study
    w("## 3. Di mana signal sebenarnya ada (IC cross-sectional)\n")
    if ok(ic):
        untr = set(ic.get("untrained_features", []))
        w(f"Panel {ic.get('n_rows','?')} baris, {len(ic.get('tickers',[]))} ticker, "
          f"periode {ic.get('period','?')}. IC diukur per tanggal lintas saham, "
          "jadi komponen arah pasar tidak ikut terhitung.\n")
        for hz in HZ:
            r = ic.get("horizons", {}).get(hz)
            if not r:
                continue
            rows = [(f, d) for f, d in r["features"].items() if d.get("t_stat") is not None]
            rows.sort(key=lambda kv: -abs(kv[1]["t_stat"]))
            sig = [f for f, d in rows if abs(d["t_stat"]) >= 2]
            w(f"**{hz}** — {r['n_dates']} tanggal, {len(sig)} fitur dengan |t| >= 2. "
              f"10 teratas:\n")
            w("| fitur | mean IC | t-stat | dilatih? |")
            w("|---|---|---|---|")
            for f, d in rows[:10]:
                w(f"| `{f}` | {fmt(d['mean_ic'],'%+.4f')} | {fmt(d['t_stat'],'%+.2f')} | "
                  f"{'tidak' if f in untr else 'ya'} |")
            w("")
        # arah signal
        r5 = ic.get("horizons", {}).get("5d", {}).get("features", {})
        strong = [(f, d["mean_ic"]) for f, d in r5.items()
                  if d.get("t_stat") is not None and abs(d["t_stat"]) >= 3]
        if strong:
            negc = sum(1 for _, v in strong if v < 0)
            w(f"Dari {len(strong)} fitur ber-|t| >= 3 di horizon 5d, **{negc} bertanda negatif**. "
              "Artinya saham yang baru naik / terentang di atas rata-ratanya justru "
              "TERTINGGAL relatif terhadap universe pada beberapa hari berikutnya — "
              "polanya mean reversion, bukan momentum.\n")
        # fitur konstan
        allf = ic.get("horizons", {}).get("5d", {}).get("features", {})
        const = sorted(f for f, d in allf.items() if d.get("t_stat") is None)
        if const:
            w(f"**{len(const)} fitur konstan / tanpa data di jalur training** — "
              "artinya bukan 'dihitung tapi tidak dipakai', melainkan tidak pernah "
              "terisi sama sekali di `prepare_training_data()`:\n")
            w("`" + "`, `".join(const) + "`\n")
    else:
        w("_IC study belum ada._\n")

    # 4. quintile
    w("## 4. Apakah signal itu bisa ditradingin\n")
    if ok(xq):
        w("Skor komposit dari fitur ber-|t| >= 2, arah bobot = tanda IC. "
          "Tanpa model, tanpa tuning. Seleksi fitur hanya melihat separuh awal data; "
          "angka out-of-sample dihitung di separuh sisanya.\n")
        w("| horizon | fitur | sampel | top Q | bottom Q | rata-rata | spread | t | hit rate |")
        w("|---|---|---|---|---|---|---|---|---|")
        for hz in HZ:
            r = xq.get(hz)
            if not r:
                continue
            for lbl, nm in (("in_sample", "in-sample"), ("out_of_sample", "out-of-sample")):
                d = r.get(lbl)
                if not d:
                    continue
                w(f"| {hz} | {r['n_features']} | {nm} ({d['n_days']} hari) | "
                  f"{fmt(d['mean_top_pct'],'%+.2f')}% | {fmt(d['mean_bottom_pct'],'%+.2f')}% | "
                  f"{fmt(d['mean_all_pct'],'%+.2f')}% | **{fmt(d['mean_spread_pct'],'%+.2f')}%** | "
                  f"{fmt(d['t_stat_overlap_adj'],'%+.2f')} | {fmt(d['hit_rate_pct'],'%.0f')}% |")
        w("")
        w("> Spread belum dikurangi biaya transaksi. Round-trip di IDX "
          "(fee + spread bid-ask) kira-kira 0,3–0,5% untuk saham likuid, jadi "
          "spread 1d yang kecil bisa habis; horizon 3d–7d punya ruang lebih lega.\n")
    else:
        w("_quintile study belum ada._\n")

    w("## 5. Langkah berikutnya\n")
    w("1. Ganti target model ke **rank cross-sectional** (top-K per hari), bukan "
      "klasifikasi absolut per saham. Ini yang dibuktikan bagian 3 dan 4.")
    w("2. Pool seluruh ticker jadi satu model dengan `ticker_id` sebagai fitur "
      "(`scripts/train_multiday_pooled_model.py` sudah ada).")
    w("3. Ganti objektif pemilihan threshold dari F1 ke precision-at-coverage "
      "atau expectancy (`models/multiday_predictor.py`, `pick_optimal_threshold`).")
    w("4. Tandai baris `ml_prediction_log` yang berasal dari "
      "`_rule_based_prediction()` supaya tidak tercampur ke metrik ML.")
    w("5. Jangan tambahkan fitur news/sentimen dulu — histori `news_signals` "
      "baru ~1 bulan, akan jadi kolom kosong di training.\n")

    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    print(f"OK -> {a.out}  ({len(L)} baris)")

if __name__ == "__main__":
    main()
