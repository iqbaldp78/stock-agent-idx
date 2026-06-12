
## Membaca Fair Value Fundamental Agent

Fundamental agent sekarang menghasilkan field `fair_value` untuk membantu membaca apakah harga ticker masih murah, wajar, atau mahal secara fundamental.

Jalankan:

```bash
make agent-fundamental TICKER=BBCA
```

Output akan memiliki bagian seperti:

```json
"fair_value": {
  "current_price": 9500,
  "method": "blended",
  "fair_value_low": 8900,
  "fair_value_base": 10400,
  "fair_value_high": 11900,
  "upside_pct": 9.47,
  "margin_of_safety_pct": 8.65,
  "valuation_label": "FAIRLY_VALUED",
  "confidence": "MEDIUM",
  "methods": {
    "pe_based": {...},
    "pbv_roe_based": {...},
    "eps_growth_based": {...}
  }
}
```

### Arti Field Utama

| Field | Arti |
|---|---|
| `current_price` | Harga terakhir yang dipakai sebagai pembanding |
| `fair_value_low` | Batas bawah estimasi fair value |
| `fair_value_base` | Estimasi utama fair value hasil blended method |
| `fair_value_high` | Batas atas estimasi fair value |
| `upside_pct` | Potensi upside/downside dari harga sekarang ke `fair_value_base` |
| `margin_of_safety_pct` | Selisih harga sekarang terhadap fair value, dilihat sebagai safety buffer |
| `valuation_label` | Label valuasi: murah, wajar, mahal |
| `confidence` | Seberapa lengkap metode valuasi yang bisa dihitung |
| `methods` | Detail hasil masing-masing metode valuasi |

### Cara Membaca `valuation_label`

| Label | Interpretasi | Efek ke Fundamental Score |
|---|---|---:|
| `DEEP_UNDERVALUED` | Harga jauh di bawah fair value | `+1.5` |
| `UNDERVALUED` | Harga cukup menarik dibanding fair value | `+1.0` |
| `FAIRLY_VALUED` | Harga relatif wajar | `+0.0` |
| `OVERVALUED` | Harga mulai mahal | `-0.7` |
| `EXPENSIVE` | Harga jauh di atas fair value | `-1.2` |
| `UNKNOWN` | Data tidak cukup untuk valuasi | `+0.0` |

### Metode yang Dipakai

#### 1. `pe_based`

Menggunakan EPS dan target PE.

```text
fair_value = EPS × target_PE
```

EPS sementara diderive dari:

```text
EPS = current_price / PER
```

Metode ini cocok untuk saham yang sudah profitable dan PER valid.

#### 2. `pbv_roe_based`

Menggunakan BVPS dan ROE.

```text
BVPS = current_price / PBV
fair_PBV = ROE / required_return
fair_value = BVPS × fair_PBV
```

Metode ini berguna untuk bank, financial, dan saham asset-heavy.

#### 3. `eps_growth_based`

Menggunakan EPS dan earnings growth untuk membuat target PE berbasis growth.

```text
fair_value = EPS × growth_adjusted_PE
```

Metode ini membantu membaca saham growth, tapi tetap diberi batas agar valuasi tidak terlalu agresif.

### Apakah Fair Value Masuk ke `key_points`?

Ya, tetapi hanya jika sinyalnya kuat.

- Jika `valuation_label` adalah `DEEP_UNDERVALUED` atau `UNDERVALUED`, maka fundamental agent akan menambahkan catatan valuasi ke `key_points`.
- Jika `valuation_label` adalah `OVERVALUED` atau `EXPENSIVE`, maka catatan valuasi akan masuk ke `risks`.
- Jika `FAIRLY_VALUED`, detailnya tetap ada di `fair_value` dan `data_used`, tapi tidak dianggap sebagai key point utama.

Alasannya: `key_points` sebaiknya berisi insight yang actionable, bukan semua angka. Detail angka lengkap tetap bisa dibaca di field `fair_value.methods`.

### Contoh Interpretasi

```json
"fair_value_base": 10400,
"current_price": 9500,
"upside_pct": 9.47,
"valuation_label": "FAIRLY_VALUED"
```

Artinya harga saat ini masih sedikit di bawah fair value, tetapi belum cukup murah untuk disebut `UNDERVALUED` karena upside belum melewati threshold `+10%`.

```json
"fair_value_base": 12500,
"current_price": 9500,
"upside_pct": 31.58,
"valuation_label": "DEEP_UNDERVALUED"
```

Artinya harga jauh di bawah estimasi fair value. Ini akan menjadi `key_points` dan menambah fundamental score.

> Catatan: fair value adalah estimasi berbasis data dan asumsi sederhana, bukan target harga pasti. Gunakan bersama technical, bandarmologi, macro, dan ML forecast.

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
