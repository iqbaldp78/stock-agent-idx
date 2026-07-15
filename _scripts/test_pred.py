import psycopg2
import psycopg2.extras
import os
import json

def get_db_conn():
    return psycopg2.connect(
        dbname=os.getenv("POSTGRES_DB", "stockagent"),
        user=os.getenv("POSTGRES_USER", "stockuser"),
        password=os.getenv("POSTGRES_PASSWORD", "stockpassword"),
        host=os.getenv("POSTGRES_HOST", "postgres"),
        port=os.getenv("POSTGRES_PORT", "5432"),
    )

conn = get_db_conn()
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
cur.execute("SELECT ticker, ml_prediction, price_prediction FROM signals ORDER BY run_date DESC LIMIT 5")
rows = cur.fetchall()
for sig in rows:
    ml_pred = sig.get("ml_prediction") or {}
    if ml_pred:
        price_pred_temp = sig.get("price_prediction")
        
        # Simulating exactly what app.py does
        if isinstance(price_pred_temp, str):
            try:
                price_pred_temp = json.loads(price_pred_temp)
            except:
                price_pred_temp = {}
        price_pred_temp = price_pred_temp or {}
        
        cp_temp = price_pred_temp.get('current_price', 1)
        day_5_temp = price_pred_temp.get("predictions", {}).get("day_5", {})
        day_5_price_temp = day_5_temp.get("price", cp_temp)
        
        try:
            pred_return = ((float(day_5_price_temp) - float(cp_temp)) / float(cp_temp)) * 100
        except (ValueError, TypeError, ZeroDivisionError) as e:
            pred_return = 0.0
            print("Exception:", e)
        
        print(f"{sig['ticker']}: cp={cp_temp}, d5={day_5_price_temp}, ret={pred_return}")
