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
print("latest_run_date:", type(latest_run_date), repr(latest_run_date))

cur.execute("SELECT run_date FROM signals LIMIT 1")
sig = cur.fetchall()[0]
print("run_date:", type(sig["run_date"]), repr(sig["run_date"]))
