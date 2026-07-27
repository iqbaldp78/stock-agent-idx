#!/usr/bin/env python3
import sys
import os
import argparse
import logging
from datetime import date, datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db import SessionLocal
from db.models import MlPredictionLog
from models.multiday_predictor import MultiDayPredictor
from scripts.train_day1_model import get_universe_tickers, fetch_ohlcv
from data.ml_features import prepare_training_data

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


def get_db_session():
    return SessionLocal()


def get_next_trading_day(ref_date: date = None) -> date:
    """
    Hitung tanggal perdagangan berikutnya (Next Trading Day):
    - Jika ref_date hari Jumat (4), Sabtu (5), atau Minggu (6) -> Senin depan.
    - Jika ref_date hari Senin (0) s/d Kamis (3) -> Besok (ref_date + 1 hari).
    """
    if ref_date is None:
        ref_date = date.today()
    weekday = ref_date.weekday()
    if weekday == 4:      # Friday
        return ref_date + timedelta(days=3)
    elif weekday == 5:    # Saturday
        return ref_date + timedelta(days=2)
    elif weekday == 6:    # Sunday
        return ref_date + timedelta(days=1)
    else:                 # Mon-Thu
        return ref_date + timedelta(days=1)


def run_ml_prediction(target_date: date = None, tickers: list = None) -> int:
    """
    Jalankan prediksi ML (MultiDayPredictor) untuk tickers dan simpan hasilnya
    ke database ml_prediction_log dengan target_date.
    """
    if target_date is None:
        target_date = get_next_trading_day()

    if isinstance(target_date, str):
        target_date = date.fromisoformat(target_date)

    if not tickers:
        tickers = get_universe_tickers()

    session = get_db_session()
    logging.info(f"Mulai Prediksi ML untuk {len(tickers)} saham pada target trade_date: {target_date}")
    count = 0

    for ticker in tickers:
        try:
            raw = fetch_ohlcv(ticker, "2y")
            if raw.empty or len(raw) < 50:
                continue

            X, _ = prepare_training_data(raw, ticker=ticker)
            if X.empty:
                continue

            latest_feature = X.iloc[-1:]
            last_close = float(raw['Close'].iloc[-1])
            predictor = MultiDayPredictor(ticker=ticker)
            predictions = predictor.predict(latest_feature)

            for horizon, pred_pct in predictions.items():
                # pred_pct bertipe float probabilitas [0.0, 1.0] (atau persentase > 1)
                prob_val = float(pred_pct)
                if prob_val > 1.0:
                    prob_val = prob_val / 100.0

                # Estimasi target price sederhana berdasarkan horizon & probabilitas
                target_pct = (prob_val - 0.50) * 0.05
                pred_price = last_close * (1 + target_pct)

                existing = session.query(MlPredictionLog).filter_by(
                    trade_date=target_date, ticker=ticker, horizon=horizon
                ).first()

                if not existing:
                    new_log = MlPredictionLog(
                        trade_date=target_date,
                        ticker=ticker,
                        horizon=horizon,
                        pred_return_pct=prob_val,
                        pred_price=pred_price,
                        predicted_direction="NAIK" if prob_val >= 0.50 else "TURUN"
                    )
                    session.add(new_log)
                else:
                    existing.pred_return_pct = prob_val
                    existing.pred_price = pred_price
                    existing.predicted_direction = "NAIK" if prob_val >= 0.50 else "TURUN"

            session.commit()
            count += 1
            logging.info(f"✅ {ticker} tersimpan untuk target {target_date}")
        except Exception as e:
            session.rollback()
            logging.error(f"Error {ticker}: {e}")

    session.close()
    logging.info(f"Selesai Prediksi ML. {count} ticker tersimpan untuk {target_date}.")
    return count


def main():
    parser = argparse.ArgumentParser(description="Cron ML Prediction Script")
    parser.add_argument("--target-date", type=str, default=None, help="Target trade date (YYYY-MM-DD)")
    parser.add_argument("--tickers", type=str, default=None, help="Comma separated tickers or 'ALL'")
    args = parser.parse_args()

    target_dt = date.fromisoformat(args.target_date) if args.target_date else get_next_trading_day()

    tickers_list = None
    if args.tickers and args.tickers.upper() != "ALL":
        tickers_list = [t.strip().upper() for t in args.tickers.split(",") if t.strip()]

    run_ml_prediction(target_date=target_dt, tickers=tickers_list)


if __name__ == "__main__":
    main()
