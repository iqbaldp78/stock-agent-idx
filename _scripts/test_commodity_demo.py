"""
Test & Demo — Commodity System
Menunjukkan cara kerja commodity fetcher, mapper, dan analyzer.
"""
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s:%(name)s: %(message)s'
)
logger = logging.getLogger(__name__)

from data.commodity_mapper import (
    get_commodities_for_ticker,
    get_tickers_for_commodity,
    get_all_commodities,
)
from data.fetcher_commodity import (
    get_commodity_price,
    get_ticker_commodities_prices,
    get_all_commodity_prices,
    format_commodity_for_display,
)
from agents.commodity_analyst import (
    analyze,
    get_commodity_market_overview,
)


def demo_1_commodity_mapping():
    """Demo 1: Show commodity-ticker mapping."""
    print("\n" + "="*70)
    print("DEMO 1: Commodity-Ticker Mapping")
    print("="*70)

    # Show all commodities
    all_commodities = get_all_commodities()
    print(f"\n✓ Total commodities tracked: {len(all_commodities)}")
    print(f"  {', '.join(all_commodities)}")

    # Show ticker examples
    print("\n✓ Ticker Examples:")
    example_tickers = ["ANTM", "PTBA", "PGAS", "INCO", "AALI", "SMGR"]
    for ticker in example_tickers:
        commodities = get_commodities_for_ticker(ticker)
        if commodities:
            commodity_names = ", ".join([c["name"] for c in commodities])
            print(f"  {ticker:6s} → {commodity_names}")


def demo_2_commodity_prices():
    """Demo 2: Fetch & display commodity prices."""
    print("\n" + "="*70)
    print("DEMO 2: Live Commodity Prices")
    print("="*70)

    commodities = ["gold", "coal", "oil", "natural_gas", "nickel", "palm_oil"]

    for commodity in commodities:
        try:
            price_data = get_commodity_price(commodity)
            if price_data:
                display = format_commodity_for_display(price_data)
                print(f"\n{display}")
        except Exception as e:
            logger.error(f"Error fetching {commodity}: {e}")


def demo_3_ticker_analysis():
    """Demo 3: Analyze commodity exposure per ticker."""
    print("\n" + "="*70)
    print("DEMO 3: Ticker Commodity Exposure Analysis")
    print("="*70)

    example_tickers = ["ANTM", "PTBA", "PGAS", "AALI"]

    for ticker in example_tickers:
        print(f"\n{'─'*70}")
        print(f"Analyzing: {ticker}")
        print(f"{'─'*70}")

        try:
            analysis = analyze(ticker)

            if analysis.get("error"):
                print(f"  ⚠️  {analysis['error']}")
                continue

            print(f"  Overall Score: {analysis['overall_score']}/10")
            print(f"  Sentiment: {analysis['sentiment']}")
            print(f"  Rationale: {analysis['rationale']}")

            if analysis.get("commodities"):
                print(f"\n  Commodities:")
                for c in analysis["commodities"]:
                    impact_emoji = "📈" if c["impact"] == "positive" else (
                        "📉" if c["impact"] == "negative" else "➖"
                    )
                    print(
                        f"    {impact_emoji} {c['name']:20s} → "
                        f"${c['current_price']:8.2f} {c['currency']:15s} "
                        f"{c['trend']:10s} (score={c['score']})"
                    )

        except Exception as e:
            logger.error(f"Error analyzing {ticker}: {e}")


def demo_4_market_overview():
    """Demo 4: Show market-wide commodity overview."""
    print("\n" + "="*70)
    print("DEMO 4: Market-Wide Commodity Overview")
    print("="*70)

    try:
        overview = get_commodity_market_overview()

        print("\n📊 Current Commodity Prices:")
        for commodity, data in overview.get("commodities", {}).items():
            trend_emoji = "📈" if data["trend"] == "BULLISH" else (
                "📉" if data["trend"] == "BEARISH" else "➖"
            )
            print(
                f"  {trend_emoji} {commodity:15s} → "
                f"${data['current_price']:8.2f} ({data['change_percent']:+.2f}%)"
            )

        print("\n🔼 Bullish Commodities:")
        for item in overview.get("top_bullish", []):
            print(f"  ✓ {item['commodity']:15s} {item['change']:+.2f}%")

        print("\n🔽 Bearish Commodities:")
        for item in overview.get("top_bearish", []):
            print(f"  ✗ {item['commodity']:15s} {item['change']:+.2f}%")

    except Exception as e:
        logger.error(f"Error getting market overview: {e}")


def demo_5_integration_example():
    """Demo 5: Show how to use in workflow integration."""
    print("\n" + "="*70)
    print("DEMO 5: Workflow Integration Example")
    print("="*70)

    print("""
    # How to use in workflow:

    from agents.commodity_integration import (
        add_commodity_context_to_macro,
        enrich_ticker_with_commodities,
    )

    # In Phase 2 (Macro Analysis):
    macro_data = macro_analyze()
    macro_data = add_commodity_context_to_macro(macro_data)

    # In scoring for each ticker:
    commodity_info = enrich_ticker_with_commodities(ticker, scores)
    scores[ticker]["commodity"] = commodity_info

    # Access commodity context in other phases:
    bullish_commodities = macro_data.get("bullish_commodities", [])
    bearish_commodities = macro_data.get("bearish_commodities", [])
    commodity_overview = macro_data.get("commodity_overview", {})

    # Result: Scores now include commodity exposure impact!
    """)


if __name__ == "__main__":
    print("\n" + "="*70)
    print("COMMODITY SYSTEM — COMPREHENSIVE TEST & DEMO")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)

    try:
        demo_1_commodity_mapping()
        demo_2_commodity_prices()
        demo_3_ticker_analysis()
        demo_4_market_overview()
        demo_5_integration_example()

        print("\n" + "="*70)
        print("✅ DEMO COMPLETE")
        print("="*70 + "\n")

    except Exception as e:
        logger.error(f"Fatal error in demo: {e}", exc_info=True)
