"""
Seed the Dashboard Performance UI using data from backtest_result.json
This script reads the JSON, and creates corresponding mock Signals and Performance rows.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from sqlalchemy.orm import Session

from db import SessionLocal
from db.models import Signal, Performance

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def find_backtest_result_path():
    candidates = [
        Path("backtest_result.json"),
        Path("/app/backtest_result.json"),
        Path(__file__).resolve().parents[1] / "backtest_result.json",
    ]
    for path in candidates:
        if path.exists():
            return path
    return None

def main():
    json_path = find_backtest_result_path()
    if not json_path:
        logger.error("backtest_result.json not found!")
        return

    logger.info(f"Loading data from {json_path}")
    with open(json_path, 'r') as f:
        data = json.load(f)
    
    tickers_data = data.get("tickers", {})
    all_trades = []
    
    # Grab all trades
    for ticker, tdata in tickers_data.items():
        all_trades.extend(tdata.get("trades", []))
    
    # Sort by entry date descending to get the most recent trades
    all_trades.sort(key=lambda x: x.get("entry_date", ""), reverse=True)
    all_trades = all_trades[:2000] # Cap at 2000 to prevent DB bloat
    
    db: Session = SessionLocal()
    try:
        # Clear previous seeded backtest data so we can rerun this cleanly
        db.query(Performance).filter(Performance.signal_id.in_(
            db.query(Signal.id).filter(Signal.weight_mode == "backtest_seeded")
        )).delete(synchronize_session=False)
        db.query(Signal).filter(Signal.weight_mode == "backtest_seeded").delete(synchronize_session=False)
        db.commit()

        logger.info(f"Seeding {len(all_trades)} trades into database...")
        
        for i, t in enumerate(all_trades):
            try:
                run_date = datetime.strptime(t["entry_date"], "%Y-%m-%d").date()
                check_date = datetime.strptime(t["exit_date"], "%Y-%m-%d").date()
            except Exception:
                continue
                
            ticker = t["ticker"]
            entry_price = float(t["entry_price"])
            exit_price = float(t["exit_price"])
            ret_pct = float(t["return_pct"])
            res = t.get("result", "")
            
            # Map TIME_EXIT / HOLD_EXP to HIT_TP if return > 0
            if "HIT_SL" not in res:
                res = "HIT_TP1" if ret_pct > 0 else "HIT_SL"
            else:
                res = "HIT_SL"
            
            # Create Signal
            sig = Signal(
                run_date=run_date,
                ticker=ticker,
                rank=1,
                signal="BUY",
                entry_low=entry_price * 0.99,
                entry_high=entry_price * 1.01,
                target_1=entry_price * 1.08,
                stop_loss=entry_price * 0.97,
                conviction="HIGH" if ret_pct > 0 else "MEDIUM",
                thesis="Seeded from historical backtest for performance tracking.",
                weight_mode="backtest_seeded",
                composite_score=8.5,
                created_at=run_date
            )
            db.add(sig)
            db.flush() # get ID
            
            # Create Performance
            perf = Performance(
                signal_id=sig.id,
                check_date=check_date,
                actual_price=exit_price,
                result=res,
                return_pct=ret_pct,
                created_at=check_date
            )
            db.add(perf)
            
            if i > 0 and i % 500 == 0:
                logger.info(f"Processed {i} trades...")
                db.commit()
                
        db.commit()
        logger.info("Successfully seeded database with backtest data!")
        
    except Exception as e:
        db.rollback()
        logger.exception("Failed to seed database")
    finally:
        db.close()

if __name__ == "__main__":
    main()
