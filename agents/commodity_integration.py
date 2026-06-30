"""
Commodity Integration Helper — Tambahkan commodity data ke workflow.
Dipanggil dalam Phase 2 (Scoring) atau Phase 2.5 (Macro).
"""
import logging
from agents.commodity_analyst import analyze as analyze_commodity, get_commodity_market_overview
from data.commodity_mapper import get_commodities_for_ticker

logger = logging.getLogger(__name__)


def enrich_ticker_with_commodities(ticker: str, scores: dict) -> dict:
    """
    Tambahkan commodity analysis ke scores[ticker].
    Dipanggil saat scoring untuk individual ticker.

    Returns:
        {
            "score": ...,
            "commodities": {...},  # dari commodity analyzer
            "commodity_impact": "positive" | "negative" | "neutral"
        }
    """
    try:
        commodity_analysis = analyze_commodity(ticker)

        if commodity_analysis.get("error"):
            return {
                "commodity_score": 5,  # neutral default
                "commodities": [],
                "commodity_impact": "neutral",
                "error": commodity_analysis["error"],
            }

        # Map sentiment ke score contribution
        sentiment_to_score = {
            "POSITIVE": 7,
            "NEUTRAL": 5,
            "NEGATIVE": 3,
        }

        commodity_score = sentiment_to_score.get(
            commodity_analysis.get("sentiment", "NEUTRAL"), 5
        )

        return {
            "commodity_score": commodity_score,
            "commodity_analysis": commodity_analysis,
            "commodities": commodity_analysis.get("commodities", []),
            "commodity_impact": commodity_analysis.get("sentiment", "NEUTRAL").lower(),
            "overall_commodity_score": commodity_analysis.get("overall_score", 0),
        }

    except Exception as e:
        logger.error(f"Error enriching {ticker} with commodities: {e}")
        return {
            "commodity_score": 5,
            "commodities": [],
            "commodity_impact": "neutral",
            "error": str(e),
        }


def add_commodity_context_to_macro(macro_data: dict) -> dict:
    """
    Tambahkan commodity market overview ke macro_data.
    Dipanggil dalam Phase 2 (Macro analysis).

    macro_data akan enriched dengan:
        - commodity_overview: market state semua komoditi
        - bullish_commodities: komoditi dengan trend bullish
        - bearish_commodities: komoditi dengan trend bearish
    """
    try:
        logger.info("[MACRO] Fetching commodity market overview")

        overview = get_commodity_market_overview()

        macro_data["commodity_overview"] = overview.get("commodities", {})
        macro_data["bullish_commodities"] = overview.get("top_bullish", [])
        macro_data["bearish_commodities"] = overview.get("top_bearish", [])

        # Log summary
        bullish_count = len(macro_data["bullish_commodities"])
        bearish_count = len(macro_data["bearish_commodities"])

        logger.info(
            f"[MACRO] Commodity outlook: "
            f"{bullish_count} bullish, {bearish_count} bearish"
        )

        if macro_data["bullish_commodities"]:
            bullish_names = ", ".join(
                [c["commodity"] for c in macro_data["bullish_commodities"]]
            )
            logger.info(f"  Bullish: {bullish_names}")

        if macro_data["bearish_commodities"]:
            bearish_names = ", ".join(
                [c["commodity"] for c in macro_data["bearish_commodities"]]
            )
            logger.info(f"  Bearish: {bearish_names}")

    except Exception as e:
        logger.warning(f"[MACRO] Failed to fetch commodity data: {e}")
        macro_data["commodity_overview"] = {}
        macro_data["bullish_commodities"] = []
        macro_data["bearish_commodities"] = []

    return macro_data


def get_commodity_rationale_for_scoring(ticker: str, composite_score: float) -> str:
    """
    Generate rationale text untuk composite score berdasarkan commodity exposure.
    Bisa ditambah ke scoring report.
    """
    try:
        commodity_analysis = analyze_commodity(ticker)

        if commodity_analysis.get("error") or not commodity_analysis.get("commodities"):
            return ""

        rationale = commodity_analysis.get("rationale", "")

        # Add impact on composite score
        sentiment = commodity_analysis.get("sentiment", "NEUTRAL")
        if sentiment == "POSITIVE":
            rationale += f" This provides upside support to the composite score."
        elif sentiment == "NEGATIVE":
            rationale += f" This creates downside pressure on the composite score."

        return rationale

    except Exception as e:
        logger.warning(f"Error generating commodity rationale for {ticker}: {e}")
        return ""


def format_commodity_summary_for_report(tickers_with_commodities: dict) -> str:
    """
    Format commodity exposure summary untuk final report.

    Args:
        tickers_with_commodities: {
            "ANTM": {"commodities": [...], "sentiment": "POSITIVE"},
            "PTBA": {"commodities": [...], "sentiment": "NEGATIVE"},
            ...
        }

    Returns:
        Formatted text summary
    """
    if not tickers_with_commodities:
        return ""

    lines = [
        "## Commodity Exposure Analysis",
        "",
    ]

    # Group by sentiment
    positive = [
        (t, d) for t, d in tickers_with_commodities.items()
        if d.get("sentiment") == "POSITIVE"
    ]
    negative = [
        (t, d) for t, d in tickers_with_commodities.items()
        if d.get("sentiment") == "NEGATIVE"
    ]
    neutral = [
        (t, d) for t, d in tickers_with_commodities.items()
        if d.get("sentiment") == "NEUTRAL"
    ]

    if positive:
        lines.append("### Bullish Commodity Exposure 📈")
        for ticker, data in positive:
            commodities = ", ".join([c["name"] for c in data.get("commodities", [])])
            lines.append(f"- **{ticker}**: {commodities}")
        lines.append("")

    if negative:
        lines.append("### Bearish Commodity Exposure 📉")
        for ticker, data in negative:
            commodities = ", ".join([c["name"] for c in data.get("commodities", [])])
            lines.append(f"- **{ticker}**: {commodities}")
        lines.append("")

    if neutral:
        lines.append("### Neutral Commodity Exposure ⚖️")
        for ticker, data in neutral:
            commodities = ", ".join([c["name"] for c in data.get("commodities", [])])
            lines.append(f"- **{ticker}**: {commodities}")
        lines.append("")

    return "\n".join(lines)
