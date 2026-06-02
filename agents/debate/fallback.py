"""Rule-based synthetic debate turns when LLM fails."""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

_AGENT_KEY = {
    "fundamental": "fundamental",
    "technical": "technical",
    "bandarmologi": "bandarm",
}


def synthetic_turn_from_scores(
    ticker: str,
    agent: str,
    analysis: dict,
    *,
    round_num: int = 1,
) -> dict | None:
    """Build debate log entry from rule-based analysis dict (score/signal)."""
    score = analysis.get("score", 5)
    if not isinstance(score, (int, float)):
        score = 5

    if agent == "fundamental":
        if score >= 7:
            key_pts = "; ".join((analysis.get("key_points") or [])[:2])
            argument = f"{ticker}: fundamental solid — {key_pts or 'metrik kuat'}"
            vote = "BUY"
        elif score <= 4:
            risks = "; ".join((analysis.get("risks") or [])[:2])
            argument = f"{ticker}: fundamental lemah — {risks or 'risiko tinggi'}"
            vote = "SELL"
        else:
            argument = f"{ticker}: fundamental netral"
            vote = "HOLD"
    elif agent == "technical":
        if score >= 7:
            argument = f"{ticker}: {analysis.get('setup', 'setup bullish')}"
            vote = "BUY"
        elif score <= 4:
            argument = f"{ticker}: chart bearish"
            vote = "SELL"
        else:
            argument = f"{ticker}: chart belum ada trigger"
            vote = "HOLD"
    elif agent == "bandarmologi":
        signal = analysis.get("signal", "")
        if score >= 7 or "ACCUMULATION" in str(signal).upper():
            argument = f"{ticker}: {signal or 'akumulasi bandar'} — sinyal bandar kuat"
            vote = "BUY"
        elif score <= 4 or "DISTRIBUTION" in str(signal).upper():
            argument = f"{ticker}: distribusi bandar terdeteksi"
            vote = "SELL"
        else:
            argument = f"{ticker}: sinyal bandar netral"
            vote = "HOLD"
    elif agent == "macro":
        if score >= 7:
            argument = f"Pasar bullish, mendukung {ticker}"
            vote = "BUY"
        elif score <= 4:
            argument = f"Pasar bearish, risk tinggi untuk {ticker}"
            vote = "SELL"
        else:
            argument = f"Pasar netral untuk {ticker}"
            vote = "HOLD"
    else:
        return None

    if round_num >= 2:
        argument = f"[Fallback R2] {argument}"

    cites = []
    data_used = analysis.get("data_used") or []
    if isinstance(data_used, list):
        cites = [str(x) for x in data_used[:3]]

    logger.info(
        "[DEBATE FALLBACK] %s %s R%d vote=%s (LLM failed)",
        ticker, agent, round_num, vote,
    )
    return {
        "round": round_num,
        "ticker": ticker,
        "agent": agent,
        "argument": argument,
        "vote": vote,
    }
