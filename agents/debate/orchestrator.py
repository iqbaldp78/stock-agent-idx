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

logger = logging.getLogger(__name__)


def run_llm_debate(state: dict) -> dict:
    """
    Multi-agent LLM debate: Round 1 parallel → Round 2 cross-exam → synthesis.
    """
    scores = state.get("scores", {})
    composites = state.get("composites", {})
    macro_data = state.get("macro_data", {})

    if not composites:
        return {"debate_log": [], "finalists": []}

    sorted_tickers = sorted(
        composites.items(),
        key=lambda x: x[1]["composite_score"],
        reverse=True,
    )
    debate_candidates = sorted_tickers[: min(LLM_DEBATE_MAX_TICKERS, len(sorted_tickers))]
    debate_log: list[dict] = []

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
