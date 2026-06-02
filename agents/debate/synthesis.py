"""Synthesis — combine composite scores with debate votes → finalists."""
from __future__ import annotations

from agents.debate.schemas import vote_to_weight_delta


def compute_round1_votes(round1_entries: list[dict]) -> dict[str, dict]:
    """Aggregate weighted votes from Round 1 per ticker."""
    per_ticker: dict[str, dict] = {}

    for entry in round1_entries:
        ticker = entry.get("ticker")
        if not ticker or ticker == "MARKET":
            continue
        agent = entry.get("agent", "")
        vote = entry.get("vote", "HOLD")
        if ticker not in per_ticker:
            per_ticker[ticker] = {"votes_for": 0.0, "votes_against": 0.0, "net_vote": 0.0}
        delta = vote_to_weight_delta(vote, agent)
        if delta > 0:
            per_ticker[ticker]["votes_for"] += delta
        elif delta < 0:
            per_ticker[ticker]["votes_against"] += abs(delta)
        per_ticker[ticker]["net_vote"] += delta

    return per_ticker


def select_finalists(
    debate_candidates: list[tuple[str, dict]],
    round1_votes: dict[str, dict],
    round2_deltas: dict[str, float],
    *,
    max_finalists: int = 7,
) -> list[dict]:
    final_ranking = []
    for ticker, composite in debate_candidates:
        r1 = round1_votes.get(ticker, {})
        debate_bonus = r1.get("net_vote", 0) + round2_deltas.get(ticker, 0)
        final_score = composite["composite_score"] + debate_bonus
        final_ranking.append((ticker, final_score, composite, debate_bonus))

    final_ranking.sort(key=lambda x: x[1], reverse=True)

    return [
        {
            "ticker": ticker,
            "final_score": round(score, 2),
            "composite_score": comp["composite_score"],
            "weight_mode": comp["weight_mode"],
            "debate_bonus": round(bonus, 2),
        }
        for ticker, score, comp, bonus in final_ranking[:max_finalists]
    ]
