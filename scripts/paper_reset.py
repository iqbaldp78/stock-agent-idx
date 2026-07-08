"""Reset paper trading tables."""
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from config import DATABASE_URL

engine = create_engine(DATABASE_URL, isolation_level='AUTOCOMMIT')
Session = sessionmaker(bind=engine)
session = Session()
try:
    session.execute(text('TRUNCATE paper_trades, paper_wallet RESTART IDENTITY CASCADE'))
    session.commit()
    print('Paper trading reset complete')
except Exception as e:
    print('err:', type(e).__name__, e)
    session.rollback()
session.close()
