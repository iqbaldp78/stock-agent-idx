import sys
import os
import argparse
import logging
from datetime import date, timedelta
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import dotenv
dotenv.load_dotenv()

from db import SessionLocal
from db.models import OhlcvPrice
from data.fetcher_stockbit import _fetch_ohlcv_range_api
from db.cache import save_ohlcv

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("backfill_metadata")

def backfill_ticker(ticker: str, start_date: str, end_date: str):
    logger.info(f"Backfilling metadata for {ticker} from {start_date} to {end_date}...")
    
    cur_start = pd.to_datetime(start_date).date()
    final_end = pd.to_datetime(end_date).date()
    total_rows = 0
    
    db = SessionLocal()
    try:
        from sqlalchemy import text
        while cur_start <= final_end:
            cur_end = min(final_end, cur_start + timedelta(days=90))
            
            try:
                df = _fetch_ohlcv_range_api(ticker, cur_start.isoformat(), cur_end.isoformat())
            except Exception as e:
                logger.error(f"Stockbit API error for {ticker} ({cur_start} to {cur_end}): {e}")
                cur_start = cur_end + timedelta(days=1)
                continue
            
            if df is None or df.empty:
                logger.debug(f"No data returned for {ticker} between {cur_start} and {cur_end}.")
                cur_start = cur_end + timedelta(days=1)
                continue

            for idx, row in df.iterrows():
                trade_date = idx.date() if hasattr(idx, "date") else idx
                params = {
                    "ticker": ticker,
                    "trade_date": trade_date,
                    "open": float(row.get("Open", 0) or 0),
                    "high": float(row.get("High", 0) or 0),
                    "low": float(row.get("Low", 0) or 0),
                    "close": float(row.get("Close", 0) or 0),
                    "volume": int(row.get("Volume", 0) or 0),
                    "frequency": int(row.get("Frequency", 0) or 0),
                    "net_foreign": int(row.get("NetForeign", 0) or 0),
                    "average_price": float(row.get("AveragePrice", 0) or 0),
                    "change_percentage": float(row.get("ChangePercentage", 0) or 0),
                    "source": "stockbit",
                }
                db.execute(text("""
                    INSERT INTO ohlcv_prices
                        (ticker, trade_date, open, high, low, close, volume, source, frequency, net_foreign, average_price, change_percentage)
                    VALUES
                        (:ticker, :trade_date, :open, :high, :low, :close, :volume, :source, :frequency, :net_foreign, :average_price, :change_percentage)
                    ON CONFLICT (ticker, trade_date) DO UPDATE SET
                        open = EXCLUDED.open, high = EXCLUDED.high,
                        low  = EXCLUDED.low,  close = EXCLUDED.close,
                        volume = EXCLUDED.volume,
                        frequency = EXCLUDED.frequency,
                        net_foreign = EXCLUDED.net_foreign,
                        average_price = EXCLUDED.average_price,
                        change_percentage = EXCLUDED.change_percentage,
                        created_at = NOW()
                """), params)
            
            db.commit()
            total_rows += len(df)
            cur_start = cur_end + timedelta(days=1)
            
        logger.info(f"Successfully backfilled {ticker}: {total_rows} total rows.")
    except Exception as e:
        db.rollback()
        logger.error(f"Error backfilling {ticker}: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Backfill OHLCV Metadata (Frequency, NetForeign, Average)")
    parser.add_argument("--ticker", type=str, help="Specific ticker to backfill (default: all unique in DB)", default=None)
    parser.add_argument("--start", type=str, help="Start date (YYYY-MM-DD)", default="2023-01-01")
    parser.add_argument("--end", type=str, help="End date (YYYY-MM-DD)", default=date.today().strftime("%Y-%m-%d"))
    
    args = parser.parse_args()
    
    tickers = []
    if args.ticker:
        tickers = [args.ticker]
    else:
        # Get all unique tickers from DB
        db = SessionLocal()
        rows = db.query(OhlcvPrice.ticker).distinct().all()
        tickers = [r[0] for r in rows]
        db.close()
        
    logger.info(f"Starting backfill for {len(tickers)} tickers...")
    for t in tickers:
        backfill_ticker(t, args.start, args.end)
        
    logger.info("Backfill complete.")
