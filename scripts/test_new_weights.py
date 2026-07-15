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
    
    # Get preds with explicit component scores
    query = "SELECT run_date::date as p_date, current_price, component_scores FROM ihsg_predictions ORDER BY run_date ASC"
    preds_df = pd.read_sql(query, engine)
    preds_df = preds_df.drop_duplicates(subset=['p_date'], keep='last')
    
    # Get actuals
    actual_df = pd.read_sql("SELECT trade_date, close FROM ihsg_ohlcv ORDER BY trade_date ASC", engine)
    actual_df['trade_date'] = pd.to_datetime(actual_df['trade_date']).dt.date
    actual_dict = dict(zip(actual_df['trade_date'], actual_df['close']))
    
    print(f"{'Date':<12} | {'Old_Cmb':<8} | {'New_Cmb':<8} | {'Old_Dir':<9} | {'New_Dir':<9} | {'Act_%':<7} | {'Old_Acc':<7} | {'New_Acc':<7}")
    print("-" * 90)
    
    total = 0
    correct_old = 0
    correct_new = 0
    
    for _, row in preds_df.iterrows():
        p_date = row['p_date']
        scores = row['component_scores']
        
        if not isinstance(scores, dict): continue
        
        # Original weights: Mom(0.3) + Brd(0.25) + Mac(0.15) + Sec(0.15) + News(0.15)
        old_comb = scores.get('combined', 0.5)
        
        # Momentum often lags, Breadth is usually noise on daily, News is very reactive
        # Let's try heavily weighting Momentum and News, dropping Macro/Sector noise
        mom = scores.get('momentum', 0.5)
        brd = scores.get('breadth', 0.5)
        mac = scores.get('macro', 0.5)
        sec = scores.get('sector', 0.5)
        news = scores.get('news', 0.5)
        
        # New aggressive weights prioritizing Momentum and News
        # Also let's push the score further from 0.5 if it's leaning
        new_comb = (mom * 0.5) + (news * 0.3) + (sec * 0.2)
        
        # Stretch it so it hits thresholds easier
        new_comb = 0.5 + ((new_comb - 0.5) * 1.5)
        new_comb = max(0, min(1, new_comb))
        
        # Direction Logic (Aggressive threshold)
        old_dir = "BULLISH" if old_comb > 0.6 else ("BEARISH" if old_comb < 0.4 else "SIDEWAYS")
        new_dir = "BULLISH" if new_comb > 0.52 else ("BEARISH" if new_comb < 0.48 else "SIDEWAYS")
        
        actual_d1_pct = 0
        found = False
        for i in range(1, 6):
            nd = p_date + timedelta(days=i)
            if nd in actual_dict:
                actual_d1_pct = (actual_dict[nd] - row['current_price']) / row['current_price'] * 100
                found = True
                break
                
        if found:
            total += 1
            
            old_correct = False
            if old_dir == "BULLISH" and actual_d1_pct > 0: old_correct = True
            elif old_dir == "BEARISH" and actual_d1_pct < 0: old_correct = True
            elif old_dir == "SIDEWAYS" and abs(actual_d1_pct) < 0.5: old_correct = True
                
            new_correct = False
            if new_dir == "BULLISH" and actual_d1_pct > 0: new_correct = True
            elif new_dir == "BEARISH" and actual_d1_pct < 0: new_correct = True
            elif new_dir == "SIDEWAYS" and abs(actual_d1_pct) < 0.5: new_correct = True
            
            if old_correct: correct_old += 1
            if new_correct: correct_new += 1
            
            print(f"{str(p_date):<12} | {old_comb:.4f}   | {new_comb:.4f}   | {old_dir:<9} | {new_dir:<9} | {actual_d1_pct:+.2f}% | {str(old_correct):<7} | {str(new_correct):<7}")
            
    print("-" * 90)
    print(f"Total Evaluated: {total}")
    print(f"Old Accuracy: {correct_old/total*100:.1f}%")
    print(f"New Accuracy: {correct_new/total*100:.1f}%")

if __name__ == "__main__":
    run()
