import psycopg2
import psycopg2.extras
import os

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

cur.execute("SELECT MAX(run_date) AS max_run_date FROM signals WHERE batch_id IS NOT NULL")
latest_meta = cur.fetchall()
latest_run_date = latest_meta[0]["max_run_date"] if latest_meta else None

cur.execute("SELECT batch_id FROM signals WHERE run_date = %s AND batch_id IS NOT NULL LIMIT 1", (latest_run_date,))
latest_batch = cur.fetchall()[0]["batch_id"]

cur.execute("SELECT * FROM signals WHERE batch_id = %s AND rank IS NOT NULL ORDER BY rank LIMIT 3", (latest_batch,))
signals = cur.fetchall()

for sig in signals:
    print(f"Ticker: {sig['ticker']}")
    
    # ML Swing (5-Day) Prediction from DB
    ml_pred = sig.get("ml_prediction") or {}
    if ml_pred:
        price_pred_temp = sig.get("price_prediction") or {}
        if isinstance(price_pred_temp, str):
            import json
            try:
                price_pred_temp = json.loads(price_pred_temp)
            except:
                price_pred_temp = {}

        cp_temp = price_pred_temp.get('current_price', 1)
        day_5_temp = price_pred_temp.get("predictions", {}).get("day_5", {})
        day_5_price_temp = day_5_temp.get("price", cp_temp)
        
        try:
            pred_return = ((float(day_5_price_temp) - float(cp_temp)) / float(cp_temp)) * 100
        except (ValueError, TypeError, ZeroDivisionError):
            pred_return = 0.0

        ml_signal = ml_pred.get("signal", "N/A")
        ml_conf = ml_pred.get("confidence", "N/A")

        print(f"ML Forecast: {ml_signal} | Return: {pred_return:+.2f}% | Confidence: {ml_conf}")
        print(f"price_prediction present: {bool(sig.get('price_prediction'))}")
        
