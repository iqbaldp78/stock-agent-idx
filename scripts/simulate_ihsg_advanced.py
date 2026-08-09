import sys
import pandas as pd
from datetime import timedelta

sys.path.insert(0, '/app')
from sqlalchemy import create_engine

def run_sim():
    db_url = "postgresql://stockuser:stockpassword@postgres:5432/stockagent"
    engine = create_engine(db_url)
    
    preds_df = pd.read_sql("SELECT run_date::date as p_date, current_price, component_scores FROM ihsg_predictions ORDER BY run_date ASC", engine)
    preds_df = preds_df.drop_duplicates(subset=['p_date'], keep='last')
    
    actual_df = pd.read_sql("SELECT trade_date, close FROM ihsg_ohlcv ORDER BY trade_date ASC", engine)
    actual_df['trade_date'] = pd.to_datetime(actual_df['trade_date']).dt.date
    actual_dict = dict(zip(actual_df['trade_date'], actual_df['close']))
    
    print(f"{'Date':<12} | {'Combined':<8} | {'Binary (>=0.50)':<18} | {'Legacy (0.4-0.6)':<18} | {'Actual D+1 %':<12}")
    print("-" * 80)
    
    for idx, row in preds_df.iterrows():
        p_date = row['p_date']
        scores = row['component_scores']
        combined = scores.get('combined', 0.5) if isinstance(scores, dict) else 0.5
        
        dir_binary = "BULLISH" if combined >= 0.50 else "BEARISH"
        dir_legacy = "BULLISH" if combined > 0.60 else ("BEARISH" if combined < 0.40 else "SIDEWAYS")
        
        actual_d1_pct = 0
        found = False
        for i in range(1, 6):
            nd = p_date + timedelta(days=i)
            if nd in actual_dict:
                actual_d1_pct = (actual_dict[nd] - row['current_price']) / row['current_price'] * 100
                found = True
                break
                
        if found:
            print(f"{str(p_date):<12} | {combined:.4f}   | {dir_binary:<18} | {dir_legacy:<18} | {actual_d1_pct:+.2f}%")

if __name__ == "__main__":
    run_sim()
