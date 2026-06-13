# Portfolio Management & DCA Automation

Dokumen ini menjelaskan fitur Portfolio Management untuk long-term investing, DCA bulanan, dan AI Portfolio Agent di project ini.

## Ringkasnya

Fitur portfolio dibuat untuk membantu mengelola portfolio long investing IDX dengan budget DCA bulanan.

Use case awal:

| Ticker | Lot | Avg Cost |
| --- | ---: | ---: |
| TLKM | 10 | 3,326 |
| ANTM | 20 | 3,683 |
| BRIS | 7 | 2,103 |
| ADMR | 28 | 1,952 |

Budget DCA default:

```text
Rp 2.000.000 / bulan
```

Fitur utama:

- track holdings dan average cost
- hitung P&L real-time dari current price
- record transaksi BUY / SELL
- preview average cost setelah pembelian baru
- buat DCA strategy dari TOP PICKS atau input manual
- rekomendasi timing DCA berdasarkan true cost bandar
- daily DCA trigger check via scheduler
- AI Portfolio Agent untuk rebalancing, DCA priority, risk analysis, dan performance attribution

## File Utama

| File | Fungsi |
| --- | --- |
| `portfolio/manager.py` | CRUD holdings, average cost calculator, P&L tracker, transaction recorder |
| `portfolio/dca_strategy.py` | DCA strategy, trigger check, timing recommendation |
| `agents/portfolio_advisor.py` | AI Portfolio Agent untuk analisis portfolio |
| `ui/app.py` | Halaman Streamlit `💼 Portfolio` dan tombol Set DCA di TOP PICKS |
| `scheduler.py` | Job harian DCA check dan AI portfolio analysis |
| `db/models.py` | Model `PortfolioHolding`, `DcaTransaction`, `DcaStrategy` |
| `db/migrations/versions/add_portfolio_tables.py` | Migration tabel portfolio |

## Database Schema

Fitur ini menambahkan 3 tabel.

### `portfolio_holdings`

Menyimpan posisi portfolio aktif.

Kolom penting:

| Kolom | Arti |
| --- | --- |
| `ticker` | Kode saham |
| `avg_cost` | Average cost per lembar |
| `total_shares` | Jumlah lembar saham, bukan lot |
| `total_invested` | Total modal = avg cost × shares |
| `current_price` | Harga terakhir |
| `current_value` | Nilai market saat ini |
| `unrealized_pnl` | P&L belum terealisasi dalam rupiah |
| `unrealized_pnl_pct` | P&L belum terealisasi dalam persen |
| `status` | `ACTIVE` atau `CLOSED` |

Catatan: 1 lot = 100 lembar.

### `dca_transactions`

Menyimpan semua transaksi BUY / SELL.

Kolom penting:

| Kolom | Arti |
| --- | --- |
| `holding_id` | Link ke holding |
| `ticker` | Kode saham |
| `transaction_type` | `BUY` atau `SELL` |
| `shares` | Jumlah lembar |
| `price` | Harga transaksi per lembar |
| `amount` | Total transaksi |
| `broker_fee` | Fee broker, default 0 |
| `transaction_date` | Tanggal transaksi |
| `signal_id` | Optional link ke sinyal TOP PICKS |
| `notes` | Catatan transaksi |

### `dca_strategy`

Menyimpan strategi DCA aktif.

Kolom penting:

| Kolom | Arti |
| --- | --- |
| `ticker` | Kode saham |
| `total_budget` | Budget total untuk strategy |
| `remaining_budget` | Budget tersisa |
| `dca_count` | Jumlah level DCA |
| `entry_low` | Level entry paling ideal |
| `entry_high` | Level entry tengah |
| `max_entry` | Harga maksimum yang masih boleh dibeli |
| `next_buy_price` | Trigger harga berikutnya |
| `signal_id` | Link ke TOP PICKS signal jika strategy dibuat dari signal |
| `tp1`, `tp2`, `tp3` | Take profit dari signal |
| `stop_loss` | Stop loss dari signal |
| `status` | `ACTIVE`, `CANCELLED`, atau `COMPLETED` |

## Setup Database

Jalankan migration:

```bash
make db-migrate
```

Atau langsung:

```bash
docker compose exec app alembic upgrade head
```

Verifikasi tabel:

```bash
docker compose exec postgres psql -U stockuser -d stockagent -c "\d portfolio_holdings"
docker compose exec postgres psql -U stockuser -d stockagent -c "\d dca_transactions"
docker compose exec postgres psql -U stockuser -d stockagent -c "\d dca_strategy"
```

## Input Holdings Awal

Contoh memasukkan portfolio existing:

```bash
docker compose exec app python -c "
from portfolio.manager import add_holding
add_holding('TLKM', 1000, 3326)
add_holding('ANTM', 2000, 3683)
add_holding('BRIS', 700, 2103)
add_holding('ADMR', 2800, 1952)
print('Holdings added')
"
```

Karena fungsi memakai `total_shares`, jumlah lot harus dikali 100:

| Lot | Shares |
| ---: | ---: |
| 10 lot | 1,000 shares |
| 20 lot | 2,000 shares |
| 7 lot | 700 shares |
| 28 lot | 2,800 shares |

Cek isi holdings:

```bash
docker compose exec postgres psql -U stockuser -d stockagent -c "SELECT ticker, total_shares, avg_cost, total_invested, status FROM portfolio_holdings ORDER BY ticker;"
```

## Halaman UI Portfolio

Buka Streamlit:

```text
http://localhost:8501
```

Pilih menu:

```text
💼 Portfolio
```

Halaman ini memiliki 5 tab.

### 1. Holdings Overview

Tab ini menampilkan:

- Total Invested
- Current Value
- Total P&L
- Best Performer
- holdings table
- form Add New Holding
- form Record BUY / SELL
- preview avg cost baru sebelum BUY

Contoh preview average cost:

```text
Current: TLKM 10 lot @ 3,326
New buy: 5 lot @ 3,300
New avg cost: 3,317
Total after buy: 15 lot
```

Formula:

```text
new_avg = (current_avg × current_shares + new_price × new_shares) / (current_shares + new_shares)
```

### 2. DCA Manager

Tab ini digunakan untuk membuat dan memantau DCA strategy.

Ada 3 bagian:

1. Active DCA Strategies
2. Create New DCA Strategy
3. DCA Timing Recommendation

#### Create DCA dari TOP PICKS

Flow:

1. Jalankan full analysis:

   ```bash
   make analysis-full
   ```

2. Buka halaman `📈 Top Picks`
3. Klik tombol:

   ```text
   💰 Set DCA for <TICKER>
   ```

4. Buka `💼 Portfolio → DCA Manager`
5. Pilih signal dari TOP PICKS
6. Isi budget, misalnya `2000000`
7. Pilih jumlah DCA levels, misalnya `3`
8. Preview levels
9. Activate DCA Strategy

#### Create DCA Manual

Jika belum ada TOP PICKS signal, strategy bisa dibuat manual dengan input:

- ticker
- entry low
- entry high
- max entry
- total budget
- jumlah levels

#### DCA Level Logic

Untuk 3 level:

| Level | Harga |
| --- | --- |
| Level 1 | `entry_low` |
| Level 2 | `entry_high` |
| Level 3 | `max_entry` |

Untuk lebih dari 3 level, harga dibuat dengan interpolasi merata antara `entry_low` dan `max_entry`.

Budget dibagi sama rata per level.

Shares selalu dibulatkan ke bawah ke kelipatan 100 lembar agar sesuai lot.

Contoh:

```text
Budget: Rp 2.000.000
DCA Count: 3
Amount per level: Rp 666.666

Level 1 @ 3,000 → 2 lot = Rp 600.000
Level 2 @ 3,200 → 2 lot = Rp 640.000
Level 3 @ 3,400 → 1 lot = Rp 340.000
```

Sisa budget tidak dipaksa habis karena pembelian harus dalam kelipatan lot.

### 3. Transaction History

Tab ini menampilkan history transaksi.

Filter:

- ticker
- transaction type: BUY / SELL

Kolom:

- date
- ticker
- type
- lot
- price
- amount
- signal id
- notes

Ada export CSV untuk kebutuhan tracking offline.

### 4. Performance Report

Tab ini menampilkan:

- monthly transaction flow
- per-ticker transaction summary
- current holdings P&L

Catatan: versi awal ini masih menghitung performance sederhana dari transaction flow dan unrealized P&L. Realized P&L detail bisa ditambahkan nanti.

### 5. AI Analysis

Tab ini untuk AI Portfolio Agent.

Fitur yang dirancang:

- rebalancing recommendations
- DCA priority ranking
- risk analysis
- performance attribution

Agent utama:

```text
agents/portfolio_advisor.py
```

## AI Portfolio Agent

AI Portfolio Agent adalah agent all-in-one untuk long investing portfolio.

### Input Data

Agent memakai data:

- current holdings + P&L
- active DCA strategies
- latest TOP PICKS signals
- bandarmologi true cost dari signals
- transaction history
- monthly DCA budget

### Output

Agent mengembalikan JSON terstruktur:

```json
{
  "summary": "Executive summary",
  "rebalancing": {
    "needed": true,
    "overweight": ["ANTM"],
    "underweight": ["TLKM"],
    "actions": [
      {
        "ticker": "TLKM",
        "action": "INCREASE",
        "reason": "Weight masih rendah dan timing acceptable"
      }
    ]
  },
  "dca_priority": [
    {
      "rank": 1,
      "ticker": "ANTM",
      "allocation": 800000,
      "timing_status": "IDEAL",
      "conviction": "HIGH",
      "reasoning": "Harga dekat true cost bandar dan signal kuat"
    }
  ],
  "risk_analysis": {
    "sector_concentration": {
      "mining": 50,
      "telco": 20,
      "banking": 30
    },
    "risk_level": "MEDIUM",
    "diversification_score": 7.0,
    "recommendations": [
      "Kurangi konsentrasi mining jika weight terlalu besar"
    ]
  },
  "performance_attribution": {
    "best_performer": {
      "ticker": "ANTM",
      "return_pct": 12.5,
      "reason": "Momentum dan accumulation kuat"
    },
    "worst_performer": {
      "ticker": "BRIS",
      "return_pct": -3.2,
      "reason": "Underperform dibanding holdings lain"
    },
    "signal_quality": "Belum cukup transaksi closed untuk evaluasi"
  }
}
```

### Test Agent Manual

Contoh menjalankan agent dari container:

```bash
docker compose exec app python -c "
from agents.portfolio_advisor import analyze_portfolio
from portfolio.manager import get_all_holdings, get_transactions
from portfolio.dca_strategy import get_active_strategies

result = analyze_portfolio(
    holdings=get_all_holdings(),
    active_strategies=get_active_strategies(),
    top_picks=[],
    monthly_budget=2000000,
    transactions=get_transactions(),
)
print(result['summary'])
"
```

Jika LLM provider/API key belum tersedia, agent akan mengembalikan error response dengan schema yang tetap konsisten.

## DCA Timing Recommendation

Fungsi:

```python
from portfolio.dca_strategy import recommend_dca_timing
```

Contoh:

```bash
docker compose exec app python -c "
from portfolio.dca_strategy import recommend_dca_timing
import json
print(json.dumps(recommend_dca_timing('TLKM'), indent=2))
"
```

Output contoh:

```json
{
  "ticker": "TLKM",
  "status": "ACCEPTABLE",
  "current_price": 2880,
  "true_cost_1m": 2840,
  "distance_pct": 1.41,
  "recommended_buy": 2840,
  "reason": "Harga 1.4% di atas true cost bandar 1M. Masih acceptable untuk DCA."
}
```

Status timing:

| Status | Kondisi | Interpretasi |
| --- | --- | --- |
| `IDEAL` | current price <= true cost bandar | Timing terbaik, harga di bawah cost bandar |
| `ACCEPTABLE` | 0-2% di atas true cost | Masih layak untuk DCA |
| `CAUTION` | 2-5% di atas true cost | Tunggu koreksi jika tidak urgent |
| `AVOID` | >5% di atas true cost | Hindari entry sekarang |
| `NO_DATA` | data harga / true cost tidak tersedia | Perlu run analysis atau data belum ada |

Agar true cost tersedia, jalankan full analysis terlebih dahulu:

```bash
make analysis-full
```

## Scheduler

Scheduler menjalankan beberapa job terkait portfolio.

### DCA Trigger Check

Job:

```text
run_dca_check() @ 16:45 WIB, Senin-Jumat
```

Fungsi:

- ambil semua active DCA strategies
- ambil current price
- cek apakah current price <= next_buy_price
- log trigger jika ada
- tidak auto-buy

Log contoh:

```text
=== DCA TRIGGER CHECK START ===
Found 1 DCA triggers:
  🎯 TLKM: Current 2,850 <= Target 2,880 | Budget remaining: Rp 1,200,000
=== DCA TRIGGER CHECK END ===
```

### AI Portfolio Analysis

Job:

```text
run_portfolio_analysis() @ 17:00 WIB, Senin-Jumat
```

Fungsi:

- ambil holdings
- ambil active DCA strategy
- ambil latest TOP PICKS dari database
- ambil transaksi 30 hari terakhir
- panggil AI Portfolio Agent
- log summary, DCA priority, risk level

Log contoh:

```text
=== PORTFOLIO AI ANALYSIS START ===
Analysis: Portfolio masih overweight mining, DCA bulan ini diprioritaskan ke TLKM dan BRIS.
  💰 DCA Priority this month:
    #1 TLKM: Rp 800,000 | ACCEPTABLE | HIGH
    #2 BRIS: Rp 700,000 | IDEAL | MEDIUM
  ⚠️ Risk: MEDIUM | Diversification: 7/10
=== PORTFOLIO AI ANALYSIS END ===
```

Monitor logs:

```bash
docker compose logs -f app | grep "DCA\|Portfolio AI"
```

## Common Commands

### Add Holding

```bash
docker compose exec app python -c "from portfolio.manager import add_holding; add_holding('TLKM', 1000, 3326)"
```

### Record Buy

```bash
docker compose exec app python -c "from portfolio.manager import record_buy; record_buy('TLKM', lots=5, price=3300)"
```

### Record Sell

```bash
docker compose exec app python -c "from portfolio.manager import record_sell; record_sell('TLKM', lots=2, price=3400)"
```

### Preview Average Cost After Buy

```bash
docker compose exec app python -c "
from portfolio.manager import preview_avg_cost_after_buy
print(preview_avg_cost_after_buy('TLKM', new_price=3300, new_lots=5))
"
```

### List Holdings

```bash
docker compose exec app python -c "from portfolio.manager import get_all_holdings; print(get_all_holdings())"
```

### Check DCA Timing

```bash
docker compose exec app python -c "from portfolio.dca_strategy import recommend_dca_timing; print(recommend_dca_timing('ANTM'))"
```

### List Active DCA Strategies

```bash
docker compose exec app python -c "from portfolio.dca_strategy import get_active_strategies; print(get_active_strategies())"
```

## Cara Pakai End-to-End

### 1. Start Services

```bash
make up
```

### 2. Run Migration

```bash
make db-migrate
```

### 3. Add Existing Holdings

```bash
docker compose exec app python -c "
from portfolio.manager import add_holding
add_holding('TLKM', 1000, 3326)
add_holding('ANTM', 2000, 3683)
add_holding('BRIS', 700, 2103)
add_holding('ADMR', 2800, 1952)
"
```

### 4. Run Full Analysis

```bash
make analysis-full
```

Ini akan mengisi TOP PICKS dan data bandarmologi / true cost yang dibutuhkan untuk timing recommendation.

### 5. Open UI

```text
http://localhost:8501
```

### 6. Check Portfolio

Buka:

```text
💼 Portfolio → Holdings Overview
```

Pastikan holdings muncul dan P&L ter-update.

### 7. Create DCA Strategy

Buka:

```text
💼 Portfolio → DCA Manager
```

Pilih:

```text
From TOP PICKS Signal
```

Set:

```text
Budget: 2000000
DCA Levels: 3
```

Klik preview lalu activate.

### 8. Check Timing

Di tab DCA Manager, pilih ticker dan klik:

```text
Check Timing
```

Gunakan status `IDEAL` / `ACCEPTABLE` sebagai kandidat entry terbaik.

## Troubleshooting

### `NO_DATA` saat Check Timing

Artinya data true cost bandar belum tersedia untuk ticker tersebut.

Solusi:

```bash
make analysis-full
```

Pastikan ticker masuk universe / TOP PICKS / pernah dianalisis.

### Table portfolio belum ada

Error seperti:

```text
relation "portfolio_holdings" does not exist
```

Solusi:

```bash
make db-migrate
```

Atau:

```bash
docker compose exec app alembic upgrade head
```

### Harga current price tidak update

Fungsi harga memakai Stockbit fetcher.

Cek manual:

```bash
docker compose exec app python -c "from data.fetcher_stockbit import get_current_price_stockbit; print(get_current_price_stockbit('TLKM'))"
```

Jika gagal, kemungkinan:

- koneksi API/data provider bermasalah
- ticker tidak valid
- session/token data provider expired

### AI Portfolio Agent error

Jika output AI Analysis berisi error, cek:

- LLM API key / 9Router config
- model config di `config.py`
- network ke LLM provider

Cek logs:

```bash
docker compose logs -f app | grep "Portfolio AI"
```

## Batasan Saat Ini

- DCA trigger hanya notify/log, tidak auto-execute buy
- AI analysis belum menyimpan hasil ke dedicated DB table
- Realized P&L detail untuk SELL masih sederhana
- Sector concentration masih bergantung pada inferensi agent / data signal yang tersedia
- Monthly budget masih hardcoded di scheduler sebagai Rp 2.000.000
- Belum ada Telegram/email notification

## Future Enhancement

Ide pengembangan berikutnya:

- simpan hasil AI Portfolio Analysis ke tabel `portfolio_analysis_reports`
- tampilkan hasil AI Analysis terakhir di UI tanpa harus run ulang
- monthly DCA plan otomatis setiap awal bulan
- Telegram notification untuk DCA trigger
- rebalancing target weight per sektor
- realized P&L detail per transaksi SELL
- DCA backtesting historis
- correlation matrix antar holdings
- Monte Carlo risk projection
