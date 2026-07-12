"""
Commodity Analyst Agent — Analisa dampak harga komoditi pada ticker IDX.
Bagian dari macro analysis, fokus pada commodity exposure & sentiment.
"""
import logging
from typing import Optional

from data.fetcher_commodity import (
    get_commodity_price,
    get_ticker_commodities_prices,
    get_all_commodity_prices,
)
from data.commodity_mapper import get_commodities_for_ticker, COMMODITY_TO_TICKERS

logger = logging.getLogger(__name__)


def _analyze_commodity_trend(price_data: dict) -> dict:
    """
    Analisa trend komoditi berdasarkan perubahan harga.
    """
    if not price_data:
        return {"trend": "UNKNOWN", "strength": 0}

    change_percent = price_data.get("change_percent", 0)
    high_52w = price_data.get("high_52w", 1)
    low_52w = price_data.get("low_52w", 1)
    current = price_data.get("current_price", 1)

    # Persentil dalam 52-week range
    percentile = ((current - low_52w) / (high_52w - low_52w) * 100) if (high_52w != low_52w) else 50

    # Determine trend
    if change_percent > 2:
        trend = "BULLISH"
    elif change_percent < -2:
        trend = "BEARISH"
    else:
        trend = "NEUTRAL"

    # Strength (0-10)
    strength = min(10, abs(change_percent) * 2)

    return {
        "trend": trend,
        "strength": round(strength, 1),
        "change_percent": change_percent,
        "percentile_52w": round(percentile, 1),
        "near_high": percentile > 80,
        "near_low": percentile < 20,
    }


def analyze(ticker: str) -> dict:
    """
    Commodity exposure analysis untuk ticker.

    Returns:
        {
            "ticker": "ANTM",
            "commodities": [
                {
                    "commodity": "gold",
                    "exposure": "high",
                    "current_price": 2050.50,
                    "trend": "BULLISH",
                    "score": 7.5,
                    "impact": "positive"
                }
            ],
            "overall_score": 7.2,
            "sentiment": "POSITIVE",
            "rationale": "..."
        }
    """
    result = {
        "ticker": ticker,
        "commodities": [],
        "overall_score": 0,
        "sentiment": "NEUTRAL",
        "rationale": "",
        "error": None,
    }

    try:
        # Get commodities terkait ticker
        commodities = get_commodities_for_ticker(ticker)

        if not commodities:
            result["error"] = f"No commodities mapped to {ticker}"
            logger.info(f"[COMMODITY] {ticker} has no commodity mapping")
            return result

        logger.info(f"[COMMODITY] Analyzing {ticker} ({len(commodities)} commodities)")

        scores = []
        sentiments = []

        for commodity_info in commodities:
            commodity = commodity_info["commodity"]
            exposure = commodity_info.get("exposure", "medium")

            try:
                # Fetch commodity price
                price_data = get_commodity_price(commodity, period="1d")
                if not price_data:
                    continue

                # Analisa trend
                trend_data = _analyze_commodity_trend(price_data)

                # Map exposure level ke weight (0-10)
                exposure_weight = {
                    "high": 10,
                    "medium": 7,
                    "low": 4,
                }.get(exposure, 7)

                # Hitung score (0-10)
                trend_strength = trend_data["strength"]
                trend_multiplier = 1 if trend_data["trend"] == "BULLISH" else (
                    -1 if trend_data["trend"] == "BEARISH" else 0
                )
                score = 5 + (trend_strength * trend_multiplier)
                score = max(0, min(10, score))

                # Determine impact
                if trend_data["trend"] == "BULLISH" and exposure_weight >= 7:
                    impact = "positive"
                elif trend_data["trend"] == "BEARISH" and exposure_weight >= 7:
                    impact = "negative"
                else:
                    impact = "neutral"

                commodity_result = {
                    "commodity": commodity,
                    "name": price_data["name"],
                    "symbol": price_data["symbol"],
                    "exposure": exposure,
                    "current_price": price_data["current_price"],
                    "currency": price_data["currency"],
                    "change_percent": price_data["change_percent"],
                    "trend": trend_data["trend"],
                    "strength": trend_data["strength"],
                    "percentile_52w": trend_data["percentile_52w"],
                    "score": round(score, 1),
                    "impact": impact,
                }

                result["commodities"].append(commodity_result)
                scores.append(score)
                sentiments.append(impact)

                logger.info(
                    f"  [{commodity}] {price_data['symbol']} → "
                    f"${price_data['current_price']} {trend_data['trend']} (score={score:.1f})"
                )

            except Exception as e:
                logger.warning(f"  Error analyzing {commodity}: {e}")
                continue

        # Calculate overall score
        if scores:
            overall_score = sum(scores) / len(scores)
            result["overall_score"] = round(overall_score, 1)

            # Determine overall sentiment
            positive_count = sentiments.count("positive")
            negative_count = sentiments.count("negative")

            if positive_count > negative_count:
                result["sentiment"] = "POSITIVE"
            elif negative_count > positive_count:
                result["sentiment"] = "NEGATIVE"
            else:
                result["sentiment"] = "NEUTRAL"

            # Build rationale
            commodity_names = ", ".join([c["name"] for c in result["commodities"]])
            result["rationale"] = (
                f"{ticker} has {len(result['commodities'])} commodity exposures ({commodity_names}). "
                f"Overall score: {result['overall_score']}/10, sentiment: {result['sentiment']}. "
            )

            if result["sentiment"] == "POSITIVE":
                bullish_commodities = [c["name"] for c in result["commodities"] if c["impact"] == "positive"]
                if bullish_commodities:
                    result["rationale"] += f"Strong tailwinds from {', '.join(bullish_commodities)}."
            elif result["sentiment"] == "NEGATIVE":
                bearish_commodities = [c["name"] for c in result["commodities"] if c["impact"] == "negative"]
                if bearish_commodities:
                    result["rationale"] += f"Headwinds from {', '.join(bearish_commodities)}."

        logger.info(f"[COMMODITY] {ticker} final score: {result['overall_score']}/10 ({result['sentiment']})")

    except Exception as e:
        logger.error(f"[COMMODITY] Error analyzing {ticker}: {e}")
        result["error"] = str(e)

    return result


def analyze_from_cache(ticker: str) -> dict:
    """
    Commodity exposure analysis untuk ticker, HANYA dari cache (no API call).
    Dipanggil per-ticker setelah preload_all_commodities() di awal workflow.

    Returns:
        {
            "ticker": "ANTM",
            "commodities": [
                {
                    "commodity": "gold",
                    "exposure": "high",
                    "current_price": 2050.50,
                    "trend": "BULLISH",
                    "score": 7.5,
                    "impact": "positive"
                }
            ],
            "overall_score": 7.2,
            "sentiment": "POSITIVE",
            "rationale": "...",
            "cached": True
        }
    """
    from data.fetcher_commodity import _PRICE_CACHE

    result = {
        "ticker": ticker,
        "commodities": [],
        "overall_score": 0,
        "sentiment": "NEUTRAL",
        "rationale": "",
        "error": None,
        "cached": True,
    }

    try:
        # Get commodities terkait ticker
        commodities = get_commodities_for_ticker(ticker)

        if not commodities:
            result["error"] = f"No commodities mapped to {ticker}"
            logger.debug(f"[COMMODITY] {ticker} has no commodity mapping")
            return result

        logger.debug(f"[COMMODITY] Analyzing {ticker} from cache ({len(commodities)} commodities)")

        scores = []
        sentiments = []

        for commodity_info in commodities:
            commodity = commodity_info["commodity"]
            exposure = commodity_info.get("exposure", "medium")

            try:
                # Get dari cache SAJA (tidak fetch API)
                price_data = _PRICE_CACHE.get(commodity)
                if not price_data:
                    logger.debug(f"  [{commodity}] Not in cache for {ticker} - skipping")
                    continue

                # Analisa trend
                trend_data = _analyze_commodity_trend(price_data)

                # Map exposure level ke weight (0-10)
                exposure_weight = {
                    "high": 10,
                    "medium": 7,
                    "low": 4,
                }.get(exposure, 7)

                # Hitung score (0-10)
                trend_strength = trend_data["strength"]
                trend_multiplier = 1 if trend_data["trend"] == "BULLISH" else (
                    -1 if trend_data["trend"] == "BEARISH" else 0
                )
                score = 5 + (trend_strength * trend_multiplier)
                score = max(0, min(10, score))

                # Determine impact
                if trend_data["trend"] == "BULLISH" and exposure_weight >= 7:
                    impact = "positive"
                elif trend_data["trend"] == "BEARISH" and exposure_weight >= 7:
                    impact = "negative"
                else:
                    impact = "neutral"

                commodity_result = {
                    "commodity": commodity,
                    "name": price_data["name"],
                    "symbol": price_data["symbol"],
                    "exposure": exposure,
                    "current_price": price_data["current_price"],
                    "currency": price_data["currency"],
                    "change_percent": price_data["change_percent"],
                    "trend": trend_data["trend"],
                    "strength": trend_data["strength"],
                    "percentile_52w": trend_data["percentile_52w"],
                    "score": round(score, 1),
                    "impact": impact,
                }

                result["commodities"].append(commodity_result)
                scores.append(score)
                sentiments.append(impact)

                logger.debug(
                    f"  [{commodity}] {price_data['symbol']} → "
                    f"${price_data['current_price']} {trend_data['trend']} (score={score:.1f})"
                )

            except Exception as e:
                logger.warning(f"  Error analyzing {commodity}: {e}")
                continue

        # Calculate overall score
        if scores:
            overall_score = sum(scores) / len(scores)
            result["overall_score"] = round(overall_score, 1)

            # Determine overall sentiment
            positive_count = sentiments.count("positive")
            negative_count = sentiments.count("negative")

            if positive_count > negative_count:
                result["sentiment"] = "POSITIVE"
            elif negative_count > positive_count:
                result["sentiment"] = "NEGATIVE"
            else:
                result["sentiment"] = "NEUTRAL"

            # Build rationale
            commodity_names = ", ".join([c["name"] for c in result["commodities"]])
            result["rationale"] = (
                f"{ticker} has {len(result['commodities'])} commodity exposures ({commodity_names}). "
                f"Overall score: {result['overall_score']}/10, sentiment: {result['sentiment']}. "
            )

            if result["sentiment"] == "POSITIVE":
                bullish_commodities = [c["name"] for c in result["commodities"] if c["impact"] == "positive"]
                if bullish_commodities:
                    result["rationale"] += f"Strong tailwinds from {', '.join(bullish_commodities)}."
            elif result["sentiment"] == "NEGATIVE":
                bearish_commodities = [c["name"] for c in result["commodities"] if c["impact"] == "negative"]
                if bearish_commodities:
                    result["rationale"] += f"Headwinds from {', '.join(bearish_commodities)}."

        logger.debug(f"[COMMODITY] {ticker} final score: {result['overall_score']}/10 ({result['sentiment']})")

    except Exception as e:
        logger.error(f"[COMMODITY] Error analyzing {ticker} from cache: {e}")
        result["error"] = str(e)

    return result
    """Analisa commodity exposure untuk multiple tickers."""
    results = {}
    for ticker in tickers:
        results[ticker] = analyze(ticker)
    return results


def get_commodity_market_overview() -> dict:
    """Dapatkan overview semua komoditi dan dampaknya."""
    overview = {
        "timestamp": "",
        "commodities": {},
        "top_bullish": [],
        "top_bearish": [],
    }

    try:
        all_prices = get_all_commodity_prices()

        for commodity, price_data in all_prices.items():
            trend_data = _analyze_commodity_trend(price_data)

            overview["commodities"][commodity] = {
                "current_price": price_data["current_price"],
                "change_percent": price_data["change_percent"],
                "trend": trend_data["trend"],
                "related_tickers": price_data["related_tickers"],
            }

            # Track bullish/bearish
            if trend_data["trend"] == "BULLISH":
                overview["top_bullish"].append({
                    "commodity": commodity,
                    "change": price_data["change_percent"],
                })
            elif trend_data["trend"] == "BEARISH":
                overview["top_bearish"].append({
                    "commodity": commodity,
                    "change": price_data["change_percent"],
                })

        # Sort by change magnitude
        overview["top_bullish"].sort(key=lambda x: x["change"], reverse=True)
        overview["top_bearish"].sort(key=lambda x: x["change"])

    except Exception as e:
        logger.error(f"Error getting commodity market overview: {e}")
        overview["error"] = str(e)

    return overview
