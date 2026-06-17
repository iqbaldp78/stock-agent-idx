# 🤖 AI Stock Engine Prediction (IDX)

Sistem **Artificial Intelligence & Quantitative Stock Engine** tingkat lanjut yang dirancang khusus untuk memprediksi pergerakan saham, memberikan sinyal *trading*, dan menganalisis portofolio di Bursa Efek Indonesia (IHSG / IDX).

Sistem ini menggabungkan kekuatan **Machine Learning (LightGBM)**, **Analisis Bandarmologi (True Cost)**, dan **Multi-Agent Large Language Models (LLM via LangGraph)** untuk berdebat dan mengambil keputusan investasi yang matang layaknya *Fund Manager* profesional.

---

## ✨ Fitur Utama

### 1. 🧠 Multi-Agent Debate System (LangGraph)
- **Technical Analyst:** Menganalisis tren harga, MA20/MA50, RSI, dan level *support/resistance*.
- **Fundamental Analyst:** Menganalisis valuasi perusahaan, pertumbuhan pendapatan, EPS, dan dividen.
- **Bandarmologi Analyst:** Melacak akumulasi/distribusi broker secara *real-time* dan menghitung "True Cost" (harga modal rata-rata bandar) pada *window* 7 hari dan 30 hari.
- **Investment Manager:** Bertindak sebagai juri utama yang menyintesis semua pandangan agen di atas, ditambah dengan hasil prediksi *Machine Learning*, untuk mengeluarkan sinyal akhir (STRONG BUY, BUY, HOLD, AVOID).

### 2. 🤖 Machine Learning Predictor
- Menggunakan **LightGBM** dengan validasi *Walk-Forward* (`TimeSeriesSplit`).
- Melakukan prediksi *Day-1 Return* berdasarkan indikator teknikal murni, menghindari kebocoran data (*data leakage*).
- Prediksi ML digunakan sebagai lapisan ekstra keyakinan (*confidence layer*) bagi Investment Manager.

### 3. 💼 AI Portfolio Advisor
- Sistem "All-in-One" analisis portofolio di dalam antarmuka UI.
- **Rebalancing:** Mendeteksi *overweight* atau *underweight* suatu saham di portofolio Anda.
- **DCA Priority:** Memberikan saran *Dollar Cost Averaging* prioritas beserta alokasi *budget* bulanan.
- **Risk Analysis & Attribution:** Mengukur tingkat konsentrasi sektoral dan atribut performa.

### 4. 📊 Premium Streamlit Dashboard
- Antarmuka *Dark Mode* dengan efek kaca (*glassmorphism*) yang premium.
- Tab **Top Picks** untuk melihat rekomendasi saham terbaik hari ini.
- Tab **Performance** yang mencatat tingkat akurasi historis *trading* otomatis dari hasil *backtest*.
- Tab **Backtest** untuk mengevaluasi strategi secara kuantitatif.

---

## 🚀 Instalasi & Persiapan (Setup)

### 1. Kebutuhan Sistem
- **Docker** dan **Docker Compose** (Rekomendasi)
- **Python 3.10+** (jika menjalankan secara lokal tanpa Docker)
- Akun dan kredensial API:
  - Gemini / DeepSeek API Key (untuk Agen LLM)
  - Akun Stockbit (Username & Password/Bearer Token untuk penarikan data)

### 2. Variabel Lingkungan (.env)
Ganti nama `.env.example` menjadi `.env` dan isi kunci API Anda:
```env
# Stockbit
STOCKBIT_API_KEY=eyJhbG... (ambil manual dari Inspect Network Browser)

# Database
POSTGRES_DB=stockagent
POSTGRES_USER=stockuser
POSTGRES_PASSWORD=stockpassword

# LLM Keys
GEMINI_API_KEY=your_gemini_api_key
```
*(Catatan: Pastikan `STOCKBIT_API_KEY` disimpan tanpa tanda kutip `'` atau `"`).*

### 3. Menjalankan via Docker Compose
Sistem ini menggunakan Docker untuk menjalankan *database* PostgreSQL dan aplikasi utama secara terisolasi.
```bash
docker-compose up -d --build
```

---

## 🕹️ Cara Penggunaan (Makefile)

Proyek ini dilengkapi dengan `Makefile` untuk mempermudah eksekusi instruksi:

- **Buka Aplikasi UI (Streamlit):**
  Aplikasi web dapat diakses di `http://localhost:8501`.

- **Menjalankan Pipeline AI Penuh:**
  ```bash
  make run
  ```
  *(Menjalankan ekstraksi data, diskusi antar-agen, prediksi ML, dan pembaruan UI untuk semua ticker di universe).*

- **Analisis Satu Saham (Debat Langsung):**
  ```bash
  make run TICKER=BBCA
  ```

- **Melatih Model Machine Learning:**
  ```bash
  make train-ml
  ```

- **Menguji Performa Historis (Backtest):**
  ```bash
  make backtest PERIOD=max
  ```

- **Mengisi Data Dummy Performance Dashboard:**
  ```bash
  docker compose exec app python scripts/seed_dashboard_from_backtest.py
  ```

---

## 🛠️ Arsitektur Teknologi

- **Backend / Scripting:** Python 3.11
- **LLM Orchestration:** LangChain / LangGraph
- **Machine Learning:** LightGBM, Scikit-Learn
- **Database:** PostgreSQL (SQLAlchemy)
- **Data Providers:** yfinance, Stockbit API (Reverse Engineered Mobile Endpoint)
- **Frontend / Dashboard:** Streamlit (dengan *Custom CSS Injection*)

---
*Dikembangkan secara otomatis dan iteratif bersama AI. "Tingkatkan alpha, minimalkan emosi."*
