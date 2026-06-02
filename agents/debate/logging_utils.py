"""Structured console logging for multi-agent debate."""
from __future__ import annotations

import logging
from collections import defaultdict

logger = logging.getLogger("agents.debate")

_VOTE_ICON = {"BUY": "🟢 BUY", "HOLD": "⚪ HOLD", "SELL": "🔴 SELL"}
_AGENT_LABEL = {
    "fundamental": "FUNDAMENTAL",
    "technical": "TECHNICAL",
    "bandarmologi": "BANDARMOLOGI",
    "macro": "MACRO",
}


def log_debate_turn(entry: dict, *, source: str = "llm") -> None:
    """Log satu giliran debat ke logger (muncul di docker logs / Streamlit)."""
    if not entry:
        return
    rnd = entry.get("round", "?")
    ticker = entry.get("ticker", "?")
    agent = entry.get("agent", "?")
    vote = entry.get("vote", "HOLD")
    argument = (entry.get("argument") or "").strip()
    vote_label = _VOTE_ICON.get(str(vote).upper(), vote)

    header = (
        f"[DEBATE R{rnd}] {ticker} | {_AGENT_LABEL.get(agent, agent.upper())} "
        f"| {vote_label} ({source})"
    )
    logger.info(header)
    if argument:
        for line in argument.split("\n"):
            line = line.strip()
            if line:
                logger.info("  → %s", line)


def log_debate_section(title: str) -> None:
    logger.info("")
    logger.info("=" * 72)
    logger.info("  %s", title)
    logger.info("=" * 72)


def log_ticker_header(ticker: str, composite_score: float | None = None) -> None:
    if composite_score is not None:
        logger.info("--- %s (composite=%.2f) ---", ticker, composite_score)
    else:
        logger.info("--- %s ---", ticker)


def log_synthesis(
    ticker: str,
    composite_score: float,
    debate_bonus: float,
    final_score: float,
    *,
    net_vote: float | None = None,
) -> None:
    extra = f", net_vote={net_vote:+.2f}" if net_vote is not None else ""
    logger.info(
        "[DEBATE SYNTH] %s | composite=%.2f%s | bonus=%+.2f | final=%.2f",
        ticker,
        composite_score,
        extra,
        debate_bonus,
        final_score,
    )


def log_finalists(finalists: list[dict]) -> None:
    log_debate_section("HASIL DEBAT — FINALIS")
    for i, f in enumerate(finalists, 1):
        logger.info(
            "  #%d %s | final_score=%.2f | composite=%.2f | debate_bonus=%+.2f",
            i,
            f.get("ticker"),
            f.get("final_score", 0),
            f.get("composite_score", 0),
            f.get("debate_bonus", 0),
        )


def format_debate_log_text(debate_log: list[dict]) -> str:
    """Format lengkap untuk print / UI."""
    if not debate_log:
        return "(tidak ada log debat)"

    by_ticker: dict[str, list[dict]] = defaultdict(list)
    market: list[dict] = []
    for e in debate_log:
        t = e.get("ticker", "?")
        if t == "MARKET":
            market.append(e)
        else:
            by_ticker[t].append(e)

    lines: list[str] = []
    if market:
        lines.append("═══ MAKRO (global) ═══")
        for e in market:
            lines.extend(_format_entry_lines(e))

    for ticker in sorted(by_ticker.keys()):
        lines.append(f"\n═══ {ticker} ═══")
        for rnd in (1, 2):
            rnd_entries = [e for e in by_ticker[ticker] if e.get("round") == rnd]
            if not rnd_entries:
                continue
            lines.append(f"  Round {rnd}:")
            for e in rnd_entries:
                lines.extend(_format_entry_lines(e, indent="    "))

    return "\n".join(lines)


def _format_entry_lines(entry: dict, indent: str = "  ") -> list[str]:
    agent = entry.get("agent", "?")
    vote = entry.get("vote", "?")
    arg = (entry.get("argument") or "").strip()
    vote_label = _VOTE_ICON.get(str(vote).upper(), vote)
    lines = [f"{indent}[{agent}] {vote_label}"]
    if arg:
        lines.append(f"{indent}  {arg}")
    return lines


def print_debate_log(debate_log: list[dict]) -> None:
    """Print ke stdout (untuk scripts/run_analysis.py)."""
    print("\n" + format_debate_log_text(debate_log) + "\n")
