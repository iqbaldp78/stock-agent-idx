import os
import json
import logging
import pandas as pd

from sqlalchemy import create_engine, text

# Konfigurasi berdasarkan docker-compose
VECTOR_DB_URL = "postgresql://vectoruser:vectorpassword@vector_postgres:5432/vectoragent"

logger = logging.getLogger(__name__)

# Buat engine SQLAlchemy
engine = create_engine(VECTOR_DB_URL)

def get_news_sentiment_features(ticker: str, start_date: str, end_date: str) -> pd.DataFrame:
    """
    Mengambil data sentimen berita dari Vector DB (tabel news_signals) 
    untuk ticker tertentu dalam rentang waktu tertentu.
    """
    query = text("""
        SELECT 
            DATE(created_at) as date,
            sentiment,
            sentiment_score,
            impact_scope
        FROM news_signals
        WHERE tickers @> CAST(:ticker_json AS jsonb)
          AND created_at BETWEEN :start AND :end
    """)
    
    ticker_json = json.dumps([ticker.upper()])
    
    try:
        with engine.connect() as conn:
            df = pd.read_sql(query, conn, params={"ticker_json": ticker_json, "start": start_date, "end": end_date})

        if df.empty:
            return pd.DataFrame()
        
        def calc_score(row):
            if pd.notnull(row.get('sentiment_score')) and isinstance(row.get('sentiment_score'), (int, float)):
                return float(row['sentiment_score'])
            sent_str = str(row.get('sentiment') or '').upper()
            if 'BULLISH' in sent_str or 'POSITIF' in sent_str:
                return 7.5
            elif 'BEARISH' in sent_str or 'NEGATIF' in sent_str:
                return 2.5
            return 5.0

        df['numeric_sentiment'] = df.apply(calc_score, axis=1)
        df['date'] = pd.to_datetime(df['date'])
        
        agg_df = df.groupby('date').agg(
            news_count=('numeric_sentiment', 'count'),
            avg_sentiment=('numeric_sentiment', 'mean')
        )
        
        return agg_df

        
        return agg_df
        
    except Exception as e:
        logger.error(f"[VectorDB] Error fetching sentiment for {ticker}: {e}")
        return pd.DataFrame()

if __name__ == "__main__":
    # Tes koneksi sederhana
    print("Testing connection...")
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1")).scalar()
            print(f"Connection successful: {result}")
    except Exception as e:
        print(f"Connection failed: {e}")
