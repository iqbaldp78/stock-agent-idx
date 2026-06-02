#!/usr/bin/env python3
"""Smoke test: 9Router health + rule-based fallback paths."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main():
    from config import LLM_BASE_URL, LLM_ENABLED, get_configured_llm_models
    from agents.llm_client import get_status, health_check
    from graph.workflow import run_debate_rule_based
    from agents.investment_manager import synthesize_rule_based

    print("=== Config ===")
    print("LLM_ENABLED:", LLM_ENABLED)
    print("LLM_BASE_URL:", LLM_BASE_URL)
    models = get_configured_llm_models()
    print("Models:", models)

    print("\n=== 9Router health ===")
    status = get_status()
    print(status)
    print("health_check:", health_check())

    print("\n=== Rule-based debate (mock state) ===")
    state = {
        "scores": {
            "BBCA": {
                "bandarm": {"score": 8, "signal": "ACCUMULATION", "data_used": ["x"]},
                "technical": {"score": 7, "setup": "breakout", "data_used": ["y"]},
                "fundamental": {"score": 8, "key_points": ["ROE ok"], "data_used": ["z"]},
            }
        },
        "composites": {
            "BBCA": {"composite_score": 7.5, "weight_mode": "default"},
        },
        "macro_data": {"score": 7},
    }
    debate = run_debate_rule_based(state)
    print("finalists:", debate.get("finalists"))
    print("debate_log entries:", len(debate.get("debate_log", [])))

    state["finalists"] = debate["finalists"]
    state["debate_log"] = debate["debate_log"]
    im = synthesize_rule_based(state)
    print("top_picks:", [p["ticker"] for p in im.get("top_picks", [])])
    print("\nOK")


if __name__ == "__main__":
    main()
