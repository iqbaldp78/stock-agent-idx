"""
Graph — LangGraph Workflow
Orchestrasi full pipeline: Filter → Scoring → Debate → Decision
"""
from __future__ import annotations

from typing import TypedDict
from langgraph.graph import StateGraph, END

from data.filter import apply_filter
from data.fetcher_stockbit import get_stock_info
from agents.fundamental import analyze as fund_analyze
from agents.technical import analyze as tech_analyze
from agents.bandarmologi import analyze as bandarm_analyze
from agents.macro import analyze as macro_analyze
from agents.investment_manager import synthesize as im_synthesize
from agents.debate import run_llm_debate
from agents.debate.logging_utils import log_debate_turn, log_debate_section, log_finalists
from agents.llm_client import health_check
from graph.scoring import calculate_composite
from config import LLM_ENABLED, get_universe

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


def run_debate_rule_based(state: AgentState) -> dict:
    """
    Phase 3 fallback: Rule-based debate — 2 rounds.
    """
    scores = state["scores"]
    composites = state["composites"]
    macro_data = state["macro_data"]

    if not composites:
        return {"debate_log": [], "finalists": []}

    sorted_tickers = sorted(
        composites.items(),
        key=lambda x: x[1]["composite_score"],
        reverse=True,
    )

    debate_candidates = sorted_tickers[:min(15, len(sorted_tickers))]
    debate_log = []

    log_debate_section(f"DEBAT MULTI-AGENT (rule-based) — {len(debate_candidates)} ticker")
    logger.info("[DEBATE] Round 1 — Initial Arguments (rule-based)")
    round1_votes = {}

    def _log(entry: dict) -> None:
        debate_log.append(entry)
        log_debate_turn(entry, source="rule")

    for ticker, composite in debate_candidates:
        ticker_scores = scores.get(ticker, {})
        bandarm = ticker_scores.get("bandarm", {})
        tech = ticker_scores.get("technical", {})
        fund = ticker_scores.get("fundamental", {})

        votes_for = 0
        votes_against = 0

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

        _log({
            "round": 1, "ticker": ticker, "agent": "bandarmologi",
            "argument": argument, "vote": vote,
        })

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

        _log({
            "round": 1, "ticker": ticker, "agent": "technical",
            "argument": argument, "vote": vote,
        })

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

        _log({
            "round": 1, "ticker": ticker, "agent": "fundamental",
            "argument": argument, "vote": vote,
        })

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

        _log({
            "round": 1, "ticker": ticker, "agent": "macro",
            "argument": argument, "vote": vote,
        })

        round1_votes[ticker] = {
            "votes_for": votes_for,
            "votes_against": votes_against,
            "net_vote": votes_for - votes_against,
        }

    logger.info("[DEBATE] Round 2 — Cross-Examination (rule-based)")

    for ticker, composite in debate_candidates:
        ticker_scores = scores.get(ticker, {})
        bandarm = ticker_scores.get("bandarm", {})
        tech = ticker_scores.get("technical", {})

        bandarm_score = bandarm.get("score", 5)
        tech_score = tech.get("score", 5)

        if bandarm_score >= 7 and tech_score <= 5:
            argument = (
                f"Bandarm override: {ticker} bandar akumulasi kuat meski chart belum confirm"
            )
            round1_votes[ticker]["net_vote"] += 0.10
            _log({
                "round": 2, "ticker": ticker, "agent": "bandarmologi",
                "argument": argument, "vote": "BUY",
            })

        elif bandarm_score <= 4 and tech_score >= 7:
            argument = f"Bandarm warning: {ticker} chart oke tapi bandar distribusi — trap potential"
            round1_votes[ticker]["net_vote"] -= 0.15
            _log({
                "round": 2, "ticker": ticker, "agent": "bandarmologi",
                "argument": argument, "vote": "SELL",
            })

        bd_7 = bandarm.get("window_7d", {}).get("net_value", 0)
        if isinstance(bd_7, (int, float)) and bd_7 > 0 and bandarm_score >= 6:
            argument = f"{ticker}: net value positif konfirmasi akumulasi bandar"
            round1_votes[ticker]["net_vote"] += 0.05
            _log({
                "round": 2, "ticker": ticker, "agent": "bandarmologi",
                "argument": argument, "vote": "BUY",
            })

    logger.info("[DEBATE] Synthesis — selecting finalists")

    final_ranking = []
    for ticker, composite in debate_candidates:
        debate_bonus = round1_votes.get(ticker, {}).get("net_vote", 0)
        final_score = composite["composite_score"] + debate_bonus
        final_ranking.append((ticker, final_score, composite))

    final_ranking.sort(key=lambda x: x[1], reverse=True)

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

    log_finalists(finalists)

    return {
        "debate_log": debate_log,
        "finalists": finalists,
    }


def run_debate(state: AgentState) -> dict:
    """
    Phase 3: LLM multi-agent debate via 9Router, with rule-based fallback.
    """
    if LLM_ENABLED and health_check():
        try:
            return run_llm_debate(state)
        except Exception as e:
            logger.warning("LLM debate failed, fallback rule-based: %s", e)
    elif LLM_ENABLED:
        logger.warning("9Router health_check failed, using rule-based debate")
    return run_debate_rule_based(state)


def run_investment_manager(state: AgentState) -> dict:
    """
    Phase 4: Investment Manager — select TOP 3 picks.
    """
    return im_synthesize(state)


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
