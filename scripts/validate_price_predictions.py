#!/usr/bin/env python3
"""
Validasi Akurasi Prediksi Harga DAY+1, +3, +5, +7.
Mengambil prediksi dari tabel signals dan mencocokkannya dengan
harga aktual (close price) dari tabel ohlcv_prices pada tanggal yang sesuai.
"""
import os
import sys
import logging
from datetime import timedelta
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db import SessionLocal
from sqlalchemy import text

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

def fetch_predictions_and_actuals():
    db = SessionLocal()
    try:
        # Get all signals that have price_predictions
        query = text("""
            SELECT 
                s.id, s.run_date, s.ticker,
                s.price_prediction
            FROM signals s
            WHERE s.price_prediction IS NOT NULL
            ORDER BY s.run_date DESC
        """)
        signals = db.execute(query).fetchall()
        
        if not signals:
            logger.warning("Tidak ada prediksi yang tersimpan di database.")
            return

        results = []
        
        for sig in signals:
            sig_id, run_date, ticker, pred_json = sig
            
            if not isinstance(pred_json, dict) or "predictions" not in pred_json:
                continue
                
            preds = pred_json.get("predictions", {})
            current_price = pred_json.get("current_price")
            
            # Fetch actual prices for the next 10 days to cover trading days
            ohlcv_query = text("""
                SELECT trade_date, close 
                FROM ohlcv_prices 
                WHERE ticker = :ticker AND trade_date > :run_date
                ORDER BY trade_date ASC LIMIT 10
            """)
            actuals = db.execute(ohlcv_query, {"ticker": ticker, "run_date": run_date}).fetchall()
            
            if not actuals:
                continue
                
            actual_prices = [row.close for row in actuals]
            actual_dates = [row.trade_date for row in actuals]
            
            for horizon, days_idx in [("day_1", 0), ("day_3", 2), ("day_5", 4), ("day_7", 6)]:
                if horizon in preds and len(actual_prices) > days_idx:
                    pred_data = preds[horizon]
                    pred_price = float(pred_data.get("price", 0))
                    # Rentang harga prediksi, default ke +/- 2% jika range tidak ada
                    pred_range = pred_data.get("price_range", [pred_price * 0.98, pred_price * 1.02])
                    
                    actual_price = float(actual_prices[days_idx])
                    actual_date = actual_dates[days_idx]
                    
                    # Cek arah prediksi (naik atau turun dari harga run_date)
                    pred_direction = 1 if pred_price > current_price else -1 if pred_price < current_price else 0
                    actual_direction = 1 if actual_price > current_price else -1 if actual_price < current_price else 0
                    
                    is_direction_correct = (pred_direction == actual_direction) and pred_direction != 0
                    is_hit_range = pred_range[0] <= actual_price <= pred_range[1]
                    error_pct = abs((actual_price - pred_price) / actual_price) * 100
                    
                    results.append({
                        "ticker": ticker,
                        "run_date": run_date.isoformat(),
                        "horizon": horizon,
                        "actual_date": actual_date.isoformat(),
                        "base_price": float(current_price),
                        "pred_price": pred_price,
                        "actual_price": actual_price,
                        "error_pct": error_pct,
                        "is_dir_correct": is_direction_correct,
                        "is_hit_range": is_hit_range
                    })
        
        return pd.DataFrame(results)
    finally:
        db.close()

def print_summary(df):
    if df is None or df.empty:
        logger.info("Belum ada data aktual yang cukup untuk divalidasi.")
        return
        
    print("\n" + "="*60)
    print("📊 VALIDASI AKURASI PREDIKSI HARGA (Berdasarkan History Database)")
    print("="*60)
    
    total_preds = len(df)
    print(f"Total Prediksi Divalidasi : {total_preds}")
    print(f"Periode                   : {df['run_date'].min()} s/d {df['run_date'].max()}\n")
    
    print("📈 Metrik per Horizon (Jarak Hari):")
    print("-" * 60)
    print(f"{'Horizon':<10} | {'Jumlah':<6} | {'Akurasi Arah':<15} | {'Masuk Range':<15} | {'Error (MAE)':<10}")
    print("-" * 60)
    
    for horizon in ["day_1", "day_3", "day_5", "day_7"]:
        subset = df[df["horizon"] == horizon]
        if subset.empty:
            continue
            
        count = len(subset)
        dir_acc = subset["is_dir_correct"].mean() * 100
        range_acc = subset["is_hit_range"].mean() * 100
        mae = subset["error_pct"].mean()
        
        print(f"{horizon.upper():<10} | {count:<6} | {dir_acc:>6.1f}%          | {range_acc:>6.1f}%          | {mae:>5.2f}%")
        
    print("="*60)
    
    # Show worst and best predictions as examples
    print("\n🔍 Contoh Prediksi Paling Akurat (Error Terendah):")
    best = df.nsmallest(3, "error_pct")
    for _, row in best.iterrows():
        print(f"  [{row['run_date']}] {row['ticker']} {row['horizon'].upper()}: Prediksi {row['pred_price']} | Aktual {row['actual_price']} (Err {row['error_pct']:.2f}%)")

if __name__ == "__main__":
    logger.info("Mengambil dan menghitung akurasi prediksi historis...")
    df = fetch_predictions_and_actuals()
    print_summary(df)
