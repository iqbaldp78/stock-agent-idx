#!/usr/bin/env python3
"""Smoke test: each debate agent returns valid JSON (not Kiro refusal)."""
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

TICKER = "BBCA"
MOCK_SCORES = {
    TICKER: {
        "fundamental": {
            "score": 8.5,
            "signal": "BUY",
            "key_points": ["ROE 22%", "PER wajar"],
            "risks": ["valuasi premium"],
            "data_used": ["ROE: 22%", "PER: 18x"],
        },
        "technical": {
            "score": 7.0,
            "setup": "Breakout resistance, volume konfirmasi",
            "entry_zone": "9400-9500",
            "data_used": ["RSI: 58", "MA20: 9350"],
        },
        "bandarm": {
            "score": 8.0,
            "signal": "STRONG_ACCUMULATION",
            "data_used": ["Stockbit broker summary 7H & 1M"],
        },
    },
}
MOCK_MACRO = {
    "score": 7,
    "ihsg_trend": "BULLISH",
    "data_used": ["IHSG di atas MA20"],
}


def main():
    from config import get_configured_llm_models, get_model_for_agent
    from agents.llm_client import health_check
    from agents.debate.round1 import present_all, present_macro_global
    from agents.debate.round2 import cross_examine

    print("=== Models ===")
    for k, v in get_configured_llm_models().items():
        if k.startswith("agent_"):
            print(f"  {k}: {v}")
    print("9Router healthy:", health_check())

    print("\n=== Macro global ===")
    macro_entry = present_macro_global(MOCK_MACRO)
    print(macro_entry)

    print(f"\n=== Round 1 — {TICKER} ===")
    r1 = present_all(TICKER, MOCK_SCORES, MOCK_MACRO)
    for e in r1:
        print(f"  {e['agent']}: {e['vote']} — {e['argument'][:80]}...")

    print(f"\n=== Round 2 — {TICKER} ===")
    r2, delta = cross_examine(TICKER, MOCK_SCORES, r1)
    for e in r2:
        print(f"  {e['agent']}: {e['vote']} — {e['argument'][:80]}...")
    print("net_delta:", delta)

    failed = [e for e in r1 + r2 if "Fallback" in e.get("argument", "")]
    if failed:
        print(f"\nWARN: {len(failed)} turns used rule-based fallback")
    else:
        print("\nOK: all turns from LLM")


if __name__ == "__main__":
    main()
