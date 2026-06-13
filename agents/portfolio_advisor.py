"""
AI Portfolio Advisor Agent
All-in-one portfolio analysis: rebalancing, DCA priority, risk analysis, performance attribution.
"""
import logging
import json
from datetime import datetime
from typing import Optional

from agents.llm_client import get_chat_model
from config import LLM_MODEL_AGENT

logger = logging.getLogger(__name__)


def analyze_portfolio(
    holdings: list[dict],
    active_strategies: list[dict],
    top_picks: list[dict],
    monthly_budget: float,
    transactions: list[dict],
) -> dict:
    """
    AI Portfolio analysis menggunakan LLM.

    Returns structured JSON dengan rebalancing, DCA priority, risk analysis, performance attribution.
    """

    # Build context
    context = _build_portfolio_context(holdings, active_strategies, top_picks, monthly_budget, transactions)

    # System prompt
    system_prompt = """You are an experienced Portfolio Manager for Indonesian stock market (IDX/LQ45) specializing in long-term investing with DCA (Dollar Cost Averaging) strategy.

Your task is to analyze the portfolio and provide actionable recommendations in JSON format.

Output JSON schema:
{
    "summary": "Executive summary in 2-3 sentences",
    "rebalancing": {
        "needed": true/false,
        "overweight": ["TICKER1", "TICKER2"],
        "underweight": ["TICKER3"],
        "actions": [
            {"ticker": "TICKER", "action": "REDUCE/INCREASE/HOLD", "reason": "..."}
        ]
    },
    "dca_priority": [
        {
            "rank": 1,
            "ticker": "TICKER",
            "allocation": 800000,
            "timing_status": "IDEAL/ACCEPTABLE/CAUTION",
            "conviction": "HIGH/MEDIUM/LOW",
            "reasoning": "Why this ticker is priority..."
        }
    ],
    "risk_analysis": {
        "sector_concentration": {"banking": 40, "mining": 30, "consumer": 20, "other": 10},
        "risk_level": "LOW/MEDIUM/HIGH",
        "diversification_score": 7.5,
        "recommendations": ["Add consumer sector exposure", "Reduce banking concentration"]
    },
    "performance_attribution": {
        "best_performer": {"ticker": "TICKER", "return_pct": 15.2, "reason": "..."},
        "worst_performer": {"ticker": "TICKER", "return_pct": -3.5, "reason": "..."},
        "signal_quality": "X/Y signals were profitable"
    }
}

Important:
- Be specific with numbers (allocation amounts, prices, percentages)
- Focus on actionable insights
- Consider timing (true cost bandar) when ranking DCA priority
- Allocate monthly budget across top 3 priorities only
- Risk level based on sector concentration + P&L volatility
- Diversification score 1-10 (higher = better)
"""

    user_prompt = f"""CURRENT PORTFOLIO:
{context['portfolio_summary']}

HOLDINGS DETAIL:
{context['holdings_detail']}

ACTIVE DCA STRATEGIES:
{context['dca_strategies']}

LATEST TOP PICKS (Investment Opportunities):
{context['top_picks_detail']}

MONTHLY DCA BUDGET: Rp {monthly_budget:,.0f}

HISTORICAL PERFORMANCE:
{context['performance_summary']}

Please provide comprehensive portfolio analysis covering:
1. Rebalancing: Is portfolio balanced? Which holdings overweight/underweight? Recommend actions.
2. DCA Priority: From TOP PICKS + current holdings, rank top 3 tickers to buy this month. Allocate the monthly budget. Consider timing, conviction, and balance.
3. Risk Analysis: Sector concentration, diversification score, risk level, recommendations.
4. Performance Attribution: Best/worst performers, signal quality, lessons learned.

Output strictly in JSON format matching the schema provided.
"""

    try:
        llm = get_chat_model(LLM_MODEL_AGENT, temperature=0.3, json_mode=True)

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        response = llm.invoke(messages)
        content = response.content.strip()

        # Parse JSON
        result = json.loads(content)
        result["generated_at"] = datetime.now().isoformat()

        logger.info(f"[Portfolio AI] Analysis completed: {result.get('summary', '')[:100]}")
        return result

    except json.JSONDecodeError as e:
        logger.error(f"[Portfolio AI] JSON parse error: {e}")
        return _error_response(f"Failed to parse AI response: {e}")
    except Exception as e:
        logger.error(f"[Portfolio AI] Error: {e}")
        return _error_response(str(e))


def _build_portfolio_context(
    holdings: list[dict],
    active_strategies: list[dict],
    top_picks: list[dict],
    monthly_budget: float,
    transactions: list[dict],
) -> dict:
    """Build structured context string dari data portfolio."""

    # Portfolio summary
    total_invested = sum(h.get('total_invested', 0) for h in holdings)
    total_current = sum(h.get('current_value', 0) or 0 for h in holdings)
    total_pnl = total_current - total_invested if total_current > 0 else 0
    total_pnl_pct = (total_pnl / total_invested * 100) if total_invested > 0 else 0

    portfolio_summary = f"""Total Holdings: {len(holdings)}
Total Invested: Rp {total_invested:,.0f}
Current Value: Rp {total_current:,.0f}
Unrealized P&L: Rp {total_pnl:+,.0f} ({total_pnl_pct:+.2f}%)
"""

    # Holdings detail
    holdings_lines = []
    for h in holdings:
        ticker = h['ticker']
        lots = h.get('total_lots', 0)
        avg = h.get('avg_cost', 0)
        curr = h.get('current_price')
        pnl_pct = h.get('unrealized_pnl_pct')
        invested = h.get('total_invested', 0)
        weight = (invested / total_invested * 100) if total_invested > 0 else 0

        line = f"- {ticker}: {lots} lot @ Rp {avg:,.0f}"
        if curr:
            line += f" → Current: Rp {curr:,.0f}"
        if pnl_pct is not None:
            line += f" | P&L: {pnl_pct:+.2f}%"
        line += f" | Weight: {weight:.1f}%"
        holdings_lines.append(line)

    holdings_detail = "\n".join(holdings_lines) if holdings_lines else "No holdings yet."

    # DCA strategies
    dca_lines = []
    for s in active_strategies:
        ticker = s['ticker']
        budget = s.get('total_budget', 0)
        used = s.get('used_budget', 0)
        remaining = s.get('remaining_budget', 0)
        next_buy = s.get('next_buy_price')

        line = f"- {ticker}: Budget Rp {budget:,.0f}, Used Rp {used:,.0f}, Remaining Rp {remaining:,.0f}"
        if next_buy:
            line += f", Next Buy @ Rp {next_buy:,.0f}"
        dca_lines.append(line)

    dca_strategies = "\n".join(dca_lines) if dca_lines else "No active DCA strategies."

    # TOP PICKS
    picks_lines = []
    for p in top_picks[:5]:  # Top 5 only
        ticker = p.get('ticker')
        entry_low = p.get('entry_low')
        max_entry = p.get('max_entry')
        conviction = p.get('conviction', 'N/A')
        thesis = p.get('thesis', '')[:100]
        bandar_1m = p.get('bandar_avg_1m')

        line = f"- {ticker}: Entry {entry_low}-{max_entry}, Conviction: {conviction}"
        if bandar_1m:
            line += f", True Cost Bandar 1M: Rp {bandar_1m:,.0f}"
        if thesis:
            line += f"\n  Thesis: {thesis}..."
        picks_lines.append(line)

    top_picks_detail = "\n".join(picks_lines) if picks_lines else "No TOP PICKS available."

    # Performance summary
    buy_txns = [t for t in transactions if t.get('transaction_type') == 'BUY']
    sell_txns = [t for t in transactions if t.get('transaction_type') == 'SELL']

    performance_summary = f"""Total Transactions: {len(transactions)}
- BUY: {len(buy_txns)}
- SELL: {len(sell_txns)}

Recent activity (last 30 days): {len([t for t in transactions if _is_recent(t.get('transaction_date'))])} transactions
"""

    return {
        "portfolio_summary": portfolio_summary,
        "holdings_detail": holdings_detail,
        "dca_strategies": dca_strategies,
        "top_picks_detail": top_picks_detail,
        "performance_summary": performance_summary,
    }


def _is_recent(date_str: Optional[str], days: int = 30) -> bool:
    """Check if date is within last N days."""
    if not date_str:
        return False
    try:
        from datetime import date, timedelta
        txn_date = datetime.strptime(str(date_str), "%Y-%m-%d").date()
        return (date.today() - txn_date).days <= days
    except Exception:
        return False


def _error_response(error_msg: str) -> dict:
    """Return error response in expected schema."""
    return {
        "summary": f"Analysis failed: {error_msg}",
        "rebalancing": {
            "needed": False,
            "overweight": [],
            "underweight": [],
            "actions": [],
        },
        "dca_priority": [],
        "risk_analysis": {
            "sector_concentration": {},
            "risk_level": "UNKNOWN",
            "diversification_score": 0,
            "recommendations": [f"Error: {error_msg}"],
        },
        "performance_attribution": {
            "best_performer": None,
            "worst_performer": None,
            "signal_quality": "N/A",
        },
        "generated_at": datetime.now().isoformat(),
        "error": error_msg,
    }
