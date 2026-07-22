#!/usr/bin/env python3
"""
Jalankan full pipeline sekali (filter → scoring → debate → TOP 3).
Usage (di host):
  docker exec stock_app python scripts/run_konglo_analysis.py
  docker exec stock_app python scripts/run_konglo_analysis.py BRPT TPIA CUAN
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
    from db.tracker import save_full_result
    from agents.llm_client import get_status

    status = get_status()
    print("9Router:", status)

    result = run_konglo_analysis(universe=tickers)
    save_full_result(result, is_konglo=True)

    picks = result.get("top_picks", [])
    print(f"\n=== TOP {len(picks)} PICKS ===")
    for p in picks:
        print(
            f"  #{p.get('rank')} {p.get('ticker')} | {p.get('conviction')} | "
            f"entry={p.get('entry_zone')} | thesis={str(p.get('thesis', ''))[:80]}..."
        )
    mode = result.get("final_report", {}).get("synthesis_mode", "n/a")
    print(f"\nSynthesis mode: {mode}")
    print(f"Finalists: {[f['ticker'] for f in result.get('finalists', [])]}")

    from agents.debate.logging_utils import print_debate_log
    print_debate_log(result.get("debate_log", []))


if __name__ == "__main__":
    main()
