# 📈 IHSG Predictor Agent

## Overview

IHSG Predictor adalah agent standalone yang memprediksi arah dan target harga IHSG (Indeks Harga Saham Gabungan) dengan confidence level dan component breakdown. Digunakan untuk risk management — jika IHSG bearish, portfolio sizing bisa disesuaikan.

**Key Features**:
- ✅ Directional forecast (BULLISH / BEARISH / SIDEWAYS)
- ✅ Multi-day price targets (D+1, D+3, D+5, D+7)
- ✅ Volatility assessment
- ✅ Component score breakdown (explainable)
- ✅ Independent UI tab (separate dashboard)
- ✅ Rule-based scoring + optional LLM narrative
- ✅ Historical tracking untuk accuracy validation

---

## Architecture

### Data Pipeline

```
IHSG OHLCV (8 tahun)  ─┐
                       ├─→ Momentum Score (0-1)
Market Breadth (LQ45) ─┤
                       ├─→ Breadth Score (0-1)
Macro Data (USD/IDR)  ─┤
                       ├─→ Macro Score (0-1)
Sector Rotation ───────┤
                       └─→ Sector Score (0-1)
                           │
                           ↓
                    Combined Score (0-1)
                           │
                           ↓
                    Daily Move % (-2.5% to +2.5%)
                           │
                           ├─→ D+1, D+3, D+5, D+7 targets
                           ├─→ Direction (BULLISH/BEARISH/SIDEWAYS)
                           ├─→ Confidence (HIGH/MEDIUM/LOW)
                           ├─→ Volatility Level
                           └─→ Component reasoning
```

### Component Scoring (0-1 scale)

#### 1. Momentum Score
- **RSI (14)** — normalized [30:70] → [0:1]
- **MACD** — signal strength (bullish/bearish divergence)
- **MA Positioning** — price vs MA20/50/100 trend strength
- **Result**: Combined momentum indicator

#### 2. Breadth Score
- **A/D Ratio** — advance/decline ratio from LQ45 gainers/losers
  - `> 1.5` → +0.2 (strong)
  - `< 0.7` → -0.2 (weak)
- **Participation** — % of LQ45 above MA20 (`40%` = neutral, `60%` = bullish)
- **Volume Trend** — expanding/contracting (5-day vs 20-day average)
- **Result**: Market breadth confidence

#### 3. Macro Score
- **USD/IDR** — currency pressure (< 15500 = bullish for equities, > 16500 = bearish)
- **IHSG vs MA20** — trend strength vs moving average
- **Volatility** — high volatility penalty (-0.1)
- **Result**: Macro environment sentiment

#### 4. Sector Score
- **Sector Divergence** — max gain - min loss (rotation indicator)
- **Leading Sector Type** — cyclical (mining, infra) vs defensive (consumer)
- **Result**: Sector rotation strength

### Prediction Projection

```python
Combined Score (0-1) → Daily Move %
(0.5 = neutral, 1.0 = strong bullish, 0.0 = strong bearish)

Formula: daily_move% = (combined_score - 0.5) × 2 × 2.5%
Range: -2.5% to +2.5% daily

Multi-day with volatility damping:
- D+1: 100% of daily move
- D+3: 90% of daily move (0.9x damping)
- D+5: 70% of daily move
- D+7: 50% of daily move

Example:
  Combined = 0.65 → Daily = +0.75%
  D+1: IHSG × (1 + 0.75%)
  D+3: IHSG × (1 + 0.75% × 0.9) = IHSG × (1 + 0.675%)
  D+7: IHSG × (1 + 0.75% × 0.5) = IHSG × (1 + 0.375%)
```

---

## Files & Structure

### New Files

#### `data/fetcher_ihsg.py` (~200 lines)
Fetch data untuk IHSG prediction:

```python
get_ihsg_ohlcv(period="8y")
  → DataFrame dengan OHLCV, 8-year history untuk stable indicators

get_market_breadth()
  → dict dengan A/D ratio, participation %, volume trend

get_sector_rotation()
  → dict dengan 5 sector returns + divergence + leading sector
```

#### `agents/ihsg_predictor.py` (~280 lines)
Main prediction engine:

```python
predict_ihsg()
  → dict dengan:
      - current_price, direction, volatility_level, confidence
      - day_1/3/5/7_price dan day_1/3/5/7_pct
      - component_scores (momentum, breadth, macro, sectors)
      - reasoning, key_drivers, risks
      - data_used (audit trail)
```

### Modified Files

#### `db/migrations/init.sql`
Tambah table:
```sql
CREATE TABLE ihsg_predictions (
  id, run_date, current_price, confidence, direction,
  volatility_level, day_1/3/5/7_price, day_1/3/5/7_pct,
  reasoning, key_drivers (JSONB), risks (JSONB),
  component_scores (JSONB), ihsg_trend, macro_signal, created_at
);
```

#### `graph/workflow.py`
Integrate IHSG prediction node:
- Import `from agents.ihsg_predictor import predict_ihsg`
- Add `ihsg_prediction: dict` ke AgentState TypedDict
- Add node: `workflow.add_node("ihsg", run_ihsg_prediction)`
- Add edges: `scoring → ihsg → debate`

#### `db/tracker.py`
Persist predictions:
- Add `save_ihsg_prediction(run_date, ihsg_pred)` function
- Call dari `save_full_result()` jika `result.get("ihsg_prediction")`

#### `ui/app.py`
UI dashboard:
- Add "📈 IHSG Predictor" ke sidebar navigation
- Add elif block untuk render tab:
  - Metrics (current level, confidence, direction, volatility)
  - Predictions (D1/D3/D5/D7 dengan % change)
  - Component breakdown (4 scores)
  - Analysis details (reasoning, drivers, risks)
  - Historical predictions (last 20 runs)

---

## Usage

### Running Full Analysis (dengan IHSG prediction)

```bash
# Full pipeline (filter → scoring → IHSG → debate → decision)
docker-compose exec app python scripts/run_analysis.py

# Atau manual
docker-compose exec app python3 -c "
from graph.workflow import run_full_analysis
result = run_full_analysis()
print(result['ihsg_prediction'])
"
```

### Accessing UI

```
http://localhost:8501
→ Click "📈 IHSG Predictor" tab
```

### Query Database

```sql
-- Latest prediction
SELECT * FROM ihsg_predictions 
WHERE run_date = (SELECT MAX(run_date) FROM ihsg_predictions);

-- Historical (last 20)
SELECT run_date, direction, confidence, day_1_price, day_1_pct
FROM ihsg_predictions 
ORDER BY run_date DESC 
LIMIT 20;
```

---

## Output Example

```json
{
  "current_price": 5840,
  "confidence": "MEDIUM",
  "direction": "BEARISH",
  "volatility_level": "MEDIUM",
  
  "day_1_price": 5789,
  "day_1_pct": -0.86,
  "day_3_price": 5802,
  "day_3_pct": -0.65,
  "day_5_price": 5815,
  "day_5_pct": -0.43,
  "day_7_price": 5852,
  "day_7_pct": 0.21,
  
  "component_scores": {
    "momentum": 0.35,
    "breadth": 0.42,
    "macro": 0.28,
    "sectors": 0.38,
    "combined": 0.33
  },
  
  "reasoning": "IHSG BEARISH: Combined score 0.33 (MEDIUM confidence). Momentum=0.35, Breadth=0.42, Macro=0.28, Sectors=0.38",
  "key_drivers": ["RSI oversold (35)", "A/D ratio weak (0.8)", "USD/IDR weakening"],
  "risks": ["Macro uncertain", "Volume low"],
  "data_used": ["IHSG: 5840", "A/D Ratio: 0.80", "Participation: 38%", "USD/IDR: 16200"],
  "ihsg_trend": "BEARISH",
  "macro_signal": "BEARISH",
  "timestamp": "2026-06-04T16:30:00"
}
```

---

## Performance Tracking

Sistem otomatis tracking accuracy:

```sql
-- Check D+1 forecast vs actual
SELECT 
  run_date,
  day_1_price as forecast,
  (SELECT close FROM ... WHERE date = run_date+1) as actual,
  ROUND(((actual - forecast) / forecast * 100), 2) as error_pct
FROM ihsg_predictions
ORDER BY run_date DESC
LIMIT 30;
```

---

## Integration with Stock Picks

IHSG Predictor **independent** dari stock picks tapi bisa digunakan untuk:

1. **Risk Management**
   - IHSG BEARISH → reduce position size atau skip picks
   - IHSG BULLISH → increase conviction/allocation

2. **Portfolio Timing**
   - IHSG oversold (D+1 -2%) → good entry for longs
   - IHSG overbought (D+1 +2%) → good entry for shorts

3. **Sector Allocation**
   - IHSG sector rotation signal → adjust sector weights

---

## Troubleshooting

### LLM Service Unavailable
- IHSG predictor **tetap berjalan** (rule-based, no LLM dependency)
- Output akan tanpa narrative enhancement, hanya numeric + reasoning template

### Database Connection Error
- Restart postgres: `docker-compose down && docker-compose up -d`
- Check schema: `docker-compose exec postgres psql -U stockuser -d stockagent -c "\dt"`

### Prediction Seems Off
- Check data freshness: `SELECT MAX(run_date) FROM ihsg_predictions;`
- Check data sources: verify yfinance/Stockbit API availability
- Rerun analysis: `docker-compose exec app python scripts/run_analysis.py`

---

## Future Enhancements

- [ ] Sentiment analysis dari IHSG-specific news (NewsAPI integration)
- [ ] VIX equivalent dari option data
- [ ] Multi-model ensemble (combine technical + ML forecasts)
- [ ] Auto-alert jika IHSG breaks resistance/support
- [ ] Performance dashboard (hit rate, accuracy by horizon)

---

## References

- **Data Sources**:
  - IHSG: yfinance ticker `^JKSE`
  - LQ45 breadth: Individual yfinance tickers
  - Sectors: yfinance sector indices
  - Macro: yfinance `USDIDR=X`

- **Related Code**:
  - Agent patterns: `agents/technical.py`, `agents/macro.py`
  - Workflow: `graph/workflow.py`
  - UI patterns: `ui/app.py` (Performance tab)
  - DB: `db/models.py`, `db/tracker.py`

---

**Last Updated**: 2026-06-04
**Status**: ✅ MVP Complete — Ready for production use
