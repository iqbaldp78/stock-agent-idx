# Historical Signal Backtest

Dokumen ini menjelaskan cara menjalankan backtest sinyal historis di project ini. Backtest memakai strategi rule-based sederhana dari data OHLCV historis, tanpa LLM, sehingga cocok untuk validasi awal kualitas sinyal teknikal sebelum dipakai dalam workflow analisis yang lebih besar.

## Overview

Script utama:

```bash
scripts/backtest_signals.py
```

Backtest akan:

- mengambil data OHLCV per ticker dari Stockbit fetcher, lalu fallback ke `yfinance` jika fetcher utama gagal
- menghitung indikator teknikal dasar
- membuat sinyal `BUY` berdasarkan aturan trend, RSI, momentum, dan volume
- mensimulasikan exit dengan target profit dan stop loss dalam beberapa hari ke depan
- menampilkan ringkasan performa di terminal
- menyimpan hasil lengkap ke file JSON

## Strategy

Strategi default sengaja dibuat konservatif supaya tidak terlalu sering menghasilkan trade.

Sinyal `BUY` muncul jika semua kondisi berikut terpenuhi:

- `Close > MA20 > MA50`
- `RSI` berada di rentang `45` sampai `72`
- return 5 hari terakhir lebih besar dari `-3%`
- volume ratio terhadap MA20 volume berada di rentang `0.7` sampai `3.0`

Jika salah satu kondisi tidak terpenuhi, sinyal dianggap `HOLD` dan tidak dibuat trade.

## Simulasi Trade

Saat sinyal `BUY` muncul:

- entry memakai harga `Close` pada hari sinyal
- default holding period adalah `5` hari
- exit dicek dari `T+1` sampai `T+5`
- jika dalam candle yang sama menyentuh stop loss dan target profit, stop loss dihitung lebih dulu untuk pendekatan konservatif

Level default:

| Level | Nilai |
| --- | ---: |
| TP1 | `+3%` |
| TP2 | `+5%` |
| TP3 | `+8%` |
| SL | `-3%` |

Jika tidak ada TP atau SL yang tersentuh sampai batas holding period, trade keluar dengan status `TIME_EXIT` memakai harga close di hari terakhir simulasi.

## Cara Menjalankan

Jalankan command dari root project.

### Via Makefile

Backtest semua ticker universe:

```bash
make backtest
```

Backtest satu ticker:

```bash
make backtest-ticker TICKER=BBCA
```

Command Makefile menjalankan script di dalam container `app`:

```bash
docker compose exec app python scripts/backtest_signals.py --all
docker compose exec app python scripts/backtest_signals.py --tickers BBCA
```

### Via Python Langsung

Beberapa ticker:

```bash
python scripts/backtest_signals.py --tickers BBCA BMRI TLKM
```

Semua ticker universe:

```bash
python scripts/backtest_signals.py --all
```

Dengan rentang tanggal tertentu:

```bash
python scripts/backtest_signals.py --tickers BBCA --start 2024-01-01 --end 2024-12-31
```

Dengan period dan holding period custom:

```bash
python scripts/backtest_signals.py --tickers BBCA BMRI --period 2y --holding-days 10
```

Dengan nama output custom:

```bash
python scripts/backtest_signals.py --tickers BBCA --output backtest_bbca.json
```

## Melihat Hasil di UI

Hasil backtest bisa dibaca langsung dari Streamlit dashboard.

Start service jika belum jalan:

```bash
make up
```

Buka:

```text
http://localhost:8501
```

Lalu pilih menu:

```text
🧪 Backtest
```

UI akan membaca file default:

```bash
backtest_result.json
```

Jika file belum ada, jalankan salah satu command berikut:

```bash
make backtest
```

atau:

```bash
python scripts/backtest_signals.py --tickers BBCA BMRI --output backtest_result.json
```

Catatan: jika menjalankan UI lewat Docker Compose, folder project di-mount ke `/app`, sehingga `backtest_result.json` di root project akan terbaca oleh container Streamlit.

## Parameter CLI

| Parameter | Wajib | Default | Keterangan |
| --- | --- | --- | --- |
| `--tickers` | Ya, jika tidak pakai `--all` | - | Daftar ticker, contoh `BBCA BMRI` |
| `--all` | Ya, jika tidak pakai `--tickers` | `False` | Ambil semua ticker aktif dari tabel universe |
| `--period` | Tidak | `1y` | Period OHLCV jika `--start` dan `--end` tidak diisi |
| `--start` | Tidak | - | Tanggal mulai format `YYYY-MM-DD` |
| `--end` | Tidak | - | Tanggal akhir format `YYYY-MM-DD` |
| `--holding-days` | Tidak | `5` | Maksimal hari hold setelah sinyal |
| `--output` | Tidak | `backtest_result.json` | File JSON hasil backtest |

`--tickers` dan `--all` bersifat mutually exclusive, jadi hanya boleh pilih salah satu.

## Output Terminal

Output terminal menampilkan ringkasan per ticker dan agregat semua trade.

Kolom utama:

| Kolom | Arti |
| --- | --- |
| `Trades` | Jumlah trade yang muncul dari sinyal `BUY` |
| `WinRate` | Persentase trade dengan return positif |
| `AvgRet` | Rata-rata return per trade |
| `PF` | Profit factor, yaitu gross profit dibagi gross loss |
| `MaxDD` | Maximum drawdown dari urutan return trade |
| `Best` | Return trade terbaik |
| `Worst` | Return trade terburuk |

Contoh bentuk output:

```text
====================================================================================
  HISTORICAL SIGNAL BACKTEST SUMMARY
====================================================================================
Ticker    Trades   WinRate    AvgRet      PF     MaxDD     Best    Worst
------------------------------------------------------------------------------------
BBCA          12     58.3%    +1.12%    1.80    -4.20%   +5.00%   -3.00%
BMRI           9     44.4%    +0.35%    1.18    -6.10%   +8.00%   -3.00%
------------------------------------------------------------------------------------
ALL           21     52.4%    +0.79%    1.45    -7.30%   +8.00%   -3.00%
====================================================================================
```

## Output JSON

Default hasil disimpan ke:

```bash
backtest_result.json
```

Struktur utama:

```json
{
  "run_date": "2026-06-13T10:00:00",
  "config": {
    "period": "1y",
    "start": null,
    "end": null,
    "holding_days": 5,
    "strategy": "close_gt_ma20_gt_ma50_rsi45_72_ret5d_gt_minus3_vol07_3"
  },
  "aggregate": {
    "trades": 21,
    "win_rate": 52.38,
    "avg_return_pct": 0.79,
    "median_return_pct": 1.2,
    "profit_factor": 1.45,
    "max_drawdown_pct": -7.3,
    "best_trade_pct": 8.0,
    "worst_trade_pct": -3.0
  },
  "tickers": {
    "BBCA": {
      "ticker": "BBCA",
      "rows": 240,
      "summary": {},
      "trades": []
    }
  }
}
```

Setiap item `trades` berisi:

| Field | Keterangan |
| --- | --- |
| `ticker` | Kode saham |
| `signal` | Sinyal yang memicu trade, saat ini `BUY` |
| `entry_date` | Tanggal entry |
| `exit_date` | Tanggal exit |
| `entry_price` | Harga entry |
| `exit_price` | Harga exit |
| `result` | `HIT_TP1`, `HIT_TP2`, `HIT_TP3`, `HIT_SL`, atau `TIME_EXIT` |
| `return_pct` | Return trade dalam persen |
| `holding_days` | Jumlah hari simulasi |
| `rsi` | RSI saat sinyal muncul |
| `ma20` | MA20 saat sinyal muncul |
| `ma50` | MA50 saat sinyal muncul |

## Universe Ticker

Jika memakai `--all`, script mencoba mengambil ticker aktif dari tabel `Universe` di database:

```python
db.query(Universe.ticker).filter(Universe.active == True).all()
```

Jika database tidak tersedia atau universe kosong, script fallback ke daftar default:

```text
BBCA, BBRI, BMRI, TLKM, ASII, UNVR, ICBP, KLBF, ANTM, INDF
```

## Interpretasi Hasil

Gunakan hasil backtest sebagai validasi awal, bukan jaminan performa real trading.

### Cara Baca Metrik Utama

| Metrik | Cara baca |
| --- | --- |
| `Trades` | Jumlah sinyal `BUY` yang benar-benar disimulasikan menjadi trade. Semakin kecil jumlahnya, semakin hati-hati membaca metrik lain. |
| `Win Rate` | Persentase trade dengan return positif. Win rate tinggi belum tentu bagus jika loss jauh lebih besar dari profit. |
| `Avg Return` | Rata-rata return per trade. Positif berarti trade historis rata-rata untung sebelum biaya dan slippage. |
| `Median Return` | Nilai tengah return. Berguna untuk melihat apakah performa ditopang banyak trade bagus atau hanya beberapa outlier. |
| `Profit Factor` | Gross profit dibagi gross loss. Nilai `> 1` berarti total profit lebih besar dari total loss; `> 1.5` biasanya lebih menarik untuk diteliti lanjut. |
| `Max Drawdown` | Penurunan terdalam dari kurva return trade. Semakin negatif, semakin besar tekanan risiko historis. |
| `Best Trade` | Return trade terbaik. Di strategi default biasanya dibatasi oleh TP tertinggi, yaitu sekitar `+8%`. |
| `Worst Trade` | Return trade terburuk. Di strategi default biasanya sekitar `-3%` karena stop loss. |

### Cara Baca Tab UI

Halaman `🧪 Backtest` memiliki beberapa tab.

#### Summary per Ticker

Tab ini membandingkan performa setiap ticker.

Gunakan tab ini untuk menjawab:

- ticker mana yang paling sering menghasilkan sinyal
- ticker mana yang punya `avg_return_pct` paling baik
- ticker mana yang profit factor-nya sehat
- ticker mana yang drawdown-nya terlalu besar

Cara baca cepat:

- `trades` minimal perlu cukup banyak sebelum metrik dianggap bermakna
- `avg_return_pct` positif lebih baik, tapi cek juga `max_drawdown_pct`
- `profit_factor > 1` berarti total profit historis lebih besar dari total loss
- ticker dengan `win_rate` bagus tapi `profit_factor` rendah biasanya punya loss yang cukup merusak
- ticker dengan trade sangat sedikit tidak boleh langsung dianggap superior

#### Trades

Tab ini menampilkan semua trade hasil simulasi.

Gunakan filter:

- `Ticker` untuk fokus ke satu saham
- `Result` untuk melihat hanya trade yang `HIT_SL`, `HIT_TP1`, `HIT_TP2`, `HIT_TP3`, atau `TIME_EXIT`

Kolom penting:

| Kolom | Cara baca |
| --- | --- |
| `entry_date` | Tanggal sinyal `BUY` muncul dan entry dilakukan di close hari itu |
| `exit_date` | Tanggal trade keluar karena TP, SL, atau time exit |
| `entry_price` | Harga close saat entry |
| `exit_price` | Harga exit hasil simulasi |
| `result` | Alasan exit trade |
| `return_pct` | Return trade dalam persen |
| `rsi` | Kondisi RSI saat entry |
| `ma20` / `ma50` | Moving average saat entry, dipakai untuk validasi trend |

Makna `result`:

| Result | Arti |
| --- | --- |
| `HIT_TP1` | Harga menyentuh target profit pertama, sekitar `+3%` |
| `HIT_TP2` | Harga menyentuh target profit kedua, sekitar `+5%` |
| `HIT_TP3` | Harga menyentuh target profit ketiga, sekitar `+8%` |
| `HIT_SL` | Harga menyentuh stop loss, sekitar `-3%` |
| `TIME_EXIT` | Tidak kena TP/SL sampai holding period habis, keluar di close hari terakhir |

Cara baca cepat:

- banyak `HIT_TP1` berarti sinyal cukup sering memberi pantulan pendek
- banyak `HIT_TP3` berarti ada momentum lanjutan yang kuat
- banyak `HIT_SL` beruntun bisa menandakan strategi tidak cocok untuk ticker atau periode itu
- banyak `TIME_EXIT` berarti target/SL tidak sering tercapai dalam holding period

#### Errors

Tab ini menampilkan ticker yang gagal diproses.

Error paling umum:

- data OHLCV terlalu sedikit
- ticker tidak valid
- fetcher Stockbit dan fallback `yfinance` gagal
- koneksi data provider bermasalah

Jika tab ini kosong, semua ticker yang diminta berhasil diproses.

#### Raw JSON

Tab ini menampilkan isi `backtest_result.json` apa adanya.

Gunakan tab ini jika ingin:

- debug struktur data
- copy hasil ke script lain
- memastikan config backtest yang sedang tampil
- melihat detail yang belum dibuat kolom khusus di UI

### Contoh Cara Membaca Hasil

Misalnya hasil agregat menunjukkan:

```text
Trades: 20
Win Rate: 55.0%
Avg Return: +1.35%
Profit Factor: 2.00
Max Drawdown: -11.55%
Best Trade: +8.00%
Worst Trade: -3.00%
```

Interpretasi praktis:

- ada 20 trade historis, jumlahnya lumayan untuk inspeksi awal tapi belum cukup untuk kesimpulan final
- `Win Rate 55%` berarti sedikit lebih banyak trade profit daripada loss
- `Avg Return +1.35%` menunjukkan ekspektasi historis per trade positif sebelum biaya
- `Profit Factor 2.00` berarti total profit sekitar dua kali total loss
- `Max Drawdown -11.55%` berarti urutan trade pernah mengalami penurunan akumulatif cukup dalam
- karena `Worst Trade -3%`, loss dikontrol oleh stop loss default
- karena `Best Trade +8%`, profit maksimal sesuai TP3 default

Kesimpulan awal dari contoh tersebut: strategi terlihat layak diteliti lanjut, tetapi tetap perlu diuji di periode berbeda, ticker berbeda, serta memperhitungkan fee, slippage, dan likuiditas.

Hal yang perlu diperhatikan:

- jumlah trade kecil bisa membuat `win_rate` dan `profit_factor` terlihat bagus tapi belum stabil
- strategi ini memakai entry di close hari sinyal, sehingga tidak menghitung slippage dan biaya transaksi
- exit memakai data high/low harian, bukan intraday tick-by-tick
- urutan SL lebih dulu dalam candle yang sama membuat hasil lebih konservatif
- performa historis dapat berubah signifikan jika period, universe, atau holding period diganti

## ML Validation dan Auto Learning

Selain backtest rule-based, project ini juga punya validasi untuk ML Day-1 Predictor.

Script utama:

```bash
scripts/validate_ml_accuracy.py
```

Jalankan validasi semua ticker:

```bash
make validate-ml
```

Validasi satu ticker:

```bash
make validate-ml-ticker TICKER=ANTM
```

Output default:

```bash
validate_ml_result.json
```

Metrics utama:

| Metric | Arti |
| --- | --- |
| `Directional Accuracy` | Persentase prediksi arah naik/turun yang benar. Baseline random sekitar 50%. |
| `MAE` | Mean Absolute Error antara prediksi return dan actual return. Lebih kecil lebih baik. |
| `Buy Precision` | Dari semua prediksi BUY, berapa persen yang actual-nya naik. |
| `Buy Recall` | Dari semua hari yang actual-nya naik, berapa persen berhasil ditangkap sebagai BUY. |

### Apakah ML Learning Bisa Otomatis Saat Full Analysis?

Bisa.

Auto training ML dijalankan saat `run_full_analysis()` dipanggil. Ini berarti otomatis berlaku untuk:

```bash
make analysis-full
make analysis-tickers TICKERS="ANTM"
```

Juga berlaku saat:

- klik tombol `Run Analysis Now` di Streamlit UI
- scheduler harian menjalankan full analysis

Auto learning dikontrol oleh environment variable berikut:

| Variable | Default | Fungsi |
| --- | --- | --- |
| `ML_AUTO_TRAIN` | `true` | Aktif/nonaktifkan auto training saat full analysis |
| `ML_AUTO_TRAIN_PERIOD` | `1y` | Period OHLCV untuk training otomatis |
| `ML_AUTO_TRAIN_MIN_ROWS` | `120` | Minimum row data per ticker agar masuk training |
| `ML_AUTO_TRAIN_MIN_DIR_ACC` | `50.0` | Minimum directional accuracy agar model baru disimpan |
| `ML_AUTO_TRAIN_FORCE_SAVE` | `false` | Simpan model walaupun tidak lolos quality gate |
| `ML_MODEL_META_PATH` | `models/checkpoints/lgbm_day1_meta.json` | Metadata training terakhir |

Contoh mematikan auto learning:

```bash
ML_AUTO_TRAIN=false make analysis-full
```

Contoh menaikkan quality gate:

```bash
ML_AUTO_TRAIN_MIN_DIR_ACC=55 make analysis-full
```

### Mekanisme Auto Learning

Saat full analysis berjalan:

1. workflow cek apakah auto training aktif
2. workflow cek metadata training terakhir di `models/checkpoints/lgbm_day1_meta.json`
3. jika hari ini belum training, script training akan dijalankan
4. model baru hanya disimpan jika lolos quality gate
5. file model aktif disimpan ke:

```bash
models/checkpoints/lgbm_day1.pkl
```

Jika model baru gagal quality gate:

- checkpoint lama tidak ditimpa
- full analysis tetap lanjut
- prediksi ML memakai model lama atau fallback rule-based jika model belum ada

Dokumentasi detail ML learning ada di:

```bash
readme/ML_LEARNING.md
```

## Troubleshooting

### OHLCV tidak cukup

Pesan seperti ini berarti data historis kurang dari kebutuhan indikator:

```text
OHLCV tidak cukup (50 rows)
```

Solusi:

- pakai period lebih panjang, misalnya `--period 2y`
- pastikan ticker valid
- cek koneksi fetcher Stockbit atau fallback `yfinance`

### Tidak ada trade yang ter-generate

Ini berarti tidak ada candle yang memenuhi semua aturan `BUY`.

Solusi:

- coba period lebih panjang
- coba ticker lain
- evaluasi ulang threshold strategi jika memang ingin lebih banyak sinyal

### Fetcher gagal

Script akan mencoba Stockbit terlebih dahulu, lalu fallback ke `yfinance`. Jika keduanya gagal, hasil ticker tersebut akan berisi error dan dilewati dari summary agregat.
