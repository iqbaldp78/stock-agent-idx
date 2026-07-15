import sys
import os
import json
from datetime import timedelta
import pandas as pd
from sqlalchemy import create_engine

sys.path.insert(0, '/app')

def run():
    db_url = "postgresql://stockuser:stockpassword@postgres:5432/stockagent"
    engine = create_engine(db_url)
    
    query = "SELECT run_date::date as p_date, current_price, component_scores FROM ihsg_predictions ORDER BY run_date ASC"
    preds_df = pd.read_sql(query, engine)
    preds_df = preds_df.drop_duplicates(subset=['p_date'], keep='last')
    
    actual_df = pd.read_sql("SELECT trade_date, close FROM ihsg_ohlcv ORDER BY trade_date ASC", engine)
    actual_df['trade_date'] = pd.to_datetime(actual_df['trade_date']).dt.date
    actual_dict = dict(zip(actual_df['trade_date'], actual_df['close']))
    
    print(f"{'Date':<12} | {'Mom':<5} | {'News':<5} | {'Sec':<5} | {'Brd':<5} | {'Mac':<5} | {'Act_%':<7}")
    print("-" * 60)
    
    for _, row in preds_df.iterrows():
        p_date = row['p_date']
        scores = row['component_scores']
        
        if not isinstance(scores, dict): continue
        
        mom = scores.get('momentum', 0.5)
        brd = scores.get('breadth', 0.5)
        mac = scores.get('macro', 0.5)
        sec = scores.get('sector', 0.5)
        news = scores.get('news', 0.5)
        
        actual_d1_pct = 0
        for i in range(1, 6):
            nd = p_date + timedelta(days=i)
            if nd in actual_dict:
                actual_d1_pct = (actual_dict[nd] - row['current_price']) / row['current_price'] * 100
                break
                
        print(f"{str(p_date):<12} | {mom:.2f}  | {news:.2f}  | {sec:.2f}  | {brd:.2f}  | {mac:.2f}  | {actual_d1_pct:+.2f}%")

if __name__ == "__main__":
    run()
