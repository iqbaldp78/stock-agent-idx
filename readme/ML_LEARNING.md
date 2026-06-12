# ML Learning Pipeline

Dokumen ini menjelaskan proses learning untuk meningkatkan akurasi prediksi Day-1 di project ini.

## Ringkasnya

Project ini memiliki model ML berbasis LightGBM untuk memprediksi return saham T+1.

File utama:

- `models/day1_predictor.py` — engine training dan inference
- `data/ml_features.py` — feature engineering dan target T+1
- `scripts/train_day1_model.py` — training model produksi
- `scripts/validate_ml_accuracy.py` — walk-forward validation
- `models/checkpoints/lgbm_day1.pkl` — model aktif yang dipakai workflow
- `models/checkpoints/lgbm_day1_meta.json` — metadata training terakhir

Jika file model belum ada, workflow tetap berjalan, tetapi `Day1Predictor` akan memakai rule-based fallback.

## Cara Training

Training semua ticker aktif di universe:

```bash
make train-ml
```

Training satu ticker:

```bash
make train-ml-ticker TICKER=BBCA
```

Atau langsung via Python:

```bash
python scripts/train_day1_model.py --all
python scripts/train_day1_model.py --tickers BBCA BMRI TLKM
```

Dengan konfigurasi custom:

```bash
python scripts/train_day1_model.py --all --period 1y --min-rows 120 --test-size 0.2
```

Secara default model hanya disimpan sebagai model aktif jika `Directional Accuracy` holdout minimal `50%`.

Jika tetap ingin menyimpan walaupun metrik di bawah threshold:

```bash
python scripts/train_day1_model.py --all --force-save
```

Output utama:

```text
models/checkpoints/lgbm_day1.pkl
models/checkpoints/lgbm_day1_meta.json
```

Setelah checkpoint tersimpan, workflow utama otomatis memakai model tersebut saat menjalankan ML Day-1 forecast.

## Auto Training Saat Full Analysis

Training ML otomatis dijalankan saat `run_full_analysis()` dipanggil. Ini berarti berlaku untuk:

- `make analysis-full`
- `make analysis-tickers TICKERS="BBCA BMRI"`
- tombol `Run Analysis Now` di Streamlit UI
- scheduler harian di `scheduler.py`

Auto training hanya dicoba **sekali per hari**. Jika hari yang sama sudah ada metadata di:

```text
models/checkpoints/lgbm_day1_meta.json
```

full analysis berikutnya akan skip training dan langsung lanjut ke pipeline analisis.

Quality gate tetap berlaku. Jika holdout `Directional Accuracy` di bawah threshold, model tidak disimpan sebagai model aktif dan workflow akan fallback ke rule-based prediction.

### Environment Variable

| Variable | Default | Keterangan |
| --- | --- | --- |
| `ML_AUTO_TRAIN` | `true` | Jalankan training otomatis sebelum full analysis |
| `ML_AUTO_TRAIN_PERIOD` | `1y` | Period OHLCV untuk training otomatis |
| `ML_AUTO_TRAIN_MIN_ROWS` | `120` | Minimum row training per ticker |
| `ML_AUTO_TRAIN_MIN_DIR_ACC` | `50.0` | Minimum directional accuracy agar model disimpan |
| `ML_AUTO_TRAIN_FORCE_SAVE` | `false` | Simpan model walaupun tidak lolos quality gate |
| `ML_MODEL_META_PATH` | `models/checkpoints/lgbm_day1_meta.json` | Path metadata untuk cek skip harian |

Contoh mematikan auto training:

```bash
ML_AUTO_TRAIN=false make analysis-full
```

Contoh menaikkan quality gate:

```bash
ML_AUTO_TRAIN_MIN_DIR_ACC=55 make analysis-full
```

## Cara Validasi

Validasi semua ticker:

```bash
make validate-ml
```

Validasi satu ticker:

```bash
make validate-ml-ticker TICKER=BBCA
```

Output:

```text
validate_ml_result.json
```

Hasil validasi juga bisa dilihat di UI:

```text
http://localhost:8501 → 📊 Performance → 🤖 ML Validation
```

## Cara Kerja Training

Script `scripts/train_day1_model.py` melakukan langkah berikut:

1. mengambil OHLCV historis dari Stockbit fetcher
2. fallback ke `yfinance` jika fetcher utama gagal atau period panjang tidak tersedia dari Stockbit
3. membuat fitur teknikal historis via `prepare_training_data()`
4. membuat target berupa return besok:

```python
target = Close.shift(-1) / Close - 1
```

5. membagi data tiap ticker menjadi train dan holdout berdasarkan urutan waktu
6. melatih model holdout untuk menghitung metrik awal
7. mengecek quality gate `Directional Accuracy >= 50%`
8. jika lolos, melatih ulang model final memakai seluruh data valid
9. menyimpan model ke `models/checkpoints/lgbm_day1.pkl`
10. menyimpan metadata dan metrik holdout ke `models/checkpoints/lgbm_day1_meta.json`

## Cara Baca Metrik

| Metrik | Arti |
| --- | --- |
| `Directional Accuracy` | Persentase prediksi arah naik/turun yang benar. Random baseline kira-kira `50%`. |
| `MAE` | Rata-rata error absolut prediksi return. Lebih kecil lebih baik. |
| `Buy Precision` | Dari semua prediksi BUY, berapa persen yang aktualnya naik. |
| `Buy Recall` | Dari semua hari yang aktualnya naik, berapa persen berhasil ditangkap sebagai BUY. |
| `Final Rows` | Jumlah baris training yang dipakai model final. |
| `Tickers Trained` | Jumlah ticker yang berhasil masuk training. |

Patokan awal:

- `Directional Accuracy < 50%` berarti model belum lebih baik dari tebakan arah acak
- `50% - 55%` masih perlu hati-hati
- `> 55%` mulai menarik untuk diuji lanjut
- `Buy Precision` lebih penting jika model dipakai sebagai filter entry
- `MAE` perlu dibandingkan dengan volatilitas rata-rata saham

## Integrasi ke Workflow

Workflow utama ada di `graph/workflow.py`.

Saat node ML berjalan:

```python
predictor = Day1Predictor()
```

`Day1Predictor` akan mencoba load:

```text
models/checkpoints/lgbm_day1.pkl
```

Jika berhasil, prediksi memakai model LightGBM. Jika gagal atau file tidak ada, prediksi memakai fallback rule-based.

Output ML dipakai sebagai bonus dalam ranking final:

- prediksi positif dapat menambah skor kandidat
- prediksi negatif atau `AVOID` dapat mengurangi skor

## Catatan Penting

Training saat ini terutama memakai fitur historis OHLCV. Beberapa fitur agent seperti bandarmologi, fundamental, dan macro diisi placeholder saat training historis karena data agent historis belum tersedia per tanggal.

Artinya:

- model sudah bisa belajar pola price action historis
- model belum sepenuhnya belajar dari histori output agent
- kualitas bisa meningkat lagi jika nanti menyimpan snapshot harian output agent ke database dan menjadikannya training data

## Workflow Rekomendasi

```bash
make train-ml
make validate-ml
make analysis-full
```

Urutannya:

1. `train-ml` membuat checkpoint model aktif
2. `validate-ml` mengukur performa walk-forward
3. `analysis-full` memakai model aktif di workflow scoring dan ranking
