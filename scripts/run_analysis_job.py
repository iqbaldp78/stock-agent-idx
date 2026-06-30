#!/usr/bin/env python3
"""
Runs the full analysis pipeline in a background process triggered by Streamlit.
Saves the result to DB and also serializes the output to a JSON file for the UI.
"""
import logging
import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

def main():
    from graph.workflow import run_full_analysis
    from db.tracker import save_full_result

    logging.info("[JOB] Starting background analysis...")
    try:
        result = run_full_analysis()
        save_full_result(result)
        logging.info("[JOB] Saved to database.")

        # Save specific keys for Streamlit UI
        output_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "last_analysis_result.json")
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        # We only dump things that are JSON serializable easily (or we just convert them)
        to_save = {
            "top_picks": result.get("top_picks", []),
            "debate_log": result.get("debate_log", []),
            "composites": {k: v for k, v in result.get("composites", {}).items()} # Assuming dict of floats/strings
        }
        
        with open(output_file, 'w') as f:
            json.dump(to_save, f)
            
        logging.info("[JOB] Analysis complete. Output written to %s", output_file)
    except Exception as e:
        logging.exception("[JOB] Analysis failed: %s", e)
        sys.exit(1)

if __name__ == "__main__":
    main()
