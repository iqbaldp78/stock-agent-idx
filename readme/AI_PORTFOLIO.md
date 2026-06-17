# 🤖 AI Portfolio Analysis

Fitur **AI Portfolio Analysis** bekerja layaknya manajer investasi pribadi profesional yang me-*review* seluruh status keuangan saham Anda secara menyeluruh. Proses ini terjadi di balik layar (di dalam file `agents/portfolio_advisor.py`) dengan tahapan berikut:

## 1. Pengumpulan Data (Context Building)
Saat Anda menekan tombol "Get AI Portfolio Analysis", sistem pertama-tama akan mengumpulkan semua data relevan dari database lokal, yaitu:
- **Status Portofolio Saat Ini (Holdings):** Saham apa saja yang dimiliki, rata-rata harga beli (*avg cost*), harga pasar sekarang, dan status P&L (Untung/Rugi).
- **Strategi DCA Aktif:** Data sisa *budget* dari strategi cicil (*Dollar Cost Averaging*) yang sedang berjalan dan di harga berapa target beli selanjutnya.
- **Top Picks Terbaru:** Rekomendasi saham teratas yang dihasilkan oleh Agen Investment Manager, lengkap dengan zona harga beli ideal dan "True Cost" bandar (harga modal rata-rata bandar).
- **Riwayat Transaksi:** Catatan kapan terakhir kali Anda melakukan *buy* atau *sell* dalam 30 hari terakhir.
- **Budget Bulanan:** Angka *budget* alokasi dana baru yang Anda atur melalui antarmuka.

## 2. Evaluasi oleh LLM (Large Language Model)
Semua data di atas dibungkus menjadi sebuah instruksi *(prompt)* terstruktur dan dikirimkan ke model AI tingkat lanjut (dapat dikonfigurasi melalui `.env`, misalnya `gemini-3-pro-preview`). 

AI diberikan "persona" untuk bertindak sebagai **Manajer Portofolio Senior di Bursa Efek Indonesia (IHSG)** yang ahli dalam investasi jangka panjang.

## 3. Hasil Analisis (Format Terstruktur)
AI diinstruksikan untuk tidak membalas dengan teks biasa, melainkan menghasilkan format data JSON yang langsung dirender oleh Streamlit menjadi 4 bagian laporan utama:

### ⚖️ Rebalancing
AI akan mendeteksi apakah portofolio Anda terlalu berat di satu saham (*overweight*) atau kurang bobot (*underweight*). Ia akan merekomendasikan aksi spesifik seperti:
- **REDUCE** (kurangi porsi)
- **INCREASE** (tambah porsi)
- **HOLD** (pertahankan)

### 💰 DCA Priority
Berdasarkan *budget* bulanan Anda, AI akan meranking **Top 3** saham mana yang paling mendesak untuk dibeli *bulan ini*. Ia mempertimbangkan:
- Posisi harga saat ini dibandingkan dengan "True Cost" bandar.
- *Conviction* (tingkat keyakinan fundamental/teknikal).
- Keseimbangan portofolio secara keseluruhan.

### ⚠️ Risk Analysis
Mengukur seberapa rentan portofolio Anda terhadap risiko sektoral (misalnya, jika dana Anda terlalu terkonsentrasi di saham Perbankan). AI juga memberikan skor diversifikasi skala 1 hingga 10 beserta rekomendasi taktis.

### 🏆 Performance Attribution
Menyimpulkan saham mana yang menjadi "tulang punggung" keuntungan Anda (*best performer*) dan mana yang menjadi beban terberat (*worst performer*), untuk dijadikan bahan pembelajaran bagi sinyal agen ke depannya.

---
*Kesimpulan: AI tidak hanya melihat saham satu per satu secara terisolasi, tetapi melihatnya sebagai sebuah "ekosistem portofolio" untuk menjaga dana Anda tetap aman, seimbang, dan teralokasikan pada momentum yang paling tepat.*
