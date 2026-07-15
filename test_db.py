from sqlalchemy import create_engine, text
engine = create_engine("postgresql://stockuser:stockpassword@localhost:5121/stockagent")
with engine.connect() as conn:
    print(conn.execute(text("SELECT result, count(*) FROM performance GROUP BY result")).fetchall())
