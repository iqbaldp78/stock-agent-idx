"""LLM debate orchestrator (Phase 3)."""
from __future__ import annotations

import logging

from agents.debate.logging_utils import (
    log_debate_section,
    log_finalists,
    log_synthesis,
    log_ticker_header,
)
from agents.debate.round1 import present_all, present_macro_global
from agents.debate.round2 import cross_examine
from agents.debate.synthesis import compute_round1_votes, select_finalists
from agents.technical import analyze as tech_analyze
from agents.fundamental import analyze as fund_analyze
from graph.scoring import calculate_composite, calculate_konglo_composite
from data.fetcher_stockbit import get_stock_info
from config import LLM_DEBATE_MAX_TICKERS

logger = logging.getLogger(__name__)


def run_llm_debate(state: dict, mode: str = "REGULAR") -> dict:
    """
    Multi-agent LLM debate: Round 1 parallel → Round 2 cross-exam → synthesis.
    Prioritizes STRONG BUY stocks from ML predictions + top composite scores.
    """
    scores = state.get("scores", {})
    composites = state.get("composites", {})
    macro_data = state.get("macro_data", {})
    ml_predictions = state.get("ml_predictions", {})

    if not composites:
        return {"debate_log": [], "finalists": []}

    # Extract STRONG BUY tickers from ml_predictions
    strong_buy_tickers = set()
    for ticker, ml_result in ml_predictions.items():
        if ml_result and ml_result.get("signal") == "STRONG BUY":
            strong_buy_tickers.add(ticker)

    # Sort composites by score
    sorted_tickers = sorted(
        composites.items(),
        key=lambda x: x[1]["composite_score"],
        reverse=True,
    )

    # Build debate candidates: STRONG BUY first, then fill with top composites
    debate_candidates = []
    seen_tickers = set()

    # Priority 1: Add all STRONG BUY tickers
    for ticker in strong_buy_tickers:
        if ticker in composites:
            debate_candidates.append((ticker, composites[ticker]))
            seen_tickers.add(ticker)

    # Priority 2: Fill remaining slots with top composite scores
    for ticker, composite in sorted_tickers:
        if ticker not in seen_tickers:
            debate_candidates.append((ticker, composite))
            seen_tickers.add(ticker)
        if len(debate_candidates) >= min(LLM_DEBATE_MAX_TICKERS, len(composites)):
            break

    debate_log: list[dict] = []

    # Enrich candidates with TradingView TA and Fundamental Data for LLM debate
    logger.info("[DEBATE LLM] Fetching TradingView TA and Fundamental Data for final candidates...")
    is_volatile = macro_data.get("ihsg_condition") == "BEARISH_VOLATILE"
    for ticker, _ in debate_candidates:
        try:
            # 1. Fetch TradingView TA
            scores[ticker]["technical"] = tech_analyze(ticker, use_tradingview=True)
            # 2. Fetch Fundamental Data
            if mode != "KONGLO":
                scores[ticker]["fundamental"] = fund_analyze(ticker)
            else:
                scores[ticker]["fundamental"] = {"score": 5.0, "status": "skipped", "analysis": "Fundamental diabaikan untuk Konglo Play."}
            
            # 3. Recalculate composite score (with fundamental included)
            agent_scores = {
                "bandarm": scores[ticker]["bandarm"]["score"],
                "technical": scores[ticker]["technical"]["score"],
                "fundamental": scores[ticker]["fundamental"]["score"],
                "macro": macro_data.get("score", 5.0),
                "news": scores[ticker]["news"].get("score", 5.0) if scores[ticker].get("news") else 5.0,
            }
            info = get_stock_info(ticker)
            market_cap = info.get("market_cap") or 0
            if mode == "KONGLO":
                composites[ticker] = calculate_konglo_composite(agent_scores, ticker, market_cap, is_volatile, macro_data)
            else:
                composites[ticker] = calculate_composite(agent_scores, ticker, market_cap, is_volatile, macro_data, exclude_fundamental=False)
        except Exception as e:
            logger.warning(f"Failed to enrich {ticker} with TradingView/Fundamental data: {e}")

    log_debate_section(
        f"DEBAT MULTI-AGENT (LLM) — {len(debate_candidates)} ticker"
    )
    logger.info("Kandidat: %s", [t for t, _ in debate_candidates])

    logger.info("[DEBATE LLM] Round 1 — Initial Arguments")
    macro_global = present_macro_global(macro_data)
    if macro_global:
        debate_log.append(macro_global)

    round1_all: list[dict] = []
    for ticker, composite in debate_candidates:
        log_ticker_header(ticker, composite.get("composite_score"))
        entries = present_all(ticker, scores, macro_data)
        round1_all.extend(entries)
        debate_log.extend(entries)

    round1_votes = compute_round1_votes(round1_all)
    for ticker, _ in debate_candidates:
        v = round1_votes.get(ticker, {})
        logger.info(
            "[DEBATE R1 VOTE] %s | for=%.2f against=%.2f net=%+.2f",
            ticker,
            v.get("votes_for", 0),
            v.get("votes_against", 0),
            v.get("net_vote", 0),
        )

    log_debate_section("Round 2 — Cross-Examination")
    round2_deltas: dict[str, float] = {}
    for ticker, composite in debate_candidates:
        log_ticker_header(ticker)
        r1_for_ticker = [e for e in round1_all if e.get("ticker") == ticker]
        r2_entries, delta = cross_examine(ticker, scores, r1_for_ticker)
        debate_log.extend(r2_entries)
        round2_deltas[ticker] = delta
        logger.info("[DEBATE R2 DELTA] %s | bonus=%+.2f", ticker, delta)

    log_debate_section("Synthesis — Ranking Finalis")
    finalists = select_finalists(
        debate_candidates,
        round1_votes,
        round2_deltas,
        ml_predictions,
    )
    for f in finalists:
        t = f["ticker"]
        comp = composites.get(t, {})
        log_synthesis(
            t,
            f.get("composite_score", 0),
            f.get("debate_bonus", 0),
            f.get("final_score", 0),
            net_vote=round1_votes.get(t, {}).get("net_vote"),
        )

    log_finalists(finalists)

    return {"debate_log": debate_log, "finalists": finalists}
