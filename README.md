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

### 4) Smoke Test dan Debug

- `make smoke-llm` - cek koneksi LLM (9Router)
- `make smoke-debate` - cek persona debate
- `make print-debate-prompts` - print prompt debate untuk debug

### 5) Database

- `make db-migrate` - jalankan migration
- `make db-backup` - backup ke file `backup.sql`
- `make db-reset` - reset database (hapus semua data)

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

## Troubleshooting

### Service tidak jalan

1. Jalankan `make logs` untuk cek error.
2. Jika image bermasalah, coba `make rebuild`.
3. Pastikan port dan environment variable tidak bentrok.

### Error "TICKER is required"

Pastikan command menyertakan variable `TICKER`, contoh:

```bash
make agent-news TICKER=BBCA
```

### Error "TICKERS is required"

Pastikan command menyertakan variable `TICKERS` dengan format string berisi ticker dipisah spasi, contoh:

```bash
make analysis-tickers TICKERS="BBCA BMRI"
```
