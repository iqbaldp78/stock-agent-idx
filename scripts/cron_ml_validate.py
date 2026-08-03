#!/usr/bin/env python3
import sys, os, logging
from datetime import date, datetime
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db import SessionLocal
from db.models import MlPredictionLog
from scripts.train_day1_model import get_universe_tickers, fetch_ohlcv
from models.multiday_predictor import MultiDayPredictor

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

def get_db_session():
    return SessionLocal()

def main():
    session = get_db_session()
    unvalidated = session.query(MlPredictionLog).filter(MlPredictionLog.actual_close_price == None).all()
    logging.info(f"Mulai Validasi Malam ML. Ada {len(unvalidated)} log yang perlu divalidasi.")
    
    # Kelompokkan by ticker
    by_ticker = {}
    for log in unvalidated:
        if log.ticker not in by_ticker:
            by_ticker[log.ticker] = []
        by_ticker[log.ticker].append(log)

    count = 0
    for ticker, logs in by_ticker.items():
        try:
            raw = fetch_ohlcv(ticker, "2m")
            if raw.empty:
                continue

            # FIXED (Fase 0.3): pakai threshold hasil training per ticker/horizon,
            # bukan cutoff hardcode 0.55, supaya validasi live konsisten dengan training.
            predictor = MultiDayPredictor(ticker=ticker)
                
            for log in logs:
                # Validasi T+1
                if log.horizon == "1d":
                    # base_close = harga penutupan SEBELUM trade_date (strictly less than)
                    # target_close = harga penutupan PADA trade_date
                    future_data = raw.loc[raw.index >= str(log.trade_date)]
                    past_data = raw.loc[raw.index < str(log.trade_date)]
                    if len(future_data) >= 1 and len(past_data) >= 1:
                        target_close = float(future_data['Close'].iloc[0])
                        base_close = float(past_data['Close'].iloc[-1])
                        actual_return = ((target_close - base_close) / base_close) * 100
                        
                        log.actual_close_price = target_close
                        log.actual_return_pct = actual_return
                        log.validated_at = datetime.now()
                        pred_val = float(log.pred_return_pct) if log.pred_return_pct is not None else 0.0
                        buy_threshold = predictor.thresholds.get(log.horizon, 0.55)
                        if pred_val >= buy_threshold:
                            log.is_correct = bool(actual_return > 0)
                        else:
                            log.is_correct = bool(actual_return <= 0)
                        count += 1
                        
                # Logika horizon lain (3d, 5d, 7d) menyesuaikan index
                elif log.horizon in ["3d", "5d", "7d"]:
                    days = int(log.horizon[0])
                    future_data = raw.loc[raw.index > str(log.trade_date)]
                    past_data = raw.loc[raw.index < str(log.trade_date)]
                    if len(future_data) >= days and len(past_data) >= 1:
                        target_close = float(future_data['Close'].iloc[days-1])
                        base_close = float(past_data['Close'].iloc[-1])
                        actual_return = ((target_close - base_close) / base_close) * 100
                        
                        log.actual_close_price = target_close
                        log.actual_return_pct = actual_return
                        log.validated_at = datetime.now()
                        
                        pred_val = float(log.pred_return_pct) if log.pred_return_pct is not None else 0.0
                        buy_threshold = predictor.thresholds.get(log.horizon, 0.55)
                        if pred_val >= buy_threshold:
                            log.is_correct = bool(actual_return > 0)
                        else:
                            log.is_correct = bool(actual_return <= 0)
                        count += 1
                        
        except Exception as e:
            logging.error(f"Error {ticker}: {e}")
            
    session.commit()
    session.close()
    logging.info(f"Selesai Validasi Malam ML. {count} log divalidasi.")

if __name__ == "__main__":
    main()
