import psycopg2
import psycopg2.extras
import json

conn = psycopg2.connect("dbname=stockagent user=postgres password=stockpassword host=postgres port=5432")
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
cur.execute("SELECT ticker, broker_true_costs FROM signals ORDER BY run_date DESC LIMIT 1")
row = cur.fetchone()
print(type(row['broker_true_costs']))
print(row['broker_true_costs'])
