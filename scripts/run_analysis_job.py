#!/usr/bin/env python3
"""
Runs the full analysis pipeline in a background process triggered by Streamlit.
Saves the result to DB and also serializes the output to a JSON file for the UI.
"""
import logging
import os
import sys
import json
from datetime import datetime, date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

def default_json_serializer(obj):
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if hasattr(obj, "item"):  # Handles numpy types (np.float64, np.int64, etc.)
        return obj.item()
    if hasattr(obj, "__dict__"):
        return obj.__dict__
    return str(obj)

def main():
    from graph.workflow import run_full_analysis
    from db.tracker import save_full_result

    # Check if a ticker argument is provided (e.g. BBCA or --ticker BBCA)
    args = sys.argv[1:]
    target_ticker = None
    if args:
        if args[0] == "--ticker" and len(args) > 1:
            target_ticker = args[1].strip().upper()
        elif not args[0].startswith("--"):
            target_ticker = args[0].strip().upper()

    if target_ticker:
        logging.info("[JOB] Starting single ticker analysis for %s...", target_ticker)
        try:
            result = run_full_analysis(universe=[target_ticker], include_portfolio=False)
            
            # Per user explicit instructions: DO NOT save single ticker run into main DB tables.
            # Save strictly as JSON file in data/single_analysis_results/
            results_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "single_analysis_results")
            os.makedirs(results_dir, exist_ok=True)
            
            now = datetime.now()
            timestamp_str = now.strftime("%Y%m%d_%H%M%S")
            
            to_save = {
                "ticker": target_ticker,
                "timestamp": now.isoformat(),
                "top_picks": result.get("top_picks", []),
                "debate_log": result.get("debate_log", []),
                "composites": result.get("composites", {}),
                "scores": result.get("scores", {}),
                "candidates": result.get("candidates", []),
                "finalists": result.get("finalists", []),
                "ml_predictions": result.get("ml_predictions", {}),
                "final_report": result.get("final_report", {}),
            }
            
            file_timestamped = os.path.join(results_dir, f"{target_ticker}_{timestamp_str}.json")
            file_latest_ticker = os.path.join(results_dir, f"latest_{target_ticker}.json")
            file_latest_single = os.path.join(results_dir, "latest_single_result.json")

            with open(file_timestamped, "w") as f:
                json.dump(to_save, f, indent=2, default=default_json_serializer)
                
            with open(file_latest_ticker, "w") as f:
                json.dump(to_save, f, indent=2, default=default_json_serializer)
                
            with open(file_latest_single, "w") as f:
                json.dump(to_save, f, indent=2, default=default_json_serializer)

            logging.info("[JOB] Single analysis complete for %s. Results written to %s", target_ticker, file_latest_ticker)
        except Exception as e:
            logging.exception("[JOB] Single ticker analysis failed: %s", e)
            sys.exit(1)
    else:
        logging.info("[JOB] Starting full background analysis...")
        try:
            result = run_full_analysis()
            save_full_result(result)
            logging.info("[JOB] Saved to database.")

            # Save specific keys for Streamlit UI
            output_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "last_analysis_result.json")
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            
            to_save = {
                "top_picks": result.get("top_picks", []),
                "debate_log": result.get("debate_log", []),
                "composites": {k: v for k, v in result.get("composites", {}).items()}
            }
            
            with open(output_file, 'w') as f:
                json.dump(to_save, f, indent=2, default=default_json_serializer)
                
            logging.info("[JOB] Analysis complete. Output written to %s", output_file)
        except Exception as e:
            logging.exception("[JOB] Analysis failed: %s", e)
            sys.exit(1)

if __name__ == "__main__":
    main()
