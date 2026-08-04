import os
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
            impact_scope
        FROM news_signals
        WHERE tickers @> :ticker_array
          AND created_at BETWEEN :start AND :end
    """)
    
    # tickers di PGVECTOR adalah array (text[]), jadi kita passing sebagai array PG
    ticker_array = f'{{{ticker}}}'
    
    try:
        with engine.connect() as conn:
            df = pd.read_sql(query, conn, params={"ticker_array": ticker_array, "start": start_date, "end": end_date})
            
        if df.empty:
            return pd.DataFrame()
        
        # Agregasi sentimen per hari: rata-rata sentimen dan jumlah berita
        df['date'] = pd.to_datetime(df['date'])
        
        # Asumsi kolom 'sentiment' berisi angka, misal -1 sampai 1 atau 1 sampai 10
        # Sesuaikan dengan format yang ada di news_signals (tadi kita lihat sentiment ada datanya)
        agg_df = df.groupby('date').agg(
            news_count=('sentiment', 'count'),
            avg_sentiment=('sentiment', 'mean')
        )
        
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
