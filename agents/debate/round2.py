"""Round 2 — cross-examination."""
from __future__ import annotations

import logging

from agents.debate.fallback import synthetic_turn_from_scores
from agents.debate.logging_utils import log_debate_turn
from agents.debate.personas import round2_user_prompt, system_prompt
from agents.debate.schemas import normalize_turn, turn_to_log_entry, vote_to_weight_delta
from agents.llm_client import invoke_json_for_agent

logger = logging.getLogger(__name__)

ROUND2_AGENTS = ("bandarmologi", "technical", "fundamental")


def _analysis_for_agent(ticker_scores: dict, agent: str) -> dict:
    key_map = {
        "bandarmologi": "bandarm",
        "technical": "technical",
        "fundamental": "fundamental",
    }
    return ticker_scores.get(key_map.get(agent, ""), {})


def cross_examine(
    ticker: str,
    scores: dict,
    round1_entries: list[dict],
) -> tuple[list[dict], float]:
    ticker_scores = scores.get(ticker, {})
    round1_for_ticker = [e for e in round1_entries if e.get("ticker") == ticker]
    entries: list[dict] = []
    net_delta = 0.0

    bandarm = ticker_scores.get("bandarm", {})
    tech = ticker_scores.get("technical", {})
    bandarm_score = bandarm.get("score", 5)
    tech_score = tech.get("score", 5)

    for agent in ROUND2_AGENTS:
        analysis = _analysis_for_agent(ticker_scores, agent)
        raw = invoke_json_for_agent(
            agent,
            2,
            system_prompt(agent, round_num=2),
            round2_user_prompt(ticker, agent, analysis, round1_for_ticker),
            ticker=ticker,
        )
        turn = normalize_turn(
            raw,
            round_num=2,
            ticker=ticker,
            agent=agent,
            analysis=analysis,
        )
        if turn:
            entry = turn_to_log_entry(turn)
            entries.append(entry)
            log_debate_turn(entry, source=f"llm-r2/{agent}")
            net_delta += vote_to_weight_delta(turn["vote"], agent)
        else:
            entry = synthetic_turn_from_scores(
                ticker, agent, analysis, round_num=2
            )
            if entry:
                entries.append(entry)
                log_debate_turn(entry, source=f"fallback-r2/{agent}")
                net_delta += vote_to_weight_delta(entry["vote"], agent)
            else:
                logger.warning("[DEBATE R2] %s %s: LLM and fallback failed", ticker, agent)

    if bandarm_score >= 7 and tech_score <= 5:
        net_delta += 0.10
    elif bandarm_score <= 4 and tech_score >= 7:
        net_delta -= 0.15

    bd_7 = bandarm.get("window_7d", {}).get("net_value", 0)
    if isinstance(bd_7, (int, float)) and bd_7 > 0 and bandarm_score >= 6:
        net_delta += 0.05

    return entries, net_delta
