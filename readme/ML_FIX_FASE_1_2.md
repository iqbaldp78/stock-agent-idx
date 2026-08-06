# Perbaikan Model LightGBM — Fase 1 & 2

Runbook · 6 Agustus 2026

Dua masalah pokok yang diperbaiki: model tidak bisa dinilai karena metriknya tidak
mencatat pembanding, dan sebagian input yang diterimanya saat inference berbeda dari
yang dipelajarinya saat training. **Fase 1** memperbaiki alat ukurnya, **Fase 2**
menyatukan definisi fiturnya.

| | |
|---|---|
| File berubah | 11 (+1 file baru) |
| Fitur skew ditutup | 15 (14 rumus + 1 window) |
| Fitur dari satu sumber | 58 dari 60 fitur training |
| Butuh retraining? | **Tidak** — training jadi acuan, live yang disesuaikan |

> **Baca ini dulu.** Fase 1 dan 2 **tidak membuat model lebih pintar.** Fase 1 membuat
> angkanya jujur — jadi angka yang tampil akan terlihat *lebih buruk*, dan itu tanda
> berhasil. Fase 2 membuat model menerima input yang benar. Menaikkan plafon
> kemampuannya adalah Fase 3.

---

## A. Apa yang berubah

### Fase 1 — alat ukur (tidak menyentuh model)

Akar masalahnya: metadata mencatat `accuracy` tapi tidak pernah mencatat `base_rate`.
Tanpa pembanding itu, angka 58% terlihat bagus padahal ada di bawah baseline "selalu
jawab tidak naik".

| File | Perubahan | Kenapa |
|---|---|---|
| `scripts/train_multiday_model.py` | `evaluate_multiday_model()` mencatat `base_rate`, `majority_baseline`, `lift`, `n_predicted_positive`, `degenerate` | Aditif — key lama tidak berubah, jadi UI dan `compare_multiday_metrics.py` tetap jalan |
| `scripts/train_multiday_model.py` | `aggregate_metrics()` dipindah ke module level dan mengeluarkan model degenerate dari headline | Dulu nested di `main()` sehingga tidak bisa diimpor. 8–16 model per horizon yang tak pernah sinyal BUY ikut menaikkan rata-rata |
| `scripts/train_multiday_pooled_model.py` | Pakai `aggregate_metrics` bersama, duplikatnya dihapus | Menghilangkan jalur agregasi kedua |
| `scripts/update_streamlit_metadata.py` | Jalur metrik duplikat **dihapus**, diganti panggilan ke fungsi bersama. Kini `exit 1` kalau tak ada model ter-load | Punya 3 bug: `predict()` dipakai seolah probabilitas, `feature_name()` yang tak ada, default threshold 0.55. Hilang karena penghapusan kode, bukan tambalan |
| `ui/app.py` | Kolom Base/Lift + tanda ⚠️ per ticker; `st.metric(delta=…)`; penjelasan metrik ditulis ulang | `delta` negatif diwarnai merah otomatis oleh Streamlit — accuracy di bawah baseline jadi tak bisa terlewat |
| `models/multiday_predictor.py` | Warning saat threshold mentok di batas rentang; warning saat model tak ditemukan; method `has_model()` | Dulu `logger.debug` — tidak tercetak di level produksi, sehingga fallback rule-based berjalan tanpa jejak |

### Fase 2 — satu sumber kebenaran fitur

`prepare_training_data()` dan `extract_features()` adalah dua implementasi terpisah
untuk fitur yang sama. Selama keduanya ada, mereka akan terus melenceng. Sekarang
keduanya memanggil `compute_ohlcv_features()`: training memakai seluruh frame, live
memakai `.iloc[-1]`.

| File | Perubahan | Kenapa |
|---|---|---|
| `data/ml_features.py` | `compute_ohlcv_features()` — satu definisi untuk 58 dari 60 fitur training | Isinya **dipindahkan** dari jalur training, bukan ditulis ulang, karena itulah definisi yang sudah dipelajari model |
| `data/ml_features.py` | 10 fitur konstan dipindah ke `ML_TRAIN_FEATURES_EXCLUDED` | Konstan di training tapi bervariasi di live — strictly lebih buruk daripada tidak ada fiturnya |
| `data/ml_features.py` | Blok fitur sektor dihapus | Menghitung skalar dari tanggal terakhir lalu menyiarkannya ke semua baris — baris 2019 menerima nilai 2026. Look-ahead penuh |
| `graph/workflow.py`, `graph/konglo_workflow.py` | Window fetch `3mo` → `2y`, plus `MIN_HISTORY_ROWS` + warning | **Skew ke-15.** `ma_dist_200` butuh 200 baris; dengan 3mo (~60 baris) nilainya selalu 0.0 di live tapi nyata di training |
| `models/day1_predictor.py`, `scripts/run_full_ml_pipeline.py` | `_model_feature_names()` memakai `feature_name_` | `hasattr(model,"feature_name")` **selalu** False untuk `LGBMRegressor`. Tanpa perbaikan ini, mengurangi `ML_TRAIN_FEATURES` membuat model lama crash |
| `scripts/check_feature_parity.py` **(baru)** | Bandingkan fitur training vs live; mode `--live-rows` untuk mensimulasikan window pendek | Penjaga agar kelas bug ini tidak kembali. Bug ini tak pernah memunculkan error — hanya prediksi yang salah dengan tenang |

**Lima skew hilang secara konstruksi, bukan ditambal:** `rsi`, `vol_ratio`, dan
`is_bullish_trend` berhenti diparse dari teks agent; `day_of_week` otomatis benar karena
diambil dari index tanggal bar; `vol_trend_5d` dan `close_to_high` hanya punya satu
rumus sehingga tidak mungkin beda.

---

## B. Yang dijalankan di server

Semua dari root repo. Service ML adalah `app` (container `stock_app`). Karena
`docker-compose.yml` bind-mount `.:/app`, file yang ditulis di container langsung muncul
di disk host — tidak perlu `docker cp`. **Jalankan berurutan.**

### 00 · Backup — WAJIB

Model di server adalah satu-satunya salinan (tidak pernah masuk git karena
`models/checkpoints/.gitignore` berisi `*`). Training akan menimpanya.

```bash
docker compose exec app bash -c '
  D=models/checkpoints_backup_$(date +%Y%m%d_%H%M%S)
  mkdir -p "$D" && cp -a models/checkpoints/. "$D"/
  echo "Backup: $D"
  ls "$D"/*.pkl 2>/dev/null | wc -l'
```

**Gate:** angka terakhir harus **> 0**. Kalau 0, **berhenti** —
`models/checkpoints/` di server juga kosong dan asumsi dasar runbook ini salah.

### 01 · Apakah pilar bandarmologi masuk ke model?

Langkah ini **bisa membalik seluruh prioritas**, karena itu dijalankan lebih dulu.

```bash
docker compose exec app python3 -c "
import json, glob
files = sorted(glob.glob('models/checkpoints/lgbm_*_1d_features.json'))
print('sidecar diperiksa:', len(files))
keys = ['day_foreign_net','foreign_net_7d','foreign_net_1m','foreign_flow_zscore']
missing = {k: 0 for k in keys}
for p in files:
    f = json.load(open(p))['selected_features']
    for k in keys:
        if k not in f: missing[k] += 1
for k, v in missing.items():
    print(f'{k:24} tidak dipakai di {v}/{len(files)} model')"
```

**Percabangan:**

- Fitur foreign **hilang di mayoritas model** → model dilatih saat bug `NetForeign`
  masih aktif (diperbaiki commit `5bfe8cd`). Artinya bobot 40% sistem tidak pernah masuk
  model, dan **retraining melompat ke prioritas 1**.
- Fitur foreign **ada** → lanjut normal.

### 02 · Paritas fitur — harus LULUS

Inti Fase 2. Membandingkan baris terakhir fitur training dengan output live untuk OHLCV
yang sama.

```bash
make check-feature-parity
```

**Ekspektasi:** `LULUS: semua fitur training dan live inference cocok.` — exit code 0.

**Kalau gagal:** output menyebut nama fitur + kolom rasio. Rasio ~200 menandakan bug
skala, rasio negatif menandakan tanda terbalik. Kirim outputnya — daftar itu langsung
menunjukkan apa yang belum beres.

### 03 · Uji detektor window pendek — harus GAGAL

Langkah ini **sengaja** harus gagal. Ia membuktikan detektornya bekerja, bukan
menandakan ada masalah.

```bash
make check-feature-parity-shortwindow
```

**Ekspektasi:** gagal, menyebut `ma_dist_200` (dan mungkin `ma_dist_50`) — exit code 1.
Live hanya diberi 60 baris sementara `ma_dist_200` butuh 200.

**Kalau ia LULUS**, detektor window pendek tidak berfungsi dan perlu diperiksa. Itu
bukan kabar baik.

### 04 · Metrik jujur — tanpa retraining

Memuat model yang *sudah ada* dan mengevaluasinya. Inilah alat utama Fase 1.

```bash
make update-ml-metadata

docker compose exec app python3 -c "
import json; m = json.load(open('models/checkpoints/lgbm_multiday_meta.json'))
print(f\"{'H':<4}{'acc':>8}{'baseline':>10}{'lift':>8}{'usable':>8}{'degen':>7}\")
for h, v in m['holdout_metrics_macro_avg'].items():
    print(f\"{h:<4}{v['accuracy']:>7.2f}%{v['majority_baseline']:>9.2f}%\"
          f\"{v['lift']:>8.3f}{v['n_usable']:>8}{v['n_degenerate']:>7}\")"
```

Ekspektasi angkanya ada di bagian C.

### 05 · Retrain — opsional di tahap ini

Fase 1 & 2 tidak mewajibkan retraining. Lakukan hanya kalau Langkah 01 menunjukkan fitur
foreign tidak masuk model.

**5a. Dry run** — `--validate-only` tidak menimpa model produksi (menulis ke
`lgbm_multiday_val_meta.json`, dan `fit_final_model()` di-skip):

```bash
docker compose exec app python scripts/train_multiday_model.py \
  --tickers BBCA --period max --validate-only
```

**5b. Ukur satu ticker** untuk estimasi total. Tiap ticker ≈ 180–240 fit LightGBM
(4 horizon × 15 iter × 3–4 fold):

```bash
docker compose exec app bash -c '
  time python scripts/train_multiday_model.py --tickers BBCA --period max'
```

**5c. Retrain penuh, detached.** Kalikan hasil 5b dengan 64. Kalau > 1 jam, wajib
detached — SSH terputus akan membunuh proses foreground:

```bash
docker compose exec -d app bash -c '
  python scripts/train_multiday_model.py --all --period max \
    > /app/logs_retrain.txt 2>&1'

tail -f logs_retrain.txt   # bind mount, langsung terlihat di host
```

**5d. Verifikasi model benar-benar tertulis** — ini yang sekarang tidak pernah diperiksa;
script hanya mencetak "Models saved to..." tanpa memvalidasi apa pun:

```bash
docker compose exec app bash -c '
  echo "pkl  : $(ls models/checkpoints/lgbm_*_[1357]d.pkl 2>/dev/null | wc -l)"
  echo "feat : $(ls models/checkpoints/*_features.json 2>/dev/null | wc -l)"
  echo "thr  : $(ls models/checkpoints/*_threshold.json 2>/dev/null | wc -l)"
  echo "baru : $(ls -t models/checkpoints/*.pkl | head -1)"'
```

**Ekspektasi:** ketiga angka sama (≈256 = 64 ticker × 4 horizon) dan file terbaru
bertanggal hari ini.

---

## C. Ekspektasi vs hasil nyata

Kolom kanan untuk diisi saat menjalankan. Ekspektasi diturunkan dari rekonstruksi
confusion matrix metadata 3 Agustus, bukan tebakan.

| Langkah | Yang diukur | Ekspektasi | Hasil nyata |
|---|---|---|---|
| 00 | Jumlah `.pkl` di backup | > 0 (idealnya ~256) | |
| 01 | Fitur foreign di `selected_features` | Belum diketahui — **inilah yang dicari** | |
| 02 | Paritas fitur | **LULUS**, exit 0 | |
| 03 | Detektor window pendek | **GAGAL**, exit 1, sebut `ma_dist_200` | |
| 04 | Ticker punya model | 64 (bukan 0) | |
| 04 | `lift` 1d | ≈ 1.05 | |
| 04 | `lift` 7d | ≈ 1.13 | |
| 04 | `accuracy` vs `majority_baseline` | −4 s/d −8 pp (**di bawah**) | |
| 04 | `n_degenerate` per horizon | 8 – 16 | |
| 05d | Jumlah `.pkl` setelah retrain | ≈ 256, ketiga angka sama | |

### Cara membaca lift

`lift = buy_precision / base_rate`. **1.00 = nol skill** — sinyal BUY tidak lebih baik
daripada menebak sesuai proporsi pasar.

- Kalau `lift ≈ 1.00`, model existing tidak punya skill sama sekali dan Fase 3 jadi
  lebih mendesak daripada apa pun di runbook ini.
- Kalau `lift` jauh **di atas** 1.13, curigai kebocoran — bukan keberhasilan.

### Yang tidak akan terjadi

- `lift` tidak akan melompat dari 1.07 ke 1.5. Fase 2 memindahkan prediksi live dari
  "input salah" ke "input benar", jadi performa live seharusnya *mendekati* angka
  backtest — bukan melampauinya.
- `accuracy` tidak akan naik. Ia akan tampak *turun* karena kini dihitung dari model
  usable saja dan didampingi baseline.
- Ranking Top Picks **akan berubah** setelah Fase 2, karena nilai fitur yang dikirim ke
  model berubah nyata. Itu diharapkan — sebelumnya inputnya salah — tapi berarti hasil
  sebelum dan sesudah tidak bisa dibandingkan langsung.

---

## D. Validasi & regresi

### Konsumen metadata tidak pecah

```bash
docker compose exec app python scripts/compare_multiday_metrics.py
docker compose restart streamlit   # lalu buka tab ML Predictions
```

`accuracy` dan `buy_precision` akan **melompat sekali** karena kini dihitung dari model
usable saja. Bandingkan lewat `accuracy_all_models` untuk melihat angka setara run lama.

### Live memakai model, bukan fallback

```bash
docker compose exec app python3 -c "
from models.multiday_predictor import MultiDayPredictor
p = MultiDayPredictor(ticker='BBCA')
print('ter-load:', {h: p.models[h] is not None for h in p.horizons})
print('threshold:', p.thresholds)"
```

Keempat horizon harus `True`. Kalau ada `False`, sekarang akan ada `logger.warning` yang
menjelaskan sebabnya — dulu senyap.

### Fitur konstan

```bash
docker compose exec app python3 -c "
import json; m = json.load(open('models/checkpoints/lgbm_multiday_meta.json'))
c = m.get('constant_features_all_tickers')
print('konstan di SEMUA ticker:', c)
bad = [x for x in (c or []) if 'foreign' in x or 'bandar' in x]
print('MASALAH:', bad) if bad else print('OK: fitur foreign bervariasi')"
```

Hanya terisi setelah retraining. Sebelumnya `null` karena metadata dibuat oleh versi
script sebelum commit `5bfe8cd` — instrumen `find_constant_features()` sudah ada tapi
belum pernah dijalankan.

### Sanity check di UI

Prediksi 1d/3d/5d/7d harus **berbeda** satu sama lain. Kalau keempatnya identik,
`_rule_based_prediction()` masih terpakai — fungsi itu menerima parameter `horizon` tapi
tidak pernah memakainya.

### Rollback

```bash
docker compose exec app bash -c 'ls -dt models/checkpoints_backup_* | head -1'
docker compose exec app bash -c \
  'cp -a models/checkpoints_backup_<TIMESTAMP>/. models/checkpoints/'
docker compose restart app streamlit
```

---

## E. Yang belum dikerjakan

| Item | Status | Catatan |
|---|---|---|
| Verifikasi runtime | **belum** | Mesin dev tidak punya numpy maupun docker. Yang sudah: compile semua file, analisis AST nama tak terdefinisi (menangkap satu `NameError` nyata), uji `aggregate_metrics` dari source dengan numpy distub, dan bukti 14 fitur skewed punya tepat satu tempat penugasian. Bukti struktural — **bukan** pengganti menjalankannya |
| Bonus composite di `graph/workflow.py` | menunggu keputusan | Tidak masuk plan yang disetujui, jadi tidak dikerjakan sendiri. `has_model()` sudah tersedia — tinggal `and predictor.has_model('1d')` |
| Bug label baris terakhir | Fase 3 | `(Close.shift(-7) > x).astype(int)` → `NaN > x` jadi `False` → `0`. Tujuh baris terakhir dilabeli "tidak naik" padahal hasilnya belum diketahui, dan `dropna` tidak membuangnya. Diperparah time-decay weight 3× ke baris terbaru |
| Pooled model + label volatility-scaled | Fase 3 | Lever terbesar. Lift turun monoton seiring data bertambah (2.50 → 1.24 → 1.08 → 1.07) — tanda variance dominan, persis kondisi di mana pooling menang |
| Gate go/no-go biaya transaksi | Fase 3 | `scripts/evaluate_profit_metrics.py` — apakah lift ~1.07 menutup biaya round-trip IDX (~0.3–0.5%)? Kalau tidak, Fase 3 harus berupa perubahan pendekatan, bukan penyempurnaan model ini |
| Commit | belum | Semua masih di working tree |

---

## Referensi

- Rencana + status implementasi: `/root/.claude/plans/wild-enchanting-honey.md`
- Versi HTML runbook ini: https://claude.ai/code/artifact/b1e3791f-3de5-46cd-91ed-f709323bb8e7
- Metrik ML lain: [`ML_LEARNING.md`](ML_LEARNING.md)
