"""
Graph — LangGraph Workflow
Orchestrasi full pipeline: Filter → Scoring → Debate → Decision
"""
from typing import TypedDict
from langgraph.graph import StateGraph, END

from data.filter import apply_filter
from data.fetcher_yfinance import get_stock_info
from agents.fundamental import analyze as fund_analyze
from agents.technical import analyze as tech_analyze
from agents.bandarmologi import analyze as bandarm_analyze
from agents.macro import analyze as macro_analyze
from graph.scoring import calculate_composite
from config import get_universe

import logging

logger = logging.getLogger(__name__)


class AgentState(TypedDict):
    universe: list
    candidates: list
    macro_data: dict
    scores: dict          # {ticker: {agent: result}}
    composites: dict      # {ticker: composite_result}
    debate_log: list
    finalists: list
    top_picks: list
    final_report: dict


# === Node Functions ===

def run_filter(state: AgentState) -> dict:
    """Phase 1: Rule-based filter ~55 → ~30 saham."""
    universe = state.get("universe") or get_universe()
    logger.info(f"[FILTER] Input: {len(universe)} tickers")

    candidates = apply_filter(universe)
    logger.info(f"[FILTER] Output: {len(candidates)} candidates")

    return {"candidates": candidates, "universe": universe}


def run_parallel_scoring(state: AgentState) -> dict:
    """Phase 2: Score semua candidates dengan 4 agent + composite."""
    candidates = state["candidates"]
    logger.info(f"[SCORING] Scoring {len(candidates)} candidates")

    # Macro data (shared for all tickers)
    macro_data = macro_analyze()
    is_volatile = macro_data["is_volatile"]

    scores = {}
    composites = {}

    for ticker in candidates:
        try:
            # Run all agents
            bandarm = bandarm_analyze(ticker)
            tech = tech_analyze(ticker)
            fund = fund_analyze(ticker)

            # Get market cap for weight selection
            info = get_stock_info(ticker)
            market_cap = info.get("market_cap") or 0

            # Store individual scores
            scores[ticker] = {
                "bandarm": bandarm,
                "technical": tech,
                "fundamental": fund,
            }

            # Calculate composite
            agent_scores = {
                "bandarm": bandarm["score"],
                "technical": tech["score"],
                "fundamental": fund["score"],
                "macro": macro_data["score"],
            }
            composite = calculate_composite(agent_scores, ticker, market_cap, is_volatile)
            composites[ticker] = composite

            logger.info(f"  [{ticker}] composite={composite['composite_score']} mode={composite['weight_mode']}")

        except Exception as e:
            logger.warning(f"  [{ticker}] ERROR: {e}")
            continue

    return {
        "scores": scores,
        "composites": composites,
        "macro_data": macro_data,
    }


def run_debate(state: AgentState) -> dict:
    """
    Phase 3: Multi-agent debate — 2 rounds.
    Round 1: Tiap agent present case (arguments for/against)
    Round 2: Cross-examination & weighted vote
    Output: 5-7 finalists
    """
    scores = state["scores"]
    composites = state["composites"]
    macro_data = state["macro_data"]

    if not composites:
        return {"debate_log": [], "finalists": []}

    # Sort by composite score
    sorted_tickers = sorted(
        composites.items(),
        key=lambda x: x[1]["composite_score"],
        reverse=True,
    )

    # Take top 10-15 for debate
    debate_candidates = sorted_tickers[:min(15, len(sorted_tickers))]
    debate_log = []

    # === ROUND 1: Initial Arguments ===
    logger.info("[DEBATE] Round 1 — Initial Arguments")
    round1_votes = {}

    for ticker, composite in debate_candidates:
        ticker_scores = scores.get(ticker, {})
        bandarm = ticker_scores.get("bandarm", {})
        tech = ticker_scores.get("technical", {})
        fund = ticker_scores.get("fundamental", {})

        votes_for = 0
        votes_against = 0

        # Bandarmologi argument (weight 40%)
        bandarm_score = bandarm.get("score", 5)
        if bandarm_score >= 7:
            argument = f"{ticker}: {bandarm.get('signal', 'N/A')} — bandar aktif akumulasi"
            vote = "BUY"
            votes_for += 0.40
        elif bandarm_score <= 4:
            argument = f"{ticker}: distribusi terdeteksi — hindari"
            vote = "SELL"
            votes_against += 0.40
        else:
            argument = f"{ticker}: netral — tidak ada sinyal kuat dari bandar"
            vote = "HOLD"

        debate_log.append({
            "round": 1, "ticker": ticker, "agent": "bandarmologi",
            "argument": argument, "vote": vote,
        })

        # Technical argument (weight 25%)
        tech_score = tech.get("score", 5)
        if tech_score >= 7:
            argument = f"{ticker}: {tech.get('setup', 'setup bullish')}"
            vote = "BUY"
            votes_for += 0.25
        elif tech_score <= 4:
            argument = f"{ticker}: chart bearish, hindari"
            vote = "SELL"
            votes_against += 0.25
        else:
            argument = f"{ticker}: chart netral, belum ada trigger"
            vote = "HOLD"

        debate_log.append({
            "round": 1, "ticker": ticker, "agent": "technical",
            "argument": argument, "vote": vote,
        })

        # Fundamental argument (weight 20%)
        fund_score = fund.get("score", 5)
        if fund_score >= 7:
            key_pts = "; ".join(fund.get("key_points", [])[:2])
            argument = f"{ticker}: fundamental solid — {key_pts}"
            vote = "BUY"
            votes_for += 0.20
        elif fund_score <= 4:
            risks = "; ".join(fund.get("risks", [])[:2])
            argument = f"{ticker}: fundamental lemah — {risks}"
            vote = "SELL"
            votes_against += 0.20
        else:
            argument = f"{ticker}: fundamental cukup, tidak outstanding"
            vote = "HOLD"

        debate_log.append({
            "round": 1, "ticker": ticker, "agent": "fundamental",
            "argument": argument, "vote": vote,
        })

        # Macro argument (weight 15%)
        macro_score = macro_data.get("score", 5)
        if macro_score >= 7:
            argument = f"Pasar bullish, mendukung {ticker}"
            vote = "BUY"
            votes_for += 0.15
        elif macro_score <= 4:
            argument = f"Pasar bearish, risk tinggi untuk {ticker}"
            vote = "SELL"
            votes_against += 0.15
        else:
            argument = f"Pasar netral, {ticker} tergantung micro"
            vote = "HOLD"

        debate_log.append({
            "round": 1, "ticker": ticker, "agent": "macro",
            "argument": argument, "vote": vote,
        })

        round1_votes[ticker] = {
            "votes_for": votes_for,
            "votes_against": votes_against,
            "net_vote": votes_for - votes_against,
        }

    # === ROUND 2: Cross-Examination ===
    logger.info("[DEBATE] Round 2 — Cross-Examination")

    for ticker, composite in debate_candidates:
        ticker_scores = scores.get(ticker, {})
        bandarm = ticker_scores.get("bandarm", {})
        tech = ticker_scores.get("technical", {})

        # Bandarmologi challenges technical if signals diverge
        bandarm_score = bandarm.get("score", 5)
        tech_score = tech.get("score", 5)

        if bandarm_score >= 7 and tech_score <= 5:
            argument = f"Bandarm override: {ticker} bandar akumulasi kuat meski chart belum confirm — early signal"
            vote = "BUY"
            round1_votes[ticker]["net_vote"] += 0.10  # bonus
            debate_log.append({
                "round": 2, "ticker": ticker, "agent": "bandarmologi",
                "argument": argument, "vote": vote,
            })

        elif bandarm_score <= 4 and tech_score >= 7:
            argument = f"Bandarm warning: {ticker} chart oke tapi bandar distribusi — trap potential"
            vote = "SELL"
            round1_votes[ticker]["net_vote"] -= 0.15  # penalty
            debate_log.append({
                "round": 2, "ticker": ticker, "agent": "bandarmologi",
                "argument": argument, "vote": vote,
            })

        # Foreign flow confirmation
        if bandarm.get("window_7d", {}).get("foreign_net_7d", 0) > 0:
            if isinstance(bandarm.get("window_7d", {}).get("foreign_net_7d"), (int, float)):
                foreign_net = bandarm["window_7d"]["foreign_net_7d"]
            else:
                foreign_net = 0

            if foreign_net > 0 and bandarm_score >= 6:
                argument = f"{ticker}: foreign net buy konfirmasi akumulasi bandar"
                round1_votes[ticker]["net_vote"] += 0.05
                debate_log.append({
                    "round": 2, "ticker": ticker, "agent": "bandarmologi",
                    "argument": argument, "vote": "BUY",
                })

    # === SYNTHESIS: Weighted Vote → Finalists ===
    logger.info("[DEBATE] Synthesis — selecting finalists")

    # Combine composite score + debate votes
    final_ranking = []
    for ticker, composite in debate_candidates:
        debate_bonus = round1_votes.get(ticker, {}).get("net_vote", 0)
        final_score = composite["composite_score"] + debate_bonus
        final_ranking.append((ticker, final_score, composite))

    final_ranking.sort(key=lambda x: x[1], reverse=True)

    # Select top 5-7 finalists
    finalists = [
        {
            "ticker": ticker,
            "final_score": round(score, 2),
            "composite_score": comp["composite_score"],
            "weight_mode": comp["weight_mode"],
            "debate_bonus": round(score - comp["composite_score"], 2),
        }
        for ticker, score, comp in final_ranking[:7]
    ]

    logger.info(f"[DEBATE] Finalists: {[f['ticker'] for f in finalists]}")

    return {
        "debate_log": debate_log,
        "finalists": finalists,
    }


def run_investment_manager(state: AgentState) -> dict:
    """
    Phase 4: Investment Manager — select TOP 3 picks.
    Placeholder: selects top 3 from finalists with entry zones.
    Will be enhanced with Claude Sonnet LLM call.
    """
    finalists = state.get("finalists", [])
    scores = state.get("scores", {})
    composites = state.get("composites", {})
    macro_data = state.get("macro_data", {})

    if not finalists:
        return {"top_picks": [], "final_report": {}}

    from datetime import datetime

    top_picks = []
    for i, finalist in enumerate(finalists[:3]):
        ticker = finalist["ticker"]
        ticker_scores = scores.get(ticker, {})
        bandarm = ticker_scores.get("bandarm", {})
        tech = ticker_scores.get("technical", {})
        composite = composites.get(ticker, {})

        # Entry zone from bandarmologi
        price_analysis = bandarm.get("price_analysis", {})
        entry_zone = price_analysis.get("ideal_entry_zone", "N/A")
        max_entry = price_analysis.get("max_entry", "N/A")

        # Target & SL from technical
        target = tech.get("target", "N/A")
        stop_loss = tech.get("stop_loss", "N/A")

        top_picks.append({
            "rank": i + 1,
            "ticker": ticker,
            "composite_score": finalist["composite_score"],
            "final_score": finalist["final_score"],
            "conviction": "HIGH" if finalist["final_score"] >= 7.5 else "MEDIUM" if finalist["final_score"] >= 6 else "LOW",
            "entry_zone": entry_zone,
            "max_entry": max_entry,
            "target_1": target,
            "stop_loss": stop_loss,
            "bandarm_signal": bandarm.get("signal", "N/A"),
            "broker_to_watch": bandarm.get("broker_to_watch", []),
            "weight_mode": finalist["weight_mode"],
        })

    # Market condition
    ihsg_trend = macro_data.get("ihsg_trend", "UNKNOWN")
    market_condition = f"{ihsg_trend} — IHSG {macro_data.get('ihsg_price', 'N/A')}"

    final_report = {
        "generated_at": datetime.now().isoformat(),
        "market_condition": market_condition,
        "top_picks": top_picks,
        "watchlist": [f["ticker"] for f in finalists[3:5]],
        "total_analyzed": len(composites),
        "total_finalists": len(finalists),
    }

    return {
        "top_picks": top_picks,
        "final_report": final_report,
    }


# === Build Workflow ===

def build_workflow() -> StateGraph:
    """Build the LangGraph workflow."""
    workflow = StateGraph(AgentState)

    workflow.add_node("filter", run_filter)
    workflow.add_node("scoring", run_parallel_scoring)
    workflow.add_node("debate", run_debate)
    workflow.add_node("decision", run_investment_manager)

    workflow.set_entry_point("filter")
    workflow.add_edge("filter", "scoring")
    workflow.add_edge("scoring", "debate")
    workflow.add_edge("debate", "decision")
    workflow.add_edge("decision", END)

    return workflow.compile()


def run_full_analysis(universe: list[str] | None = None) -> dict:
    """Run the complete analysis pipeline."""
    app = build_workflow()
    initial_state = {
        "universe": universe or get_universe(),
        "candidates": [],
        "macro_data": {},
        "scores": {},
        "composites": {},
        "debate_log": [],
        "finalists": [],
        "top_picks": [],
        "final_report": {},
    }
    result = app.invoke(initial_state)
    return result
