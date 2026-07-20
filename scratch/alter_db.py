import sys
import os
import sqlalchemy
from sqlalchemy import text

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import dotenv
dotenv.load_dotenv()

from db import SessionLocal

db = SessionLocal()
try:
    print("Executing ALTER TABLE on ohlcv_prices...")
    # Using numeric for float values and big int for net foreign to match the plan
    db.execute(text("ALTER TABLE ohlcv_prices ADD COLUMN IF NOT EXISTS frequency INTEGER DEFAULT 0;"))
    db.execute(text("ALTER TABLE ohlcv_prices ADD COLUMN IF NOT EXISTS net_foreign BIGINT DEFAULT 0;"))
    db.execute(text("ALTER TABLE ohlcv_prices ADD COLUMN IF NOT EXISTS average_price NUMERIC(12, 2) DEFAULT 0;"))
    db.execute(text("ALTER TABLE ohlcv_prices ADD COLUMN IF NOT EXISTS change_percentage NUMERIC(12, 2) DEFAULT 0;"))
    
    print("Executing ALTER TABLE on ihsg_ohlcv...")
    db.execute(text("ALTER TABLE ihsg_ohlcv ADD COLUMN IF NOT EXISTS frequency INTEGER DEFAULT 0;"))
    db.execute(text("ALTER TABLE ihsg_ohlcv ADD COLUMN IF NOT EXISTS net_foreign BIGINT DEFAULT 0;"))
    db.execute(text("ALTER TABLE ihsg_ohlcv ADD COLUMN IF NOT EXISTS average_price NUMERIC(12, 2) DEFAULT 0;"))
    db.execute(text("ALTER TABLE ihsg_ohlcv ADD COLUMN IF NOT EXISTS change_percentage NUMERIC(12, 2) DEFAULT 0;"))
    
    db.commit()
    print("SUCCESS: Columns added successfully.")
except Exception as e:
    db.rollback()
    print(f"FAILED: {e}")
finally:
    db.close()
