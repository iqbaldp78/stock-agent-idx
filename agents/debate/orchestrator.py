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
from config import LLM_DEBATE_MAX_TICKERS
from data.fetcher_tradingview import get_technical_analysis

logger = logging.getLogger(__name__)


def run_llm_debate(state: dict) -> dict:
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

    log_debate_section(
        f"DEBAT MULTI-AGENT (LLM) — {len(debate_candidates)} ticker"
    )
    logger.info("Kandidat: %s", [t for t, _ in debate_candidates])

    # LAZY FETCH: Fetch TradingView TA only for debate candidates to save API limits
    logger.info("[DEBATE LLM] Lazy-fetching TradingView TA for candidates...")
    for ticker, _ in debate_candidates:
        if ticker in scores and "technical" in scores[ticker]:
            tv_ta = get_technical_analysis(ticker)
            if tv_ta.get("status") == "success":
                scores[ticker]["technical"]["tradingview_ta"] = {
                    "summary": tv_ta.get("summary", {}),
                    "indicators": tv_ta.get("indicators", {})
                }
            else:
                scores[ticker]["technical"]["tradingview_ta"] = {"error": tv_ta.get("message")}


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
