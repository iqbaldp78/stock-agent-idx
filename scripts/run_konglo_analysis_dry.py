#!/usr/bin/env python3
"""
Jalankan full pipeline Konglo Play sekali (filter → scoring → debate → TOP 3) TANPA menyimpan ke DB.
Usage (di host):
  docker compose exec app python scripts/run_konglo_analysis_dry.py
  docker compose exec app python scripts/run_konglo_analysis_dry.py BRPT TPIA CUAN
"""
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

def main():
    tickers = sys.argv[1:] if len(sys.argv) > 1 else None
    from graph.konglo_workflow import run_konglo_analysis
    from agents.llm_client import get_status

    status = get_status()
    print("9Router Status:", status)
    print("=== KONGLO ANALYSIS (DRY RUN - NOT SAVING TO DB) ===")

    result = run_konglo_analysis(universe=tickers)
    # DRY RUN: save_full_result(result, is_konglo=True) is intentionally skipped!

    picks = result.get("top_picks", [])
    print(f"\n=== TOP {len(picks)} KONGLO PICKS ===")
    for p in picks:
        print(
            f"  #{p.get('rank')} {p.get('ticker')} | {p.get('conviction')} | "
            f"entry={p.get('entry_zone')} | thesis={str(p.get('thesis', ''))[:100]}..."
        )
    mode = result.get("final_report", {}).get("synthesis_mode", "n/a")
    print(f"\nSynthesis mode: {mode}")
    print(f"Finalists: {[f['ticker'] for f in result.get('finalists', [])]}")

    from agents.debate.logging_utils import print_debate_log
    print_debate_log(result.get("debate_log", []))


if __name__ == "__main__":
    main()
