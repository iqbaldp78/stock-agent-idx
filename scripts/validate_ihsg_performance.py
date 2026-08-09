import sys
import pandas as pd
from datetime import timedelta
from sqlalchemy import create_engine
import logging

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

sys.path.insert(0, '/app')

def validate_ihsg_performance():
    db_url = "postgresql://stockuser:stockpassword@postgres:5432/stockagent"
    engine = create_engine(db_url)
    
    query = """
        WITH predicted_data AS (
            SELECT DISTINCT ON (run_date::date)
                run_date::date as p_date,
                direction,
                current_price,
                day_1_price,
                day_1_pct
            FROM ihsg_predictions
            ORDER BY run_date::date DESC, run_date DESC
        ),
        actual_data AS (
            SELECT trade_date, close
            FROM ihsg_ohlcv
        ),
        matched_data AS (
            SELECT 
                p.p_date,
                p.direction,
                p.current_price,
                p.day_1_price as target_d1,
                p.day_1_pct,
                a1.close as actual_d1,
                ROUND(((a1.close - p.current_price) / p.current_price * 100)::numeric, 2) as actual_d1_pct
            FROM predicted_data p
            LEFT JOIN (
                SELECT p_date, min(trade_date) as next_day 
                FROM predicted_data p2
                JOIN actual_data a ON a.trade_date > p2.p_date
                GROUP BY p_date
            ) next_trade ON next_trade.p_date = p.p_date
            LEFT JOIN actual_data a1 ON a1.trade_date = next_trade.next_day
            WHERE a1.close IS NOT NULL
        )
        SELECT 
            COUNT(*) as total_predictions,
            SUM(CASE 
                WHEN direction = 'BULLISH' AND actual_d1_pct >= 0 THEN 1
                WHEN direction = 'BEARISH' AND actual_d1_pct < 0 THEN 1
                WHEN direction = 'SIDEWAYS' AND abs(actual_d1_pct) < 0.5 THEN 1
                ELSE 0 
            END) as correct_direction,
            ROUND(AVG(abs(day_1_pct - actual_d1_pct)), 2) as mean_absolute_error_pct
        FROM matched_data;
    """
    
    try:
        results = pd.read_sql(query, engine)
        
        logger.info("============================================================")
        logger.info("📊 VALIDASI AKURASI PREDIKSI IHSG (Historical Database)")
        logger.info("============================================================")
        
        if results.empty or results.iloc[0]['total_predictions'] == 0:
            logger.info("Belum ada data cukup untuk di-validasi.")
            return
            
        row = results.iloc[0]
        total = row['total_predictions']
        correct = row['correct_direction']
        mae = row['mean_absolute_error_pct']
        acc = (correct / total * 100) if total > 0 else 0
        
        logger.info(f"Total Trading Days Divalidasi : {total} hari")
        logger.info(f"Tebakan Arah (Tren) Benar     : {correct} hari ({acc:.1f}%)")
        logger.info(f"Rata-rata Meleset (MAE)       : {mae}% (jarak harga prediksi vs aktual)")
        logger.info("============================================================")
        
    except Exception as e:
        logger.error(f"Gagal melakukan validasi performa IHSG: {e}")

if __name__ == "__main__":
    validate_ihsg_performance()
