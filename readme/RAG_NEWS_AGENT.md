# RAG News Agent Workflow 📰🤖

Dokumen ini menjelaskan arsitektur dan alur kerja (workflow) dari **News Agent** (Sistem RAG Berita) yang diintegrasikan ke dalam ekosistem analisa saham `stock-agent-idx`.

Sistem ini didesain khusus agar **LLM Debate** (Agen Fundamental, Technical, Bandarmologi) dan **Investment Manager** memiliki akses ke konteks berita *real-time* sebelum memberikan rekomendasi trading akhir.

---

## 1. Arsitektur Komponen

Sistem RAG ini menggunakan 3 komponen utama:
1. **News Ingester (`scripts/news_ingester.py`)**: Bertugas menarik *feed* berita dari API Stockbit, membuat kesimpulan (Summary, Sentiment, Tickers), lalu mengubah teks menjadi representasi angka 3072-dimensi (*vector embeddings*) menggunakan model `gemini-embedding-2-preview` dari 9Router.
2. **Vector DB (PostgreSQL + `pgvector`)**: Database khusus yang menggunakan tipe data `halfvec(3072)` untuk menyimpan vektor berita agar pencarian semantic (*cosine similarity*) berjalan sangat cepat.
3. **RAG Retriever (`scripts/rag_retriever.py`)**: Modul yang dipanggil oleh agen debat untuk melakukan *query* atau penarikan berita spesifik dari Vector DB berdasarkan nama saham (Ticker).

---

## 2. Alur Kerja (Workflow) Harian

Workflow sistem berjalan secara otomatis melalui `scheduler.py` dan `run_single_ticker.py` dengan urutan sebagai berikut:

### A. Pengumpulan Berita Berkelanjutan (24/7)
`scheduler.py` diatur untuk mengeksekusi `run_news_ingester` **setiap 30 menit**.
*   **Checkpoint Logic**: Ingester akan mengecek PostgreSQL untuk ID berita (`stream_id`) yang masuk. Jika berita sudah ada di DB, berita tersebut akan **di-skip**. LLM hanya dipanggil untuk memproses berita yang **benar-benar baru** guna menghemat *resource*.
*   Data disimpan dalam format JSONB untuk tag ticker dan array float untuk *embedding*.

### B. Injeksi Berita ke Agen Analis (Debate Round 1)
Ketika proses analisa saham (misal: `MYOR`) dijalankan:
*   Fungsi di `agents/debate/round1.py` akan memanggil `search_by_ticker("MYOR", limit=2)` dari Vector DB.
*   Dua berita teratas dirangkum menjadi **[RAG NEWS CONTEXT]**.
*   Konteks ini disisipkan ke dalam *prompt* sistem (`agents/debate/personas.py`) sebelum dikirim ke LLM Agen Fundamental dan Technical.
*   *Hasil*: Analis merespons dengan mempertimbangkan katalis berita terbaru.

### C. Hak Veto oleh Investment Manager
Setelah debat selesai, kandidat "Top 3 Pick" disaring oleh Investment Manager.
*   Modul `agents/investment_manager.py` kembali menarik berita untuk semua kandidat finalis.
*   Berita-berita ini diberikan kepada LLM Investment Manager sebagai instruksi tambahan: *"Gunakan berita ini sebagai Hak Veto untuk mengeliminasi saham yang rawan, atau mem-boost saham yang punya katalis bagus."*
*   *Hasil*: Ranking akhir bisa berubah secara dinamis merespons sentimen buruk/baik dadakan.

---

## 3. Konfigurasi Penting

*   **Network LLM**: Karena Ingester dan Retriever berjalan dari *dalam* container Docker, seluruh rute panggilan API ke 9Router diarahkan ke network internal (`http://host.docker.internal:20128/v1`), yang sudah di-izinkan melalui `iptables` di host VM.
*   **Vector Size**: Model Gemini terbaru (`gemini-embedding-2-preview`) mengembalikan **3072 dimensi**. Tabel `news_signals` di DB wajib menggunakan tipe data `halfvec(3072)` agar bisa di-indeks menggunakan HNSW.

