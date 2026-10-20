import logging
from sqlalchemy import text, inspect
from db import engine
from db.models import Base

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("schema_migrator")

def migrate():
    with engine.begin() as conn:
        logger.info("1. Adding missing columns to existing tables...")
        
        # universe
        conn.execute(text("ALTER TABLE universe ADD COLUMN IF NOT EXISTS is_konglo BOOLEAN DEFAULT FALSE;"))
        
        # signals
        conn.execute(text("ALTER TABLE signals ADD COLUMN IF NOT EXISTS batch_id VARCHAR(36);"))
        conn.execute(text("ALTER TABLE signals ADD COLUMN IF NOT EXISTS is_konglo BOOLEAN DEFAULT FALSE;"))
        conn.execute(text("ALTER TABLE signals ADD COLUMN IF NOT EXISTS fair_value JSONB;"))
        
        # ohlcv_prices
        conn.execute(text("ALTER TABLE ohlcv_prices ADD COLUMN IF NOT EXISTS frequency INTEGER DEFAULT 0;"))
        conn.execute(text("ALTER TABLE ohlcv_prices ADD COLUMN IF NOT EXISTS net_foreign BIGINT DEFAULT 0;"))
        conn.execute(text("ALTER TABLE ohlcv_prices ADD COLUMN IF NOT EXISTS average_price NUMERIC(12, 2) DEFAULT 0;"))
        conn.execute(text("ALTER TABLE ohlcv_prices ADD COLUMN IF NOT EXISTS change_percentage NUMERIC(12, 2) DEFAULT 0;"))
        
        # ihsg_ohlcv
        conn.execute(text("ALTER TABLE ihsg_ohlcv ADD COLUMN IF NOT EXISTS frequency INTEGER DEFAULT 0;"))
        conn.execute(text("ALTER TABLE ihsg_ohlcv ADD COLUMN IF NOT EXISTS net_foreign BIGINT DEFAULT 0;"))
        conn.execute(text("ALTER TABLE ihsg_ohlcv ADD COLUMN IF NOT EXISTS average_price NUMERIC(12, 2) DEFAULT 0;"))
        conn.execute(text("ALTER TABLE ihsg_ohlcv ADD COLUMN IF NOT EXISTS change_percentage NUMERIC(12, 2) DEFAULT 0;"))
        
        # portfolio_holdings
        conn.execute(text("ALTER TABLE portfolio_holdings ADD COLUMN IF NOT EXISTS user_id INTEGER;"))
        
        logger.info("Columns updated successfully.")

    logger.info("2. Creating any missing tables from Base.metadata...")
    Base.metadata.create_all(engine)
    logger.info("Tables created successfully.")

    logger.info("3. Verifying schema consistency...")
    inspector = inspect(engine)
    missing = False
    for table_name, table in Base.metadata.tables.items():
        if not inspector.has_table(table_name):
            logger.error(f"Still missing table: {table_name}")
            missing = True
        else:
            existing_cols = {col['name'] for col in inspector.get_columns(table_name)}
            model_cols = {col.name for col in table.columns}
            diff = model_cols - existing_cols
            if diff:
                logger.error(f"Table {table_name} still missing columns: {diff}")
                missing = True
    
    if not missing:
        logger.info("ALL TABLES AND COLUMNS ARE NOW FULLY IN SYNC!")
    else:
        logger.warning("Some discrepancies remain.")

if __name__ == "__main__":
    migrate()
