# 🛠️ Panduan Lengkap Makefile (Stock Agent IDX)

File `Makefile` pada proyek ini berisi berbagai macam pintasan perintah (kumpulan *command*) yang dibuat untuk mempermudah Anda dalam menjalankan servis Docker, memanggil Agen AI secara individual, menguji *machine learning*, hingga mereset database.

Tidak perlu mengetik perintah Docker atau Python yang panjang-panjang! Anda cukup mengetikkan `make <nama-perintah>` di terminal Anda.

Berikut adalah rincian fungsionalitas dari setiap perintah yang tersedia:

---

## 🐳 1. Docker Commands (Manajemen Wadah/Container)
Perintah untuk mengatur nyala/matinya server lokal aplikasi Anda.

- **`make up`** : Menjalankan seluruh sistem (PostgreSQL, App, dan Streamlit) di belakang layar (*detached*).
- **`make down`** : Mematikan seluruh sistem.
- **`make restart`** : Mematikan lalu langsung menyalakan kembali seluruh sistem (berguna jika baru saja mengubah konfigurasi).
- **`make logs`** : Melihat *log* (catatan terminal) dari semua wadah Docker secara bersamaan dan terus-menerus.
- **`make logs-app`** : Melihat *log* khusus mesin Python (`app`) saja. (Sangat berguna untuk melihat proses AI bekerja).
- **`make logs-streamlit`** : Melihat *log* khusus mesin antarmuka (Streamlit) saja.
- **`make rebuild`** : Membangun ulang (*build*) Docker *image* dari nol tanpa menggunakan *cache* lalu menyalakannya (wajib dijalankan jika Anda baru menambahkan *library* ke `requirements.txt`).
- **`make shell`** : Masuk ke dalam terminal/sistem operasi wadah `app`.
- **`make db-shell`** : Langsung masuk ke baris perintah (*console*) basis data PostgreSQL (psql).

---

## 🤖 2. Individual Agents (Menjalankan Agen Satu per Satu)
Digunakan jika Anda ingin mengetes analisis spesifik tanpa harus menjalankan *workflow* lengkap.
*(Ganti `BBCA` pada panduan di bawah dengan saham yang Anda tuju).*

- **`make agent-bandarmologi TICKER=BBCA`** : Menyuruh Agen Bandarmologi menghitung *True Cost* dan akumulasi bandar BBCA.
- **`make agent-technical TICKER=BBCA`** : Menyuruh Agen Teknikal menghitung *Support/Resistance* BBCA.
- **`make agent-fundamental TICKER=BBCA`** : Menyuruh Agen Fundamental menghitung kesehatan keuangan BBCA.
- **`make agent-macro`** : Menyuruh Agen Makro menganalisis kondisi IHSG dan global secara keseluruhan.
- **`make agent-news TICKER=BBCA`** : Menyuruh Agen Berita merangkum sentimen berita terkini BBCA.
- **`make agent-price-predictor TICKER=BBCA`** : Menyuruh AI memprediksi harga BBCA esok hari menggunakan Model ML.
- **`make all-agents TICKER=BBCA`** : Menjalankan keempat agen utama (Bandar, Teknikal, Fundamental, Berita) satu per satu secara berurutan untuk saham BBCA.

---

## 🧠 3. Debate & Analysis (Simulasi Rapat Analis)
Ini adalah inti dari *Stock Agent*. Menjalankan serangkaian agen yang berujung pada debat penetapan *Top Picks*.

- **`make analysis-full`** : Menjalankan siklus analisa lengkap untuk *seluruh* saham dari awal: filter pasar -> memberikan skor -> Debat antar Agen AI -> Rekomendasi Portofolio.
- **`make analysis-tickers TICKERS="BBCA BMRI"`** : Menjalankan analisa lengkap, namun dikunci hanya untuk saham yang Anda sebutkan saja.
- **`make debate-only`** : Melewati tahap penyaringan (filter), langsung menyuruh agen berdebat terhadap saham-saham yang skornya sudah ada di database.
- **`make debate-tickers TICKERS="BBCA BMRI"`** : Langsung menyuruh agen berdebat hanya tentang saham spesifik tersebut.

---

## 🧪 4. Backtest & Machine Learning (Validation)
Untuk mengevaluasi kehebatan AI ke masa lalu (*historical testing*).

- **`make backtest`** : Menyimulasikan *trading* otonom berdasarkan rekomendasi sinyal AI selama **1 tahun terakhir**.
- **`make backtest-max`** : Menyimulasikan *trading* historis dengan menarik data sejauh mungkin tanpa batas waktu.
- **`make backtest-ticker TICKER=BBCA PERIOD=5y`** : Menyimulasikan *trading* AI khusus pada saham tertentu dengan rentang waktu yang bisa disesuaikan (contoh: 5 tahun).
- **`make train-ml`** : Melatih ulang kecerdasan model prediktif (LightGBM) AI untuk *seluruh* saham agar makin pintar.
- **`make train-ml-ticker TICKER=BBCA`** : Melatih model prediktif hanya untuk satu saham spesifik.
- **`make validate-ml`** : Memberikan "ujian ketepatan" kepada model prediktif untuk seluruh saham, hasilnya muncul di Dashboard Performance.
- **`make validate-ml-ticker TICKER=BBCA`** : Menguji ketepatan model prediktif khusus satu saham.

---

## 💾 5. Data & Database (Manajemen Pangkalan Data)
Penting untuk kebersihan dan keamanan riwayat data AI Anda.

- **`make db-migrate`** : Memperbarui struktur tabel *database* dengan aman jika ada pembaruan versi (lewat `alembic`).
- **`make db-backup`** : Mengamankan dan mengunduh seluruh *database* (termasuk portofolio) ke dalam satu file mentah `backup.sql`.
- **`make reset-dev-data`** : **(PENTING)** Menghapus tabel data yang kotor/sampah historis simulasi AI (Sinyal, Skor, Log Debat, Transaksi), namun **TIDAK** menghapus isi Portofolio Anda maupun *Cache* sejarah harga saham.
- **`make db-reset`** : **(BAHAYA)** Menghapus total, meratakan, dan menghancurkan seluruh isi pangkalan data Anda tanpa sisa, lalu membangunnya ulang dari nol.

---

## 🩺 6. Testing & Smoke Tests (Pengujian Koneksi)
Digunakan jika sistem terasa bermasalah dan Anda ingin memeriksa apakah komponen sistem dapat menyala normal.

- **`make smoke-llm`** : Memastikan server AI Generatif (seperti Gemini/OpenAI lewat 9Router) dapat membalas sapaan sistem (Koneksi LLM sehat).
- **`make smoke-debate`** : Menguji coba karakter (Persona) debat setiap agen apakah mereka bisa membalas dengan nada yang tepat.
- **`make print-debate-prompts`** : Mencetak teks perintah (Prompt) rahasia yang biasa dikirim ke AI Generatif, berguna untuk evaluasi prompt.
- **`make validate-schema`** : Melakukan pengetesan input data ke PostgreSQL untuk memastikan tidak ada tabel yang error.

---

## ⚡ 7. Quick Shortcuts (Jalan Pintas Cepat)
Pintasan satu klik untuk riset mendalam.

- **`make bbca`** : Langsung menjalankan semua agen untuk saham BBCA.
- **`make bmri`** : Langsung menjalankan semua agen untuk saham BMRI.
- **`make antm`** : Langsung menjalankan semua agen untuk saham ANTM.

---

## 🧹 8. Development (Bagi Pengembang)
- **`make clean`** : Menyapu bersih *file-file temporary* bawaan Python (`__pycache__`, `*.pyc`) yang tidak berguna dan membuat sempit ruang.
- **`make lint`** & **`make format`** : Merapikan penulisan kode sesuai standar PEP-8 (perlu pengaturan `ruff`/`black` di masa depan).
