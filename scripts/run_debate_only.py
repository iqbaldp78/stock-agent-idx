#!/usr/bin/env python3
"""
Run Debate Only - Jalankan debate workflow tanpa investment manager.
Filter → Scoring → Debate → Output finalists.

Usage:
    python scripts/run_debate_only.py              # All LQ45 tickers
    python scripts/run_debate_only.py BBCA BMRI    # Specific tickers
"""
import sys
import os
import json
import logging
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from graph.workflow import run_filter, run_parallel_scoring, run_debate
from config import get_universe

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def run_debate_only(universe: list[str] | None = None) -> dict:
    """
    Run debate workflow only (without Investment Manager).

    Args:
        universe: List of tickers to analyze. If None, use all from config.

    Returns:
        dict with keys: candidates, scores, composites, macro_data, debate_log, finalists
    """
    start_time = datetime.now()
    logger.info("=" * 80)
    logger.info("DEBATE-ONLY WORKFLOW START")
    logger.info("=" * 80)

    # Prepare initial state
    initial_state = {
        "universe": universe or get_universe(),
        "candidates": [],
        "macro_data": {},
        "scores": {},
        "composites": {},
        "debate_log": [],
        "finalists": [],
    }

    logger.info(f"Universe: {len(initial_state['universe'])} tickers")

    # Phase 1: Filter
    logger.info("\n[PHASE 1] FILTER")
    logger.info("-" * 80)
    state = run_filter(initial_state)
    logger.info(f"Candidates after filter: {len(state.get('candidates', []))}")

    if not state.get("candidates"):
        logger.warning("No candidates after filter. Stopping.")
        return state

    # Phase 2: Scoring
    logger.info("\n[PHASE 2] SCORING")
    logger.info("-" * 80)
    scoring_result = run_parallel_scoring(state)
    state.update(scoring_result)
    logger.info(f"Scored tickers: {len(state.get('composites', {}))}")

    # Show top 10 by composite score
    composites = state.get("composites", {})
    if composites:
        sorted_tickers = sorted(
            composites.items(),
            key=lambda x: x[1]["composite_score"],
            reverse=True,
        )
        logger.info("\nTop 10 by composite score:")
        for i, (ticker, comp) in enumerate(sorted_tickers[:10], 1):
            logger.info(
                f"  {i:2d}. {ticker:6s} | score={comp['composite_score']:5.2f} | "
                f"mode={comp['weight_mode']}"
            )

    # Phase 3: Debate
    logger.info("\n[PHASE 3] DEBATE")
    logger.info("-" * 80)
    debate_result = run_debate(state)
    state.update(debate_result)

    finalists = state.get("finalists", [])
    logger.info(f"\nFinalists: {len(finalists)}")

    if finalists:
        logger.info("\nFINAL RANKING:")
        logger.info("-" * 80)
        for i, f in enumerate(finalists, 1):
            ticker = f["ticker"]
            final_score = f.get("final_score", 0)
            composite = f.get("composite_score", 0)
            bonus = f.get("debate_bonus", 0)
            mode = f.get("weight_mode", "N/A")
            logger.info(
                f"  {i:2d}. {ticker:6s} | final={final_score:5.2f} "
                f"(composite={composite:5.2f} + bonus={bonus:+5.2f}) | mode={mode}"
            )

    # Summary
    elapsed = (datetime.now() - start_time).total_seconds()
    logger.info("\n" + "=" * 80)
    logger.info("DEBATE-ONLY WORKFLOW COMPLETE")
    logger.info(f"Elapsed time: {elapsed:.1f}s")
    logger.info(f"Total analyzed: {len(composites)}")
    logger.info(f"Finalists: {len(finalists)}")
    logger.info("=" * 80)

    return state


def main():
    """CLI entry point."""
    # Parse command-line arguments
    if len(sys.argv) > 1:
        universe = [ticker.strip().upper() for ticker in sys.argv[1:]]
        logger.info(f"Running debate for custom tickers: {universe}")
    else:
        universe = None
        logger.info("Running debate for all LQ45 tickers")

    try:
        result = run_debate_only(universe)

        # Save result to JSON for inspection
        output_file = "debate_result.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False, default=str)
        logger.info(f"\nResult saved to: {output_file}")

        # Print finalists summary
        finalists = result.get("finalists", [])
        if finalists:
            print("\n" + "=" * 80)
            print("TOP FINALISTS")
            print("=" * 80)
            for i, f in enumerate(finalists[:7], 1):
                print(f"{i}. {f['ticker']} - Score: {f.get('final_score', 0):.2f}")
            print("=" * 80)

        return 0

    except Exception as e:
        logger.exception(f"Error running debate: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
