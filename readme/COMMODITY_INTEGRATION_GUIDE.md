"""
Commodity System Integration Guide
====================================

📦 FILES CREATED:
─────────────────────────────────────────────────────────────────────
1. data/commodity_mapper.py
   - Maps 10+ commodities to IDX tickers
   - Gold→ANTM, Coal→PTBA/ADRO/ITMG, Oil→BRPT/ADRO, etc.
   - Provides: get_commodities_for_ticker(), get_tickers_for_commodity()

2. data/fetcher_commodity.py
   - Fetches live commodity prices from yfinance
   - Symbols: GC=F (Gold), CL=F (Oil), NG=F (Gas), HG=F (Copper), etc.
   - Caches prices with 1-hour TTL
   - Returns OHLCV + 52-week highs/lows

3. agents/commodity_analyst.py
   - Analyzes commodity exposure per ticker
   - Scores: 0-10 based on trend + exposure level
   - Sentiment: POSITIVE / NEUTRAL / NEGATIVE
   - Rationale: Human-readable explanation

4. agents/commodity_integration.py
   - Helper functions for workflow integration
   - enrich_ticker_with_commodities() → adds commodity score to ticker
   - add_commodity_context_to_macro() → enriches macro_data
   - format_commodity_summary_for_report() → report formatting

5. test_commodity_demo.py
   - Complete demo script showing all features
   - Run: python test_commodity_demo.py

─────────────────────────────────────────────────────────────────────

🔌 WORKFLOW INTEGRATION:
─────────────────────────────────────────────────────────────────────

✅ Already integrated in graph/workflow.py:
   - Line 22-28: Imports added
   - Line 73-78: Commodity context added to macro_data in Phase 2

The macro_data now contains:
   {
       "commodity_overview": {commodity → price data},
       "bullish_commodities": [{commodity, change}, ...],
       "bearish_commodities": [{commodity, change}, ...],
       ... (existing macro data)
   }

─────────────────────────────────────────────────────────────────────

💡 HOW TO USE:
─────────────────────────────────────────────────────────────────────

1. SIMPLE: Get commodity prices
   ──────────────────────────────
   from data.fetcher_commodity import get_commodity_price
   
   gold_data = get_commodity_price("gold")
   # Returns: {current_price, change_percent, high_52w, low_52w, ...}

2. ANALYZE: Score ticker's commodity exposure
   ────────────────────────────────────────────
   from agents.commodity_analyst import analyze
   
   result = analyze("ANTM")
   # Returns: {overall_score, sentiment, commodities[], rationale}

3. ENRICH SCORES: Add commodity factor to composite score
   ────────────────────────────────────────────────────────
   from agents.commodity_integration import enrich_ticker_with_commodities
   
   commodity_info = enrich_ticker_with_commodities("PTBA", scores)
   # Returns: {commodity_score, commodity_analysis, impact}

4. MARKET OVERVIEW: See global commodity sentiment
   ────────────────────────────────────────────────
   from agents.commodity_analyst import get_commodity_market_overview
   
   overview = get_commodity_market_overview()
   # Returns: {commodities, top_bullish, top_bearish}

─────────────────────────────────────────────────────────────────────

🎯 COMMODITY EXPOSURE EXAMPLES:
─────────────────────────────────────────────────────────────────────

ANTM (Antam)         → Gold (HIGH exposure)
PTBA (Pertamina)     → Coal (HIGH exposure)
PGAS (Gas Negara)    → Natural Gas (HIGH exposure)
INCO (Vale Indonesia)→ Nickel (HIGH exposure)
AALI (Astra Agro)    → Palm Oil (HIGH exposure)
SMGR (Semen Gresik)  → Cement (MEDIUM exposure)
ADRO (Adaro)         → Coal + Oil (HIGH exposure)
BRPT (Barito Pacific)→ Oil (HIGH exposure)
TINS (Timah)         → Tin (HIGH exposure)

─────────────────────────────────────────────────────────────────────

📊 RESULT STRUCTURE:
─────────────────────────────────────────────────────────────────────

analyze("ANTM") returns:
{
    "ticker": "ANTM",
    "commodities": [
        {
            "commodity": "gold",
            "name": "Gold",
            "symbol": "GC=F",
            "exposure": "high",
            "current_price": 2050.50,
            "change_percent": +1.23,
            "trend": "BULLISH",
            "strength": 2.46,
            "percentile_52w": 75.2,
            "score": 7.5,
            "impact": "positive"
        }
    ],
    "overall_score": 7.5,
    "sentiment": "POSITIVE",
    "rationale": "ANTM has 1 commodity exposures (Gold). Overall score: 7.5/10..."
}

─────────────────────────────────────────────────────────────────────

🚀 NEXT STEPS:
─────────────────────────────────────────────────────────────────────

Option A: Add to composite score calculation
   - Modify graph/scoring.py to include commodity_score
   - Weight: 5-10% of composite (optional)

Option B: Add to debate phase
   - Reference commodity sentiment in Round 1 arguments
   - Commodity trends as cross-exam ammunition in Round 2

Option C: Add to investment manager decision
   - Use commodity outlook in final decision rationale
   - Reject/confirm picks based on commodity alignment

Option D: Create commodity-specific reports
   - Generate "Commodity Winners" report each day
   - Show which sectors benefit from current commodity prices

─────────────────────────────────────────────────────────────────────

🧪 TO TEST:

   python test_commodity_demo.py

Expected output:
   ✓ Commodity mapping
   ✓ Live prices for 6+ commodities
   ✓ Ticker analysis (ANTM, PTBA, PGAS, AALI)
   ✓ Market-wide overview
   ✓ Integration examples

─────────────────────────────────────────────────────────────────────
"""

if __name__ == "__main__":
    print(__doc__)
