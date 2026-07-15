"""
Test: Commodity Price Discovery Integration
=============================================

Demo script untuk verify:
1. Commodity analysis dengan price discovery
2. Bonus/penalty diterapkan ke composite score
3. Apakah stock sudah price in commodity move atau belum
"""
import logging
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s:%(name)s: %(message)s'
)
logger = logging.getLogger(__name__)

from agents.commodity_price_discovery import (
    analyze_with_price_discovery,
    calculate_adjusted_commodity_bonus,
    _calculate_price_discovery_gap,
)
from data.fetcher_commodity import get_commodity_price
from data.fetcher_stockbit import get_ohlcv


def demo_price_discovery():
    """Demo 1: Show price discovery check."""
    print("\n" + "="*80)
    print("DEMO 1: Price Discovery — Apakah Stock Sudah Price In Commodity Move?")
    print("="*80)

    example_tickers = ["ANTM", "PTBA", "AALI", "INCO"]

    for ticker in example_tickers:
        print(f"\n{'─'*80}")
        print(f"📊 {ticker}")
        print(f"{'─'*80}")

        try:
            # Analyze dengan price discovery
            analysis = analyze_with_price_discovery(ticker)

            if analysis.get("error"):
                print(f"  ⚠️  {analysis['error']}")
                continue

            # Show stock price changes
            stock_context = analysis.get("stock_price_context", {})
            stock_1d = stock_context.get("change_1d", 0)
            stock_2d = stock_context.get("change_2d", 0)

            print(f"\n  Stock Price Changes:")
            print(f"    1-day:  {stock_1d:+.2f}%")
            print(f"    2-day:  {stock_2d:+.2f}%")

            # Show commodity analysis with price discovery
            print(f"\n  Commodity Analysis:")
            for commodity in analysis.get("commodities", []):
                name = commodity.get("name", "")
                change = commodity.get("change_percent", 0)
                trend = commodity.get("trend", "")

                discovery = commodity.get("price_discovery", {})
                gap_1d = discovery.get("gap_1d", 0)
                sentiment = discovery.get("sentiment", "")
                narrative = discovery.get("narrative", "")

                print(f"\n    {name} ({commodity['symbol']})")
                print(f"      Price: {change:+.2f}% → {trend}")
                print(f"      Gap (1d): {gap_1d:+.2f}% | Sentiment: {sentiment}")
                print(f"      → {narrative}")

            # Show adjusted sentiment if changed
            if analysis.get("sentiment_adjusted"):
                print(f"\n  ⚡ Sentiment Adjusted:")
                print(f"     Reason: {analysis.get('sentiment_reason')}")

        except Exception as e:
            logger.error(f"Error analyzing {ticker}: {e}", exc_info=True)


def demo_bonus_calculation():
    """Demo 2: Show how bonus is calculated."""
    print("\n" + "="*80)
    print("DEMO 2: Composite Score Bonus Calculation")
    print("="*80)

    test_cases = [
        {
            "name": "Commodity up + Stock lagging → Bullish bonus",
            "commodity_change": 2.5,
            "stock_1d": 0.5,
            "stock_2d": 0.8,
            "exposure": "high",
        },
        {
            "name": "Commodity up + Stock already up → No bonus",
            "commodity_change": 2.0,
            "stock_1d": 2.5,
            "stock_2d": 2.2,
            "exposure": "high",
        },
        {
            "name": "Commodity down + Stock resist → Neutral",
            "commodity_change": -1.5,
            "stock_1d": 0.2,
            "stock_2d": -0.1,
            "exposure": "medium",
        },
        {
            "name": "Mixed exposure → Lower adjustment",
            "commodity_change": 1.0,
            "stock_1d": 0.8,
            "stock_2d": 0.6,
            "exposure": "low",
        },
    ]

    for test_case in test_cases:
        print(f"\n{'─'*80}")
        print(f"📈 {test_case['name']}")
        print(f"{'─'*80}")

        discovery = _calculate_price_discovery_gap(
            test_case["commodity_change"],
            test_case["stock_1d"],
            test_case["stock_2d"],
            test_case["exposure"],
        )

        print(f"  Input:")
        print(f"    Commodity change: {test_case['commodity_change']:+.2f}%")
        print(f"    Stock 1-day:      {test_case['stock_1d']:+.2f}%")
        print(f"    Stock 2-day:      {test_case['stock_2d']:+.2f}%")
        print(f"    Exposure level:   {test_case['exposure']}")

        print(f"\n  Price Discovery Analysis:")
        print(f"    Gap (1d):        {discovery['gap_1d']:+.2f}%")
        print(f"    Gap (2d):        {discovery['gap_2d']:+.2f}%")
        print(f"    Sentiment:       {discovery['sentiment']}")
        print(f"    Priced In:       {discovery['is_priced_in']}")
        print(f"    Narrative:       {discovery['narrative']}")


def demo_full_ticker_analysis():
    """Demo 3: Full analysis for one ticker."""
    print("\n" + "="*80)
    print("DEMO 3: Full Ticker Analysis with Price Discovery")
    print("="*80 + "\n")

    ticker = "ANTM"

    try:
        print(f"Analyzing {ticker}...\n")

        # Get analysis
        analysis = analyze_with_price_discovery(ticker)

        if analysis.get("error"):
            print(f"Error: {analysis['error']}")
            return

        # Overall summary
        print(f"📊 SUMMARY:")
        print(f"  Ticker:           {ticker}")
        print(f"  Overall Score:    {analysis.get('overall_score', 0)}/10")
        print(f"  Sentiment:        {analysis.get('sentiment', 'UNKNOWN')}")
        print(f"  Commodities:      {len(analysis.get('commodities', []))} exposure(s)")

        # Stock price context
        stock_ctx = analysis.get("stock_price_context", {})
        print(f"\n📈 STOCK PRICE:")
        print(f"  1-day change:     {stock_ctx.get('change_1d', 0):+.2f}%")
        print(f"  2-day change:     {stock_ctx.get('change_2d', 0):+.2f}%")

        # Commodity details
        if analysis.get("commodities"):
            print(f"\n⛏️  COMMODITY EXPOSURE:")
            for c in analysis["commodities"]:
                discovery = c.get("price_discovery", {})
                print(f"\n  {c['name']}")
                print(f"    Symbol:        {c['symbol']}")
                print(f"    Current Price: ${c['current_price']:.2f} ({c['change_percent']:+.2f}%)")
                print(f"    Trend:         {c['trend']}")
                print(f"    Score:         {c['score']}/10")
                print(f"    Gap (1d):      {discovery.get('gap_1d', 0):+.2f}%")
                print(f"    Sentiment:     {discovery.get('sentiment', 'N/A')}")
                print(f"    Analysis:      {discovery.get('narrative', '')}")

        # Adjusted sentiment
        if analysis.get("sentiment_adjusted"):
            print(f"\n⚡ ADJUSTMENT:")
            print(f"  Reason: {analysis.get('sentiment_reason')}")

        # Calculate bonus
        bonus, narrative = calculate_adjusted_commodity_bonus(analysis)
        print(f"\n💰 COMPOSITE SCORE IMPACT:")
        print(f"  Adjustment:  {bonus:+.2f} points")
        print(f"  Impact:      {narrative}")

        if bonus > 0:
            print(f"  → Stock gets BONUS (bullish gap not yet priced in)")
        elif bonus < 0:
            print(f"  → Stock gets PENALTY (commodity move already captured)")
        else:
            print(f"  → No adjustment (fairly valued)")

    except Exception as e:
        logger.error(f"Error in full analysis: {e}", exc_info=True)


if __name__ == "__main__":
    print("\n" + "="*80)
    print("COMMODITY PRICE DISCOVERY SYSTEM — COMPREHENSIVE TEST")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)

    try:
        demo_price_discovery()
        demo_bonus_calculation()
        demo_full_ticker_analysis()

        print("\n" + "="*80)
        print("✅ TEST COMPLETE")
        print("="*80 + "\n")

    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
