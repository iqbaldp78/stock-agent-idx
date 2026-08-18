#!/usr/bin/env python3
"""
Clean up analysis signals, agent scores, debate logs, and IHSG predictions for a given date.
Usage:
  python scripts/clean_analysis_data.py [--date YYYY-MM-DD]
"""
import argparse
import logging
import os
import sys
from datetime import datetime, date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import func
from db import SessionLocal
from db.models import Signal, AgentScore, DebateLog, IhsgPrediction, Performance, PaperTrade

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

def clean_data_for_date(target_date: date):
    db = SessionLocal()
    try:
        logging.info(f"Cleaning up analysis data for date: {target_date}")
        
        # 1. Fetch signal IDs for target_date to handle foreign key constraints
        signal_records = db.query(Signal.id).filter(func.date(Signal.run_date) == target_date).all()
        signal_ids = [s[0] for s in signal_records]
        
        if signal_ids:
            # Delete performance entries linked to these signals
            deleted_perf = db.query(Performance).filter(Performance.signal_id.in_(signal_ids)).delete(synchronize_session=False)
            if deleted_perf:
                logging.info(f"Unlinked/deleted {deleted_perf} performance records.")
                
            # Set signal_id to NULL in paper_trades referencing these signals
            updated_trades = db.query(PaperTrade).filter(PaperTrade.signal_id.in_(signal_ids)).update({PaperTrade.signal_id: None}, synchronize_session=False)
            if updated_trades:
                logging.info(f"Unlinked {updated_trades} paper_trade records from signals.")

        # 2. Delete main analysis records
        deleted_signals = db.query(Signal).filter(func.date(Signal.run_date) == target_date).delete(synchronize_session=False)
        deleted_scores = db.query(AgentScore).filter(func.date(AgentScore.run_date) == target_date).delete(synchronize_session=False)
        deleted_debates = db.query(DebateLog).filter(func.date(DebateLog.run_date) == target_date).delete(synchronize_session=False)
        deleted_ihsg = db.query(IhsgPrediction).filter(func.date(IhsgPrediction.run_date) == target_date).delete(synchronize_session=False)
        
        db.commit()
        logging.info(f"Deleted {deleted_signals} signals, {deleted_scores} agent_scores, {deleted_debates} debate_logs, {deleted_ihsg} ihsg_predictions.")
        
        # 3. Reset UI cache file if target_date is today
        if target_date == date.today():
            json_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "last_analysis_result.json")
            if os.path.exists(json_file):
                with open(json_file, "w") as f:
                    f.write('{\n  "top_picks": [],\n  "debate_log": [],\n  "composites": {}\n}\n')
                logging.info(f"Reset UI cache file: {json_file}")
                
    except Exception as e:
        db.rollback()
        logging.exception(f"Failed to clean up data for date {target_date}: {e}")
        sys.exit(1)
    finally:
        db.close()

def main():
    parser = argparse.ArgumentParser(description="Clean analysis data for a specific date.")
    parser.add_argument("--date", type=str, help="Target date in YYYY-MM-DD format (default: today)")
    args = parser.parse_args()

    if args.date:
        try:
            target_date = datetime.strptime(args.date, "%Y-%m-%d").date()
        except ValueError:
            logging.error("Invalid date format. Use YYYY-MM-DD.")
            sys.exit(1)
    else:
        target_date = date.today()

    clean_data_for_date(target_date)

if __name__ == "__main__":
    main()
