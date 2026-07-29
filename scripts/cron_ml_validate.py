#!/usr/bin/env python3
import sys, os, logging
from datetime import date
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db import SessionLocal
from db.models import MlPredictionLog
from scripts.train_day1_model import get_universe_tickers, fetch_ohlcv

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
                
            for log in logs:
                # Validasi T+1
                if log.horizon == "1d":
                    # Cari close price setelah trade_date (atau harga hari ini jika mau dipakai validasi akhir hari)
                    # Jika data cron diambil pagi, maka untuk memprediksi hari INI tutupnya berapa, kita cek harga close hari INI (T=0 dibanding pagi)
                    # Tergantung definisi: 1D = penutupan hari ini, atau 1D = penutupan besok. 
                    # Jika 1D = penutupan HARI INI (untuk ODT), pakai >= trade_date.
                    future_data = raw.loc[raw.index >= str(log.trade_date)]
                    if len(future_data) >= 1:
                        target_close = float(future_data['Close'].iloc[0])
                        base_close = float(raw.loc[raw.index <= str(log.trade_date)]['Close'].iloc[-1])
                        actual_return = ((target_close - base_close) / base_close) * 100
                        
                        log.actual_close_price = target_close
                        log.actual_return_pct = actual_return
                        # Kapan model disebut benar?
                        # Karena output ML skrg biner probability (0 s/d 1), threshold adalah 0.5 (50%)
                        # Jika pred > 0.5 (Prediksi NAIK), maka harus actual_return > 0 (Beneran naik)
                        # Jika pred < 0.5 (Prediksi TURUN), maka harus actual_return <= 0 (Beneran turun/stagnan)
                        pred_val = float(log.pred_return_pct) if log.pred_return_pct is not None else 0.0
                        if pred_val >= 0.5:
                            log.is_correct = bool(actual_return > 0)
                        else:
                            log.is_correct = bool(actual_return <= 0)
                        count += 1
                        
                # Logika horizon lain (3d, 5d, 7d) menyesuaikan index
                elif log.horizon in ["3d", "5d", "7d"]:
                    days = int(log.horizon[0])
                    # Menggunakan > (strictly greater) agar hanya menghitung hari bursa (open market) SETELAH trade_date.
                    # Jika data cron diambil pagi, trade_date sudah open market. Jadi hari ke-1 adalah hari bursa *besoknya*, dst.
                    future_data = raw.loc[raw.index > str(log.trade_date)]
                    if len(future_data) >= days:
                        target_close = float(future_data['Close'].iloc[days-1])
                        base_close = float(raw.loc[raw.index <= str(log.trade_date)]['Close'].iloc[-1])
                        actual_return = ((target_close - base_close) / base_close) * 100
                        
                        log.actual_close_price = target_close
                        log.actual_return_pct = actual_return
                        
                        pred_val = float(log.pred_return_pct) if log.pred_return_pct is not None else 0.0
                        if pred_val >= 0.5:
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
