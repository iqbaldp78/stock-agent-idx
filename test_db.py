import os
import psycopg2
import psycopg2.extras
import json

def get_db_conn():
    return psycopg2.connect(
        dbname=os.getenv("POSTGRES_DB", "stockagent"),
        user=os.getenv("POSTGRES_USER", "stockuser"),
        password=os.getenv("POSTGRES_PASSWORD", "stockpassword"),
        host=os.getenv("POSTGRES_HOST", "127.0.0.1"), # Using localhost for script
        port=os.getenv("POSTGRES_PORT", "5432"),
    )

def main():
    try:
        conn = get_db_conn()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT ticker, run_date, fair_value FROM signals ORDER BY run_date DESC LIMIT 5")
        rows = cur.fetchall()
        for row in rows:
            print(f"Ticker: {row['ticker']}, Date: {row['run_date']}")
            print(f"Fair Value Type: {type(row['fair_value'])}")
            print(f"Fair Value: {row['fair_value']}")
            print("---")
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
