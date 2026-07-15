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
cur.execute("SELECT ticker, ml_prediction, price_prediction FROM signals ORDER BY run_date DESC LIMIT 1")
sig = cur.fetchall()[0]
print("ticker:", sig["ticker"])
print("ml_prediction:", sig["ml_prediction"])
if sig["price_prediction"]:
    print("price_prediction keys:", sig["price_prediction"].keys())
    print("current_price:", sig["price_prediction"].get("current_price"))
    print("predictions:", sig["price_prediction"].get("predictions"))
