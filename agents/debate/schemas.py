"""Debate turn schemas and validation."""
from __future__ import annotations

import logging
from typing import Any, TypedDict

logger = logging.getLogger(__name__)

VALID_VOTES = frozenset({"BUY", "HOLD", "SELL"})


class DebateTurn(TypedDict, total=False):
    round: int
    ticker: str
    agent: str
    argument: str
    vote: str
    confidence: str
    cites: list[str]


def normalize_turn(
    raw: dict[str, Any] | None,
    *,
    round_num: int,
    ticker: str,
    agent: str,
    analysis: dict,
) -> DebateTurn | None:
    if not raw:
        return None
    vote = str(raw.get("vote", "HOLD")).upper()
    if vote not in VALID_VOTES:
        vote = "HOLD"
    argument = str(raw.get("argument", "")).strip()
    if not argument:
        return None
    cites = raw.get("cites") or []
    if not isinstance(cites, list):
        cites = []
    data_used = _collect_data_used(analysis)
    cites = [c for c in cites if isinstance(c, str) and c in data_used][:5]
    if not cites and data_used:
        logger.debug("No valid cites for %s/%s; argument kept", ticker, agent)
    return {
        "round": round_num,
        "ticker": ticker,
        "agent": agent,
        "argument": argument,
        "vote": vote,
        "confidence": str(raw.get("confidence", "MEDIUM")),
        "cites": cites,
    }


def turn_to_log_entry(turn: DebateTurn) -> dict:
    """Strip extra fields for DB / debate_log."""
    return {
        "round": turn["round"],
        "ticker": turn["ticker"],
        "agent": turn["agent"],
        "argument": turn["argument"],
        "vote": turn["vote"],
    }


def _collect_data_used(analysis: dict) -> set[str]:
    used = analysis.get("data_used") or []
    if isinstance(used, list):
        return {str(x) for x in used}
    return set()


def vote_to_weight_delta(vote: str, agent: str) -> float:
    """Weighted vote contribution for synthesis."""
    weights = {
        "bandarmologi": 0.40,
        "technical": 0.25,
        "fundamental": 0.20,
        "macro": 0.15,
    }
    w = weights.get(agent, 0.10)
    if vote == "BUY":
        return w
    if vote == "SELL":
        return -w
    return 0.0
