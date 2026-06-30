"""
Commodity-Enhanced Composite Scoring (Optional)
================================================

Add commodity exposure factor to composite score calculation.
Usage: Optional - use only if you want commodity prices to influence final scores.

How to use:
-----------
from graph.scoring_commodity import calculate_composite_with_commodity

result = calculate_composite_with_commodity(
    scores={"bandarm": 8, "technical": 7, ...},
    ticker="ANTM",
    market_cap=60_000_000_000_000,
    is_volatile=False,
    macro_data=macro_data,
    commodity_score=7.5  # From commodity_analyst.analyze()
)
"""
from graph.scoring import (
    get_weights,
    detect_mode,
)


def _calculate_commodity_adjustment(
    commodity_score: float,
    ticker: str,
    sector: str,
) -> tuple[float, str]:
    """
    Calculate adjustment to composite score based on commodity exposure.

    Args:
        commodity_score: 0-10 score from commodity_analyst.analyze()
        ticker: Stock ticker
        sector: Industry sector

    Returns:
        (adjustment_value, narrative_text)

    Adjustment logic:
    - Commodity-sensitive sectors: higher weight (±0.5 to ±1.0)
    - Other sectors: lower weight (±0.2 to ±0.3)
    """
    if not commodity_score or commodity_score == 5:
        return (0.0, "")

    # Sectors highly exposed to commodities
    commodity_sensitive = [
        "Energy", "Basic Materials", "Utilities"
    ]

    # Calculate adjustment magnitude
    score_delta = commodity_score - 5.0  # 5 is neutral
    is_sensitive = sector in commodity_sensitive

    if is_sensitive:
        # High sensitivity: ±1.0 per point from neutral
        adjustment = score_delta * 0.1  # 0.1 = 10% of max score swing
        adjustment = max(-1.0, min(1.0, adjustment))

        if score_delta > 0:
            narrative = (
                f"Commodity tailwind boost (+{abs(score_delta):.1f} pts, "
                f"adjustment: +{adjustment:.2f})"
            )
        else:
            narrative = (
                f"Commodity headwind (-{abs(score_delta):.1f} pts, "
                f"adjustment: {adjustment:.2f})"
            )
    else:
        # Lower sensitivity: ±0.5 per point from neutral
        adjustment = score_delta * 0.05  # 5% of max score swing
        adjustment = max(-0.5, min(0.5, adjustment))

        if score_delta > 0:
            narrative = (
                f"Mild commodity support (+{abs(score_delta):.1f} pts, "
                f"adjustment: +{adjustment:.2f})"
            )
        else:
            narrative = (
                f"Mild commodity pressure (-{abs(score_delta):.1f} pts, "
                f"adjustment: {adjustment:.2f})"
            )

    return (adjustment, narrative)


def calculate_composite_with_commodity(
    scores: dict,
    ticker: str,
    market_cap: float,
    is_volatile: bool,
    macro_data: dict = None,
    commodity_score: float = None,
) -> dict:
    """
    Enhanced composite score calculation including commodity factor.

    Args:
        scores: Agent scores dict {"bandarm", "technical", "fundamental", "macro", "news"}
        ticker: Stock ticker
        market_cap: Market capitalization
        is_volatile: Is market volatile
        macro_data: Macro context
        commodity_score: Optional commodity exposure score (0-10)

    Returns:
        Enhanced composite result with commodity breakdown
    """
    from graph.scoring import calculate_composite

    # Get base composite score
    result = calculate_composite(scores, ticker, market_cap, is_volatile, macro_data)

    # Add commodity factor if provided
    if commodity_score is not None and commodity_score != 5:
        sector = result.get("sector", "Unknown")

        commodity_adj, commodity_narrative = _calculate_commodity_adjustment(
            commodity_score, ticker, sector
        )

        # Apply adjustment
        result["commodity_score"] = commodity_score
        result["commodity_adjustment"] = round(commodity_adj, 2)
        result["commodity_narrative"] = commodity_narrative

        # Update composite score
        old_composite = result["composite_score"]
        result["composite_score"] = round(old_composite + commodity_adj, 2)
        result["composite_score_before_commodity"] = old_composite

        # Add to breakdown
        result["breakdown"]["commodity"] = {
            "score": commodity_score,
            "weight": 0.05,  # 5% of total score
            "contribution": round(commodity_score * 0.05, 2),
        }

    return result


# Integration example (for reference)
INTEGRATION_EXAMPLE = """
# In workflow.py, modify run_parallel_scoring:

from graph.scoring_commodity import calculate_composite_with_commodity
from agents.commodity_analyst import analyze as analyze_commodity

for ticker in candidates:
    # ... existing code ...

    # Calculate commodity score
    commodity_analysis = analyze_commodity(ticker)
    commodity_score = commodity_analysis.get("overall_score")

    # Use commodity-enhanced scoring
    if commodity_score:
        composite = calculate_composite_with_commodity(
            agent_scores,
            ticker,
            market_cap,
            is_volatile,
            macro_data,
            commodity_score=commodity_score
        )
    else:
        # Fallback to standard composite
        composite = calculate_composite(
            agent_scores,
            ticker,
            market_cap,
            is_volatile,
            macro_data
        )

    composites[ticker] = composite
"""
