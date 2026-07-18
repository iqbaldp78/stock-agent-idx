# Realtime Stockbit Integration untuk IHSG & Portfolio Analyzer

## Ringkasan Perubahan

Implementasi realtime price fetching dari Stockbit API untuk IHSG page dan portfolio analyzer.

### File yang Dimodifikasi

#### 1. `data/fetcher_stockbit.py`
**Fungsi Baru:**
- `get_ihsg_realtime_price_stockbit()` → Fetch IHSG realtime price dari Stockbit
- `_ihsg_realtime_fallback()` → Fallback jika API tidak tersedia
- `get_current_price_stockbit(ticker)` → Existing function tetap sama

**Return Format:**
```python
{
    "price": float,
    "prev_close": float,
    "change": float,
    "change_pct": float,
    "timestamp": str,
    "currency": str,
    "source": "stockbit" | "fallback"
}
```

---

#### 2. `web-backend/main.py` - Endpoint `/api/ihsg`
**Perubahan:**
- Menambahkan realtime IHSG price fetch dari Stockbit
- Response sekarang include `realtime` field dengan price data

**Response Baru:**
```json
{
    "latest": { ... },
    "history": [ ... ],
    "realtime": {
        "price": 7250.45,
        "prev_close": 7200.00,
        "change": 50.45,
        "change_pct": 0.70,
        "timestamp": "2026-07-18T08:45:00",
        "currency": "IDR",
        "source": "stockbit"
    }
}
```

---

#### 3. `agents/portfolio_advisor.py`
**Fungsi Baru:**
- `_get_realtime_prices(tickers)` → Parallel fetch realtime prices untuk multiple tickers

**Perubahan di `analyze_portfolio()`:**
1. Fetch realtime prices untuk semua holdings & top picks (parallel, 5 workers)
2. Update holdings & top_picks dengan realtime prices sebelum analysis
3. Pass data ke LLM dengan note bahwa harga sudah REALTIME
4. LLM menggunakan harga actualtime untuk menghitung target_price & target_lots

**User Prompt Update:**
```
DETAIL HOLDINGS (HARGA DIUPDATE REALTIME):
...

TOP PICKS TERBARU (Peluang Investasi - HARGA REALTIME):
...

CATATAN PENTING:
- Semua harga di atas adalah harga REALTIME terbaru dari Stockbit (bukan cache/stale data).
- Gunakan harga realtime ini untuk menghitung target allocation, target price, dan target lots yang akurat.
```

---

## Alur Data

### Untuk IHSG Page (`/api/ihsg`)
```
User Request → /api/ihsg
    ↓
Fetch IHSG Realtime dari Stockbit
    ↓
Fetch Latest Prediction dari DB
    ↓
Combine realtime + prediction
    ↓
Return {latest, history, realtime}
```

### Untuk Portfolio Analyzer (`/api/portfolio/ai-analysis`)
```
Request dengan holdings & top_picks
    ↓
Extract semua tickers (holdings + top_picks)
    ↓
Parallel fetch realtime prices (max 5 concurrent)
    ↓
Update holdings & top_picks dengan realtime prices
    ↓
Build portfolio context (dengan harga fresh)
    ↓
LLM Analysis (dengan realtime prices + RAG news)
    ↓
Return recommendations (target_price & target_lots berbasis harga realtime)
```

---

## Error Handling

**IHSG Realtime:**
- Jika Stockbit API fail → fallback dengan error message
- Tetap return valid response structure

**Portfolio Prices:**
- Jika fetch price fail untuk ticker tertentu → skip ticker itu, lanjut ke ticker lain
- Jika semua fail → gunakan cached prices dari holdings/top_picks
- Logged untuk debugging

---

## Performance

### IHSG Realtime
- Single API call → ~500-1000ms
- Cached response (optional future enhancement)

### Portfolio Realtime Prices
- Parallel fetching: 5 workers
- Untuk 15 tickers → ~2-3 seconds total
- ThreadPoolExecutor dengan timeout handling

---

## Testing

### Test 1: IHSG Realtime
```bash
curl -X GET http://localhost:8000/api/ihsg \
  -H "Authorization: Bearer <token>"
```
Cek field `realtime` dalam response

### Test 2: Portfolio Analysis
```bash
curl -X POST http://localhost:8000/api/portfolio/ai-analysis \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 1,
    ...
  }'
```
Cek:
- `dca_priority[*].target_price` = realtime prices
- `dca_priority[*].target_lots` = calculated dari realtime prices
- System prompt mention "HARGA REALTIME terbaru dari Stockbit"

---

## Dependencies

✅ Semua sudah tersedia:
- `data.fetcher_stockbit` → Sudah punya Stockbit API integration
- `concurrent.futures.ThreadPoolExecutor` → Python stdlib
- `httpx` → Sudah di requirements

---

## Future Enhancements

1. **Cache realtime prices** (5-10 min TTL)
2. **Webhook untuk price updates** (real WebSocket)
3. **Batch price fetch** untuk IHSG + major holdings
4. **Price alert thresholds** di portfolio
