# Stock Agent IDX - Makefile Guide

Panduan ini menjelaskan cara menggunakan `Makefile` untuk menjalankan workflow project dengan cepat.

## Prasyarat

- Docker dan Docker Compose sudah terpasang.
- File `.env` sudah terisi (lihat `.env.example` jika ada field yang belum diisi).
- Jalankan command dari root project ini.

## Mulai Cepat

```bash
make            # sama dengan make help
make up         # start semua service
make logs       # lihat log
```

Untuk menghentikan service:

```bash
make down
```

## Daftar Command Utama

Lihat semua command yang tersedia:

```bash
make help
```

### 1) Docker Commands

- `make up` - Start semua service (postgres, app, streamlit)
- `make down` - Stop semua service
- `make restart` - Restart semua service
- `make rebuild` - Rebuild image tanpa cache lalu start lagi
- `make logs` - Tampilkan log semua service
- `make logs-app` - Log service app
- `make logs-streamlit` - Log service streamlit
- `make shell` - Masuk shell container app
- `make db-shell` - Masuk PostgreSQL shell

### 2) Agent Commands (Single Agent)

Semua command yang butuh ticker wajib pakai variable `TICKER`.

Contoh:

```bash
make agent-technical TICKER=BBCA
```

Daftar command:

- `make agent-bandarmologi TICKER=BBCA`
- `make agent-technical TICKER=BBCA`
- `make agent-fundamental TICKER=BBCA`
- `make agent-news TICKER=BBCA`
- `make agent-price-predictor TICKER=BBCA`
- `make agent-macro` (tanpa ticker)
- `make all-agents TICKER=BBCA` (jalankan beberapa agent sekaligus)

Shortcut cepat:

- `make bbca`
- `make antm`
- `make bmri`

### 3) Debate dan Full Analysis

Untuk beberapa ticker, gunakan variable `TICKERS` dipisah spasi.

Contoh:

```bash
make debate-tickers TICKERS="BBCA BMRI TLKM"
make analysis-tickers TICKERS="BBCA BMRI"
```

Daftar command:

- `make debate-only`
- `make debate-tickers TICKERS="BBCA BMRI TLKM"`
- `make analysis-full`
- `make analysis-tickers TICKERS="BBCA BMRI"`

Catatan: `analysis-full` dan `analysis-tickers` akan mencoba auto-train model ML Day-1 sekali per hari sebelum analisis berjalan. Set `ML_AUTO_TRAIN=false` jika ingin skip training.

### 4) Smoke Test dan Debug

- `make train-ml` - train model ML Day-1 untuk semua universe ticker
- `make train-ml-ticker TICKER=BBCA` - train model ML Day-1 untuk satu ticker
- `make validate-ml` - validasi akurasi model ML Day-1
- `make validate-ml-ticker TICKER=BBCA` - validasi akurasi model ML Day-1 untuk satu ticker
- `make smoke-llm` - cek koneksi LLM (9Router)
- `make smoke-debate` - cek persona debate
- `make print-debate-prompts` - print prompt debate untuk debug

### 5) Database & Backup Otomatis (Google Drive)

- `make db-migrate` - Jalankan migrasi schema database
- `make db-backup` - Backup lokal cepat ke file `backup.sql`
- `make db-reset` - Reset database (hapus semua data)
- `make backup-gdrive` - **Backup lengkap (PostgreSQL + Vector DB + .env + models ML + 9router) ke Google Drive**
- `make restore-gdrive FILE=<filename>` - Restore sistem dari file backup Google Drive

---

## 💾 Backup & Disaster Recovery (Google Drive)

Project ini dilengkapi sistem otomatisasi backup data harian ke Google Drive menggunakan `rclone`. Ukuran arsip sangat ringkas (~25 MB terkompresi) dan aman jika ingin pindah server/cloud provider kapan saja.

### Komponen yang Dibackup
1. Database PostgreSQL utama (`stockagent`)
2. Database Vector (`vectoragent`)
3. File konfigurasi (`.env`)
4. Model Machine Learning (`models/`)
5. **9router AI Gateway** (`~/.9router/` berisi SQLite database, API keys model, routes, JWT secrets, dan user auth)

### Jadwal Otomatis (Cron)
- Berjalan otomatis setiap hari pukul **02:00 WIB**.
- **Retention Policy**: Otomatis menghapus backup di Google Drive yang lebih lama dari **7 hari** agar storage tidak menumpuk.
- File log harian tersimpan di: `/var/log/backup_gdrive.log`.

### Command Manual

```bash
# 1. Menjalankan backup manual ke Google Drive
make backup-gdrive
# atau: ./scripts/backup_to_gdrive.sh

# 2. Melihat daftar file backup di Google Drive
rclone ls hamboo-sumupod-backup:VPS_StockAgent_Backups

# 3. Restore ke server baru / recovery
make restore-gdrive FILE=stockagent_backup_YYYYMMDD_HHMMSS.tar.gz
# atau: ./scripts/restore_from_backup.sh stockagent_backup_YYYYMMDD_HHMMSS.tar.gz
```

---

### 6) Development Helpers

- `make clean` - hapus cache Python (`__pycache__`, `*.pyc`, `*.pyo`)
- `make lint` - placeholder (belum dikonfigurasi)
- `make format` - placeholder (belum dikonfigurasi)

## Workflow Harian (Rekomendasi)

```bash
make up
make smoke-llm
make analysis-tickers TICKERS="BBCA BMRI"
make logs-app
```

Saat selesai kerja:

```bash
make down
```
