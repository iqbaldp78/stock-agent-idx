# Laporan Model ML — 2026-08-22 22:36

Dibuat otomatis oleh `scripts/build_ml_report.py`. Semua angka lahir dari script yang bisa dijalankan ulang; tidak ada yang diketik tangan.

## 1. Kenyataan di log live

Periode **2026-08-08 → 2026-08-21** (11 hari bursa).

- BUY win rate: **37.0%** dari 365 sinyal (CI ±5.0pp)
- Base rate pasar: 34.3%
- Korelasi win rate harian vs breadth pasar: **+0.908** atas 46 hari-horizon
- Rata-rata edge harian: -0.02pp

| horizon | sinyal BUY | win rate | base rate | edge |
|---|---|---|---|---|
| 1d | 152 | 39.5% ±7.8 | 39.6% | -0.1pp |
| 3d | 93 | 35.5% ±9.7 | 32.6% | +2.8pp |
| 5d | 66 | 39.4% ±11.8 | 28.5% | +10.9pp |
| 7d | 54 | 29.6% ±12.2 | 32.3% | -2.7pp |

## 2. Single-holdout vs walk-forward

Single-holdout: 65 ticker. Walk-forward: 65 ticker, 4 fold.

| horizon | edge holdout | edge walk-forward | lift holdout | lift WF | selisih |
|---|---|---|---|---|---|
| 1d | +5.2pp | -1.6pp | 1.160 | 0.955 | -6.9pp |
| 3d | +4.1pp | -4.8pp | 1.169 | 0.821 | -9.0pp |
| 5d | +5.0pp | -4.7pp | 1.166 | 0.819 | -9.7pp |
| 7d | +4.8pp | -3.8pp | 1.139 | 0.853 | -8.6pp |

**Edge walk-forward <= 0 di horizon: 1d, 3d, 5d, 7d.** Edge yang dilaporkan single-holdout adalah artefak split, bukan kemampuan model.

## 3. Di mana signal sebenarnya ada (IC cross-sectional)

Panel 68159 baris, 65 ticker, periode 5y. IC diukur per tanggal lintas saham, jadi komponen arah pasar tidak ikut terhitung.

**1d** — 1155 tanggal, 28 fitur dengan |t| >= 2. 10 teratas:

| fitur | mean IC | t-stat | dilatih? |
|---|---|---|---|
| `close_to_low` | -0.0666 | -12.97 | ya |
| `close_vs_avg` | -0.0511 | -9.54 | ya |
| `ret_1d` | -0.0309 | -5.46 | ya |
| `stock_vs_ihsg_1d` | -0.0309 | -5.46 | ya |
| `ma_dist_5` | -0.0295 | -4.80 | ya |
| `close_to_high` | +0.0293 | +4.77 | ya |
| `day_foreign_net` | +0.0217 | +4.64 | ya |
| `dist_avg_7d` | -0.0261 | -4.55 | tidak |
| `ret_2d` | -0.0262 | -4.41 | ya |
| `bb_lower_dist` | -0.0265 | -3.98 | ya |

**3d** — 1153 tanggal, 19 fitur dengan |t| >= 2. 10 teratas:

| fitur | mean IC | t-stat | dilatih? |
|---|---|---|---|
| `close_to_low` | -0.0374 | -7.20 | ya |
| `close_vs_avg` | -0.0303 | -5.91 | ya |
| `close_to_high` | +0.0271 | +4.63 | ya |
| `vol_profile_20d_mid` | -0.0143 | -3.49 | tidak |
| `ma_dist_5` | -0.0181 | -3.04 | ya |
| `vol_profile_20d_upper` | +0.0146 | +2.93 | tidak |
| `dist_avg_7d` | -0.0160 | -2.84 | tidak |
| `ret_2d` | -0.0160 | -2.80 | ya |
| `vol_profile_20d_lower` | -0.0138 | -2.75 | tidak |
| `ret_1d` | -0.0148 | -2.70 | ya |

**5d** — 1151 tanggal, 15 fitur dengan |t| >= 2. 10 teratas:

| fitur | mean IC | t-stat | dilatih? |
|---|---|---|---|
| `close_to_low` | -0.0338 | -6.36 | ya |
| `close_vs_avg` | -0.0263 | -5.11 | ya |
| `vol_profile_20d_mid` | -0.0192 | -4.53 | tidak |
| `close_to_high` | +0.0245 | +4.14 | ya |
| `frequency_1d` | -0.0165 | -3.16 | ya |
| `ma_dist_50` | -0.0246 | -2.94 | ya |
| `vol_profile_20d_upper` | +0.0135 | +2.63 | tidak |
| `ret_1d_lag4` | +0.0134 | +2.40 | ya |
| `ma_dist_200` | +0.0316 | +2.35 | ya |
| `ret_1d` | -0.0123 | -2.20 | ya |

**7d** — 1149 tanggal, 10 fitur dengan |t| >= 2. 10 teratas:

| fitur | mean IC | t-stat | dilatih? |
|---|---|---|---|
| `vol_profile_20d_mid` | -0.0244 | -5.81 | tidak |
| `close_to_low` | -0.0262 | -4.94 | ya |
| `frequency_1d` | -0.0220 | -4.18 | ya |
| `ma_dist_50` | -0.0342 | -3.86 | ya |
| `close_vs_avg` | -0.0170 | -3.29 | ya |
| `close_to_high` | +0.0195 | +3.28 | ya |
| `ticker_id` | +0.0087 | +2.29 | tidak |
| `rsi` | -0.0190 | -2.23 | ya |
| `vol_profile_20d_upper` | +0.0117 | +2.20 | tidak |
| `ma_dist_200` | +0.0288 | +2.05 | ya |

Dari 5 fitur ber-|t| >= 3 di horizon 5d, **4 bertanda negatif**. Artinya saham yang baru naik / terentang di atas rata-ratanya justru TERTINGGAL relatif terhadap universe pada beberapa hari berikutnya — polanya mean reversion, bukan momentum.

**31 fitur konstan / tanpa data di jalur training** — artinya bukan 'dihitung tapi tidak dipakai', melainkan tidak pernah terisi sama sekali di `prepare_training_data()`:

`bandarm_score`, `commodity_score`, `day_of_week`, `dominance_score`, `haka_score`, `ihsg_ma_dist_20`, `ihsg_ret_1d`, `ihsg_ret_5d`, `ihsg_rsi`, `ihsg_trend`, `ihsg_trend_3d`, `ihsg_volatility`, `is_fomo_trap`, `is_retail_accum`, `news_count_30d`, `news_count_7d`, `news_score`, `news_sent_30d`, `news_sent_7d`, `report_count_30d`, `report_count_7d`, `report_sent_30d`, `report_sent_7d`, `resistance_proximity`, `retail_buy_ratio_7d`, `retail_sell_ratio_7d`, `support_proximity`, `top3_buy_ratio_1m`, `top3_buy_ratio_7d`, `top3_sell_ratio_1m`, `top3_sell_ratio_7d`

## 4. Apakah signal itu bisa ditradingin

Skor komposit dari fitur ber-|t| >= 2, arah bobot = tanda IC. Tanpa model, tanpa tuning. Seleksi fitur hanya melihat separuh awal data; angka out-of-sample dihitung di separuh sisanya.

| horizon | fitur | sampel | top Q | bottom Q | rata-rata | spread | t | hit rate |
|---|---|---|---|---|---|---|---|---|
| 1d | 20 | in-sample (579 hari) | +0.09% | +0.26% | +0.11% | **-0.18%** | -2.41 | 47% |
| 1d | 20 | out-of-sample (576 hari) | +0.33% | +0.24% | +0.18% | **+0.09%** | +0.91 | 53% |
| 3d | 7 | in-sample (579 hari) | +0.45% | +0.40% | +0.34% | **+0.06%** | +0.25 | 54% |
| 3d | 7 | out-of-sample (574 hari) | +1.06% | +0.20% | +0.54% | **+0.86%** | +3.26 | 60% |
| 5d | 5 | in-sample (579 hari) | +0.62% | +1.07% | +0.59% | **-0.46%** | -1.09 | 45% |
| 5d | 5 | out-of-sample (572 hari) | +0.98% | +1.34% | +0.92% | **-0.35%** | -0.77 | 47% |
| 7d | 6 | in-sample (579 hari) | +0.95% | +1.48% | +0.83% | **-0.53%** | -0.90 | 46% |
| 7d | 6 | out-of-sample (570 hari) | +1.17% | +2.36% | +1.31% | **-1.19%** | -1.71 | 41% |

> Spread belum dikurangi biaya transaksi. Round-trip di IDX (fee + spread bid-ask) kira-kira 0,3–0,5% untuk saham likuid, jadi spread 1d yang kecil bisa habis; horizon 3d–7d punya ruang lebih lega.

## 5. Langkah berikutnya

1. Ganti target model ke **rank cross-sectional** (top-K per hari), bukan klasifikasi absolut per saham. Ini yang dibuktikan bagian 3 dan 4.
2. Pool seluruh ticker jadi satu model dengan `ticker_id` sebagai fitur (`scripts/train_multiday_pooled_model.py` sudah ada).
3. Ganti objektif pemilihan threshold dari F1 ke precision-at-coverage atau expectancy (`models/multiday_predictor.py`, `pick_optimal_threshold`).
4. Tandai baris `ml_prediction_log` yang berasal dari `_rule_based_prediction()` supaya tidak tercampur ke metrik ML.
5. Jangan tambahkan fitur news/sentimen dulu — histori `news_signals` baru ~1 bulan, akan jadi kolom kosong di training.

