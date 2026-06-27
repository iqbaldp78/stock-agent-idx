from db import SessionLocal
from db.models import Signal

db = SessionLocal()
tickers = db.query(Signal.ticker).distinct().all()
print("Tickers in Signal table:", [t[0] for t in tickers])
