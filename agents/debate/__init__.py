"""Multi-agent LLM debate (Phase 3)."""


def run_llm_debate(state: dict) -> dict:
    from agents.debate.orchestrator import run_llm_debate as _run

    return _run(state)


__all__ = ["run_llm_debate"]
