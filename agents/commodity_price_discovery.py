"""
Commodity Score with Price Discovery Check
============================================

Enhanced commodity scoring yang mempertimbangkan apakah stock sudah price in
commodity movement atau belum.

Logic:
- Commodity naik 2%, stock naik 0.5% (1d) → Stock belum price in → Bullish signal ✓
- Commodity naik 2%, stock naik 3% (1d) → Stock sudah ahead → No bonus (neutral)
- Commodity turun 1%, stock naik 0.5% (1d) → Stock fighting headwind → Bearish signal ✓
"""
import logging
from typing import Optional
from data.fetcher_commodity import get_commodity_price, get_ticker_commodities_prices
from data.fetcher_stockbit import get_ohlcv
from agents.commodity_analyst import analyze as analyze_commodity

logger = logging.getLogger(__name__)


def _calculate_price_discovery_gap(
    commodity_change_pct: float,
    stock_change_1d: float,
    stock_change_2d: float,
    exposure_level: str = "high",
) -> dict:
    """
    Hitung berapa banyak commodity move yang belum ter-price in di stock.

    Args:
        commodity_change_pct: % perubahan harga komoditi (1d)
        stock_change_1d: % perubahan harga stock (1d)
        stock_change_2d: % perubahan harga stock (2d)
        exposure_level: "high", "medium", "low"

    Returns:
        {
            "gap_1d": float,        # Commodity change - stock 1d change
            "gap_2d": float,        # Commodity change - stock 2d change
            "is_priced_in": bool,   # Apakah stock sudah price in?
            "sentiment": str,       # "bullish", "neutral", "bearish"
            "narrative": str        # Penjelasan
        }

    Logic:
    - If gap > 0: Stock underperformed commodity → Bullish (upside potential)
    - If gap < -0.5: Stock outperformed commodity → Bearish (already priced in)
    - If gap near 0: Stock in line with commodity → Neutral (fairly priced)
    """
    gap_1d = commodity_change_pct - stock_change_1d
    gap_2d = commodity_change_pct - stock_change_2d

    # Exposure sensitivity (high exposure = larger acceptable gap)
    gap_threshold = {
        "high": 0.3,      # Need >0.3% gap to confirm not priced in
        "medium": 0.2,
        "low": 0.1,
    }.get(exposure_level, 0.2)

    # Determine if priced in
    if gap_1d < -gap_threshold:
        # Stock significantly outperformed → likely priced in
        is_priced_in = True
        sentiment = "bearish"
        narrative = f"Stock already outpaced commodity by {abs(gap_1d):.2f}% — move likely priced in"
    elif gap_1d > gap_threshold:
        # Stock significantly underperformed → opportunity
        is_priced_in = False
        if commodity_change_pct > 0:
            sentiment = "bullish"
            narrative = f"Commodity up {commodity_change_pct:.2f}% but stock only +{stock_change_1d:.2f}% (gap={gap_1d:.2f}%) — upside potential"
        else:
            sentiment = "bearish"
            narrative = f"Commodity down {abs(commodity_change_pct):.2f}% but stock resist — headwind concern (gap={gap_1d:.2f}%)"
    else:
        # In line with commodity → fairly priced
        is_priced_in = True
        sentiment = "neutral"
        narrative = f"Stock in line with commodity movement (gap={gap_1d:.2f}%) — fairly valued"

    return {
        "gap_1d": round(gap_1d, 2),
        "gap_2d": round(gap_2d, 2),
        "is_priced_in": is_priced_in,
        "sentiment": sentiment,
        "narrative": narrative,
        "threshold_used": gap_threshold,
    }


def analyze_with_price_discovery(ticker: str) -> dict:
    """
    Analyze commodity exposure dengan price discovery check.

    Returns base commodity analysis + price discovery metrics.
    """
    try:
        # Get commodity analysis
        commodity_analysis = analyze_commodity(ticker)

        if commodity_analysis.get("error") or not commodity_analysis.get("commodities"):
            return commodity_analysis

        # Get stock price changes
        try:
            ohlcv = get_ohlcv(ticker, period="1mo")
            if ohlcv.empty or len(ohlcv) < 3:
                logger.warning(f"[PRICE_DISCOVERY] Not enough OHLCV data for {ticker}")
                return commodity_analysis

            # Calculate 1d and 2d returns
            current_close = ohlcv["Close"].iloc[-1]
            close_1d_ago = ohlcv["Close"].iloc[-2]
            close_2d_ago = ohlcv["Close"].iloc[-3] if len(ohlcv) >= 3 else close_1d_ago

            stock_change_1d = ((current_close - close_1d_ago) / close_1d_ago * 100)
            stock_change_2d = ((current_close - close_2d_ago) / close_2d_ago * 100)

        except Exception as e:
            logger.warning(f"[PRICE_DISCOVERY] Error getting stock prices for {ticker}: {e}")
            return commodity_analysis

        # Enrich each commodity with price discovery
        discovery_results = []

        for commodity_info in commodity_analysis.get("commodities", []):
            commodity = commodity_info["commodity"]
            exposure = commodity_info.get("exposure", "medium")
            commodity_change = commodity_info.get("change_percent", 0)

            # Calculate price discovery
            discovery = _calculate_price_discovery_gap(
                commodity_change,
                stock_change_1d,
                stock_change_2d,
                exposure
            )

            commodity_info["price_discovery"] = discovery
            discovery_results.append(discovery)

        # Adjust overall sentiment based on price discovery
        if discovery_results:
            # Count sentiments
            bullish_count = sum(1 for d in discovery_results if d["sentiment"] == "bullish")
            bearish_count = sum(1 for d in discovery_results if d["sentiment"] == "bearish")

            original_sentiment = commodity_analysis.get("sentiment", "NEUTRAL")

            # Only upgrade/downgrade if significant
            if bullish_count > bearish_count and bullish_count >= len(discovery_results) * 0.5:
                if original_sentiment != "POSITIVE":
                    commodity_analysis["sentiment_adjusted"] = True
                    commodity_analysis["sentiment_reason"] = (
                        f"Commodity moves not fully priced in ({bullish_count} bullish gaps)"
                    )
            elif bearish_count > bullish_count and bearish_count >= len(discovery_results) * 0.5:
                if original_sentiment != "NEGATIVE":
                    commodity_analysis["sentiment_adjusted"] = True
                    commodity_analysis["sentiment_reason"] = (
                        f"Moves already priced in ({bearish_count} fully captured)"
                    )

            # Add stock price context
            commodity_analysis["stock_price_context"] = {
                "change_1d": round(stock_change_1d, 2),
                "change_2d": round(stock_change_2d, 2),
            }

        logger.info(
            f"[PRICE_DISCOVERY] {ticker}: "
            f"Stock {stock_change_1d:+.2f}% (1d), {stock_change_2d:+.2f}% (2d) "
            f"vs commodities → {bullish_count}B {bearish_count}Be"
        )

        return commodity_analysis

    except Exception as e:
        logger.error(f"[PRICE_DISCOVERY] Error analyzing {ticker}: {e}")
        return analyze_commodity(ticker)


def calculate_adjusted_commodity_bonus(
    commodity_analysis: dict,
) -> tuple[float, str]:
    """
    Calculate final commodity score adjustment with price discovery.

    Returns:
        (adjustment_value, narrative)

    Logic:
    - Bullish gap + high exposure = max bonus (+1.0)
    - Fully priced in = no bonus (0.0)
    - Bearish gap = penalty (-0.5)
    """
    if not commodity_analysis.get("commodities"):
        return (0.0, "")

    # Count price discovery sentiments
    bullish_count = 0
    bearish_count = 0
    neutral_count = 0

    for commodity in commodity_analysis.get("commodities", []):
        discovery = commodity.get("price_discovery", {})
        sentiment = discovery.get("sentiment", "neutral")

        if sentiment == "bullish":
            bullish_count += 1
        elif sentiment == "bearish":
            bearish_count += 1
        else:
            neutral_count += 1

    total = len(commodity_analysis["commodities"])

    # Calculate adjustment based on discovery
    if bullish_count > total * 0.5:
        # Mostly bullish gaps → apply bonus
        commodity_score = commodity_analysis.get("overall_score", 5)
        adjustment = ((commodity_score - 5) * 0.1) * 1.2  # 20% boost for unexploited gap

        narrative = (
            f"Commodity tailwind + unexploited gap ({bullish_count}/{total} bullish) → "
            f"adjustment: +{adjustment:.2f}"
        )

    elif bearish_count > total * 0.5:
        # Mostly already priced in → reduce bonus
        commodity_score = commodity_analysis.get("overall_score", 5)
        adjustment = ((commodity_score - 5) * 0.05) * 0.5  # 50% reduction for already priced

        narrative = (
            f"Commodity move already priced in ({bearish_count}/{total} captured) → "
            f"adjustment: {adjustment:.2f}"
        )

    else:
        # Mixed → no significant adjustment
        adjustment = 0.0
        narrative = "Commodity moves fairly priced in stock"

    return (round(adjustment, 2), narrative)
