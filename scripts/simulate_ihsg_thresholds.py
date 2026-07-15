import sys
import os
import pandas as pd
from datetime import datetime, timedelta

# Append /app to sys.path so we can import from db
sys.path.insert(0, '/app')
from sqlalchemy import create_engine
import psycopg2

def run_simulation():
    db_url = "postgresql://stockuser:stockpassword@postgres:5432/stockagent"
    engine = create_engine(db_url)
    
    # Get historical predictions with their component scores
    query_preds = """
        SELECT 
            run_date::date as p_date,
            current_price,
            component_scores
        FROM ihsg_predictions
        ORDER BY run_date ASC
    """
    preds_df = pd.read_sql(query_preds, engine)
    preds_df = preds_df.drop_duplicates(subset=['p_date'], keep='last')
    
    # Get actual closing prices
    query_actual = """
        SELECT trade_date, close 
        FROM ihsg_ohlcv 
        ORDER BY trade_date ASC
    """
    actual_df = pd.read_sql(query_actual, engine)
    actual_df['trade_date'] = pd.to_datetime(actual_df['trade_date']).dt.date
    actual_dict = dict(zip(actual_df['trade_date'], actual_df['close']))
    
    # Evaluate configurations
    configs = [
        {"name": "Current (0.40 - 0.60)", "low": 0.40, "high": 0.60},
        {"name": "Proposed (0.45 - 0.55)", "low": 0.45, "high": 0.55},
        {"name": "Aggressive (0.48 - 0.52)", "low": 0.48, "high": 0.52}
    ]
    
    print("=" * 60)
    print("IHSG PREDICTOR THRESHOLD SIMULATION")
    print("=" * 60)
    
    results = []
    
    for config in configs:
        correct_count = 0
        total_eval = 0
        
        for idx, row in preds_df.iterrows():
            p_date = row['p_date']
            scores = row['component_scores']
            
            # Use safe combined score extraction
            if isinstance(scores, dict):
                combined = scores.get('combined', 0.5)
            else:
                combined = 0.5
                
            # Predict direction based on config
            if combined > config['high']:
                pred_dir = "BULLISH"
            elif combined < config['low']:
                pred_dir = "BEARISH"
            else:
                pred_dir = "SIDEWAYS"
                
            # Find next trading day actual closing price
            # Simple approach: look up to 5 days ahead for the next available actual price
            actual_next_close = None
            actual_d1_pct = 0
            
            for days_ahead in range(1, 6):
                next_date = p_date + timedelta(days=days_ahead)
                if next_date in actual_dict:
                    actual_next_close = actual_dict[next_date]
                    actual_d1_pct = (actual_next_close - row['current_price']) / row['current_price'] * 100
                    break
                    
            if actual_next_close is not None:
                total_eval += 1
                
                # Check accuracy
                is_correct = False
                if pred_dir == "BULLISH" and actual_d1_pct > 0:
                    is_correct = True
                elif pred_dir == "BEARISH" and actual_d1_pct < 0:
                    is_correct = True
                elif pred_dir == "SIDEWAYS" and abs(actual_d1_pct) < 0.5:
                    is_correct = True
                    
                if is_correct:
                    correct_count += 1
                    
        accuracy = (correct_count / total_eval * 100) if total_eval > 0 else 0
        print(f"Config: {config['name']}")
        print(f"Total Evaluated: {total_eval} days")
        print(f"Correct Direction: {correct_count} days")
        print(f"Accuracy: {accuracy:.2f}%")
        print("-" * 60)

if __name__ == "__main__":
    run_simulation()
