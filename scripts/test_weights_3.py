import sys
import pandas as pd
from datetime import timedelta
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
    
    print(f"{'Date':<12} | {'New_Cmb':<8} | {'New_Dir':<9} | {'Act_%':<7} | {'New_Acc':<7}")
    print("-" * 50)
    
    total = 0
    correct = 0
    
    for _, row in preds_df.iterrows():
        p_date = row['p_date']
        scores = row['component_scores']
        if not isinstance(scores, dict): continue
        
        # Looking at the data, Breadth (Brd) is highly correlated with actual moves.
        # Mom is too lagging, Mac/Sec are static noise here.
        # Let's lean heavily on Breadth + Momentum
        mom = scores.get('momentum', 0.5)
        brd = scores.get('breadth', 0.5)
        news = scores.get('news', 0.5)
        
        # Calculate new score heavily weighted to Breadth
        new_comb = (brd * 0.6) + (mom * 0.25) + (news * 0.15)
        
        # Threshold adjusted
        new_dir = "BULLISH" if new_comb > 0.52 else ("BEARISH" if new_comb < 0.48 else "SIDEWAYS")
        
        found = False
        for i in range(1, 6):
            nd = p_date + timedelta(days=i)
            if nd in actual_dict:
                actual_d1_pct = (actual_dict[nd] - row['current_price']) / row['current_price'] * 100
                found = True
                break
                
        if found:
            total += 1
            is_correct = False
            if new_dir == "BULLISH" and actual_d1_pct > 0: is_correct = True
            elif new_dir == "BEARISH" and actual_d1_pct < 0: is_correct = True
            elif new_dir == "SIDEWAYS" and abs(actual_d1_pct) < 0.5: is_correct = True
            
            if is_correct: correct += 1
            
            print(f"{str(p_date):<12} | {new_comb:.4f}   | {new_dir:<9} | {actual_d1_pct:+.2f}% | {str(is_correct):<7}")
            
    print("-" * 50)
    print(f"Accuracy: {correct/total*100:.1f}% ({correct}/{total})")

if __name__ == "__main__":
    run()
