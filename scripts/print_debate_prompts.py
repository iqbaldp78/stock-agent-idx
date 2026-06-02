#!/usr/bin/env python3
"""Print system + user prompts sent to LLM for each debate agent."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import get_model_for_agent, LLM_MODEL_INVESTMENT_MANAGER
from agents.debate.personas import (
    IM_SYSTEM_PROMPT,
    round1_user_prompt,
    round2_user_prompt,
    system_prompt,
)

TICKER = "BBCA"
MOCK_FUND = {
    "score": 8.5,
    "per": 18,
    "roe": 0.22,
    "key_points": ["ROE 22%", "PER wajar"],
    "risks": ["valuasi premium"],
    "data_used": ["ROE: 22%", "PER: 18x"],
}
MOCK_TECH = {
    "score": 7.0,
    "setup": "Breakout resistance, volume konfirmasi",
    "entry_zone": "9400-9500",
    "data_used": ["RSI: 58", "MA20: 9350"],
}
MOCK_BANDARM = {
    "score": 8.0,
    "signal": "STRONG_ACCUMULATION",
    "data_used": ["Stockbit broker summary 7H & 1M"],
}
MOCK_MACRO = {
    "score": 7,
    "ihsg_trend": "BULLISH",
    "ihsg_price": 7200,
    "data_used": ["IHSG di atas MA20", "foreign net buy"],
}
R1_SAMPLE = [
    {
        "round": 1,
        "ticker": TICKER,
        "agent": "technical",
        "argument": "BBCA breakout resistance dengan volume naik.",
        "vote": "BUY",
    },
    {
        "round": 1,
        "ticker": TICKER,
        "agent": "fundamental",
        "argument": "ROE 22% solid, PER masih wajar.",
        "vote": "BUY",
    },
]


def _print_block(title: str, system: str, user: str) -> None:
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)
    print("\n>>> SYSTEM MESSAGE <<<\n")
    print(system)
    print("\n>>> USER MESSAGE <<<\n")
    print(user)
    print(f"\n[System: {len(system)} chars | User: {len(user)} chars]")


def main() -> None:
    analyses = {
        "fundamental": MOCK_FUND,
        "technical": MOCK_TECH,
        "bandarmologi": MOCK_BANDARM,
    }

    print("STOCK AGENT IDX — Contoh prompt debat (ticker=%s)" % TICKER)
    print("Setiap call ke 9Router = [SystemMessage] + [HumanMessage]")

    for agent in ("fundamental", "technical", "bandarmologi"):
        _print_block(
            f"ROUND 1 | {agent.upper()} | model={get_model_for_agent(agent, 1)}",
            system_prompt(agent, round_num=1),
            round1_user_prompt(TICKER, agent, analyses[agent], MOCK_MACRO),
        )

    _print_block(
        f"ROUND 1 | MACRO (global) | model={get_model_for_agent('macro', 1)}",
        system_prompt("macro", round_num=1),
        round1_user_prompt(
            "MARKET",
            "macro",
            {},
            MOCK_MACRO,
        ),
    )

    _print_block(
        f"ROUND 2 | BANDARMOLOGI | model={get_model_for_agent('bandarmologi', 2)}",
        system_prompt("bandarmologi", round_num=2),
        round2_user_prompt(TICKER, "bandarmologi", MOCK_BANDARM, R1_SAMPLE),
    )

    _print_block(
        f"ROUND 2 | TECHNICAL | model={get_model_for_agent('technical', 2)}",
        system_prompt("technical", round_num=2),
        round2_user_prompt(TICKER, "technical", MOCK_TECH, R1_SAMPLE),
    )

    print("\n" + "=" * 78)
    print(f"INVESTMENT MANAGER | model={LLM_MODEL_INVESTMENT_MANAGER}")
    print("=" * 78)
    print("\n>>> SYSTEM MESSAGE <<<\n")
    print(IM_SYSTEM_PROMPT)
    print("\n>>> USER MESSAGE (contoh — dari investment_manager.py) <<<\n")
    print(
        "Pilih TOP 3 dari finalis berikut. Rank 1 = conviction tertinggi.\n\n"
        "{ finalists, scores, composites, debate_log, macro_data }  ← JSON pipeline state"
    )


if __name__ == "__main__":
    main()
