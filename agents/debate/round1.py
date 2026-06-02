"""Round 1 — parallel initial arguments per agent."""
from __future__ import annotations

import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from agents.debate.fallback import synthetic_turn_from_scores
from agents.debate.logging_utils import log_debate_turn
from agents.debate.personas import round1_user_prompt, system_prompt
from agents.debate.schemas import normalize_turn, turn_to_log_entry
from agents.llm_client import invoke_json_for_agent

logger = logging.getLogger(__name__)


def _present_one(
    ticker: str,
    agent: str,
    analysis: dict,
    macro_data: dict,
) -> dict | None:
    if agent == "macro":
        analysis_payload = macro_data
    else:
        analysis_payload = analysis

    raw = invoke_json_for_agent(
        agent,
        1,
        system_prompt(agent, round_num=1),
        round1_user_prompt(ticker, agent, analysis_payload, macro_data),
        ticker=ticker if agent != "macro" else "MARKET",
    )
    turn = normalize_turn(
        raw,
        round_num=1,
        ticker=ticker if agent != "macro" else "MARKET",
        agent=agent,
        analysis=analysis_payload if isinstance(analysis_payload, dict) else {},
    )
    if turn:
        entry = turn_to_log_entry(turn)
        log_debate_turn(entry, source=f"llm-r1/{agent}")
        return entry

    entry = synthetic_turn_from_scores(
        ticker if agent != "macro" else "MARKET",
        agent,
        analysis_payload,
        round_num=1,
    )
    if entry:
        log_debate_turn(entry, source=f"fallback-r1/{agent}")
    else:
        logger.warning("[DEBATE R1] %s %s: LLM and fallback failed", ticker, agent)
    return entry


def present_all(
    ticker: str,
    scores: dict[str, dict],
    macro_data: dict,
) -> list[dict]:
    ticker_scores = scores.get(ticker, {})

    def run_agent(agent: str) -> tuple[str, dict | None]:
        if agent == "fundamental":
            analysis = ticker_scores.get("fundamental", {})
        elif agent == "technical":
            analysis = ticker_scores.get("technical", {})
        elif agent == "bandarmologi":
            analysis = ticker_scores.get("bandarm", {})
        else:
            return agent, None
        entry = _present_one(ticker, agent, analysis, macro_data)
        return agent, entry

    entries: list[dict] = []
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {
            executor.submit(run_agent, a): a
            for a in ("fundamental", "technical", "bandarmologi")
        }
        for future in as_completed(futures):
            agent, entry = future.result()
            if entry:
                entries.append(entry)

    return entries


def present_macro_global(macro_data: dict) -> dict | None:
    raw = invoke_json_for_agent(
        "macro",
        1,
        system_prompt("macro", round_num=1),
        (
            "Berikan outlook makro pasar Indonesia hari ini untuk stock picking IDX.\n"
            "Output: satu objek JSON saja.\n\n"
            f"DATA:\n{json.dumps(macro_data, ensure_ascii=False, default=str)}"
        ),
        ticker="MARKET",
    )
    turn = normalize_turn(
        raw,
        round_num=1,
        ticker="MARKET",
        agent="macro",
        analysis=macro_data,
    )
    if turn:
        entry = turn_to_log_entry(turn)
        log_debate_turn(entry, source="llm-r1/macro")
        return entry

    entry = synthetic_turn_from_scores("MARKET", "macro", macro_data, round_num=1)
    if entry:
        log_debate_turn(entry, source="fallback-r1/macro")
    return entry
