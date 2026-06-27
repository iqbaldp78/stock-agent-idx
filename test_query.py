from db import SessionLocal
from db.models import Signal

db = SessionLocal()
ticker = 'MBMA'
latest_signal = (
    db.query(Signal)
    .filter(Signal.ticker == ticker.upper())
    .order_by(Signal.run_date.desc())
    .first()
)
print(f"ID returned: {latest_signal.id if latest_signal else None}")
print(f"bandar_1m: {latest_signal.bandar_avg_1m if latest_signal else None}")
