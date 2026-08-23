# Laporan Model ML — 2026-08-22 19:19

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

Single-holdout: 65 ticker. Walk-forward: 3 ticker, 4 fold.

| horizon | edge holdout | edge walk-forward | lift holdout | lift WF | selisih |
|---|---|---|---|---|---|
| 1d | +5.2pp | -2.0pp | 1.160 | 0.943 | -7.2pp |
| 3d | +4.1pp | -2.3pp | 1.169 | 0.917 | -6.5pp |
| 5d | +5.0pp | -12.6pp | 1.166 | 0.584 | -17.6pp |
| 7d | +4.8pp | -5.5pp | 1.139 | 0.807 | -10.3pp |

**Edge walk-forward <= 0 di horizon: 1d, 3d, 5d, 7d.** Edge yang dilaporkan single-holdout adalah artefak split, bukan kemampuan model.

## 3. Di mana signal sebenarnya ada (IC cross-sectional)

Panel 5484 baris, 12 ticker, periode 2y. IC diukur per tanggal lintas saham, jadi komponen arah pasar tidak ikut terhitung.

**1d** — 456 tanggal, 22 fitur dengan |t| >= 2. 10 teratas:

| fitur | mean IC | t-stat | dilatih? |
|---|---|---|---|
| `close_vs_avg` | -0.1007 | -5.94 | ya |
| `close_to_low` | -0.0957 | -5.83 | ya |
| `dist_avg_7d` | -0.0807 | -4.55 | tidak |
| `ret_2d` | -0.0768 | -4.42 | ya |
| `ma_dist_5` | -0.0784 | -4.41 | ya |
| `stoch_k` | -0.0709 | -4.13 | ya |
| `ret_3d` | -0.0703 | -3.99 | ya |
| `stoch_d` | -0.0643 | -3.82 | ya |
| `close_to_high` | +0.0651 | +3.72 | ya |
| `ret_5d` | -0.0658 | -3.66 | ya |

**3d** — 454 tanggal, 27 fitur dengan |t| >= 2. 10 teratas:

| fitur | mean IC | t-stat | dilatih? |
|---|---|---|---|
| `stoch_k` | -0.1097 | -6.75 | ya |
| `close_vs_avg` | -0.0950 | -6.02 | ya |
| `ma_dist_5` | -0.1032 | -5.64 | ya |
| `dist_avg_7d` | -0.0963 | -5.32 | tidak |
| `bb_upper_dist` | -0.0876 | -5.27 | ya |
| `stoch_d` | -0.0859 | -5.23 | ya |
| `ret_2d` | -0.0927 | -5.17 | ya |
| `ret_3d` | -0.0902 | -5.07 | ya |
| `close_to_high` | +0.0804 | +5.02 | ya |
| `dist_avg_1m` | -0.0873 | -4.89 | tidak |

**5d** — 452 tanggal, 31 fitur dengan |t| >= 2. 10 teratas:

| fitur | mean IC | t-stat | dilatih? |
|---|---|---|---|
| `stoch_k` | -0.1194 | -7.69 | ya |
| `close_vs_avg` | -0.0990 | -6.29 | ya |
| `vwap_deviation_20d` | -0.1096 | -6.22 | ya |
| `stoch_d` | -0.0977 | -6.08 | ya |
| `bb_upper_dist` | -0.0977 | -5.97 | ya |
| `dist_avg_1m` | -0.1030 | -5.86 | tidak |
| `ma_dist_20` | -0.0988 | -5.52 | ya |
| `ma_dist_5` | -0.0971 | -5.34 | ya |
| `close_to_high` | +0.0860 | +5.26 | ya |
| `rsi` | -0.0849 | -5.22 | ya |

**7d** — 450 tanggal, 33 fitur dengan |t| >= 2. 10 teratas:

| fitur | mean IC | t-stat | dilatih? |
|---|---|---|---|
| `stoch_k` | -0.1235 | -7.73 | ya |
| `vwap_deviation_20d` | -0.1290 | -7.30 | ya |
| `stoch_d` | -0.1144 | -7.08 | ya |
| `dist_avg_1m` | -0.1246 | -7.07 | tidak |
| `ma_dist_20` | -0.1197 | -6.69 | ya |
| `bb_upper_dist` | -0.1021 | -6.47 | ya |
| `macd_hist` | -0.1091 | -6.10 | ya |
| `rsi` | -0.0989 | -6.08 | ya |
| `ob_imbalance_proxy_20d` | +0.0910 | +5.96 | ya |
| `ret_10d` | -0.1066 | -5.89 | ya |

Dari 26 fitur ber-|t| >= 3 di horizon 5d, **22 bertanda negatif**. Artinya saham yang baru naik / terentang di atas rata-ratanya justru TERTINGGAL relatif terhadap universe pada beberapa hari berikutnya — polanya mean reversion, bukan momentum.

**31 fitur konstan / tanpa data di jalur training** — artinya bukan 'dihitung tapi tidak dipakai', melainkan tidak pernah terisi sama sekali di `prepare_training_data()`:

`bandarm_score`, `commodity_score`, `day_of_week`, `dominance_score`, `haka_score`, `ihsg_ma_dist_20`, `ihsg_ret_1d`, `ihsg_ret_5d`, `ihsg_rsi`, `ihsg_trend`, `ihsg_trend_3d`, `ihsg_volatility`, `is_fomo_trap`, `is_retail_accum`, `news_count_30d`, `news_count_7d`, `news_score`, `news_sent_30d`, `news_sent_7d`, `report_count_30d`, `report_count_7d`, `report_sent_30d`, `report_sent_7d`, `resistance_proximity`, `retail_buy_ratio_7d`, `retail_sell_ratio_7d`, `support_proximity`, `top3_buy_ratio_1m`, `top3_buy_ratio_7d`, `top3_sell_ratio_1m`, `top3_sell_ratio_7d`

## 4. Apakah signal itu bisa ditradingin

Skor komposit dari fitur ber-|t| >= 2, arah bobot = tanda IC. Tanpa model, tanpa tuning. Seleksi fitur hanya melihat separuh awal data; angka out-of-sample dihitung di separuh sisanya.

| horizon | fitur | sampel | top Q | bottom Q | rata-rata | spread | t | hit rate |
|---|---|---|---|---|---|---|---|---|
| 1d | 8 | in-sample (229 hari) | +0.09% | -0.18% | -0.01% | **+0.28%** | +1.69 | 54% |
| 1d | 8 | out-of-sample (227 hari) | +0.36% | -0.29% | +0.04% | **+0.65%** | +3.73 | 62% |
| 3d | 25 | in-sample (229 hari) | +0.27% | -0.61% | -0.04% | **+0.88%** | +1.84 | 61% |
| 3d | 25 | out-of-sample (225 hari) | +0.62% | -0.54% | +0.09% | **+1.17%** | +2.48 | 62% |
| 5d | 29 | in-sample (229 hari) | +0.63% | -0.91% | -0.07% | **+1.53%** | +2.10 | 62% |
| 5d | 29 | out-of-sample (223 hari) | +0.81% | -0.44% | +0.12% | **+1.26%** | +1.69 | 60% |
| 7d | 33 | in-sample (229 hari) | +0.72% | -0.87% | -0.11% | **+1.59%** | +1.50 | 60% |
| 7d | 33 | out-of-sample (221 hari) | +0.97% | -0.48% | +0.15% | **+1.45%** | +1.30 | 62% |

> Spread belum dikurangi biaya transaksi. Round-trip di IDX (fee + spread bid-ask) kira-kira 0,3–0,5% untuk saham likuid, jadi spread 1d yang kecil bisa habis; horizon 3d–7d punya ruang lebih lega.

## 5. Langkah berikutnya

1. Ganti target model ke **rank cross-sectional** (top-K per hari), bukan klasifikasi absolut per saham. Ini yang dibuktikan bagian 3 dan 4.
2. Pool seluruh ticker jadi satu model dengan `ticker_id` sebagai fitur (`scripts/train_multiday_pooled_model.py` sudah ada).
3. Ganti objektif pemilihan threshold dari F1 ke precision-at-coverage atau expectancy (`models/multiday_predictor.py`, `pick_optimal_threshold`).
4. Tandai baris `ml_prediction_log` yang berasal dari `_rule_based_prediction()` supaya tidak tercampur ke metrik ML.
5. Jangan tambahkan fitur news/sentimen dulu — histori `news_signals` baru ~1 bulan, akan jadi kolom kosong di training.

