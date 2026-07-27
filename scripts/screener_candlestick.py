#!/usr/bin/env python3
"""
Screener Candlestick Pattern BEI
Menganalisis seluruh Ticker Universe untuk mencari pola Candlestick terbaru.
"""
import sys
import os
import argparse
import logging
from datetime import date
from tqdm import tqdm

# Setup logging
logging.basicConfig(level=logging.WARNING, format='%(message)s')
logger = logging.getLogger('screener')

# Ensure we can import from project root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config import get_universe
from data.fetcher_stockbit import get_ohlcv
from agents.candlestick_patterns import detect_candlestick_patterns
from db.models import CandlestickSignal
from db import SessionLocal
import os

def get_db_session():
    return SessionLocal()

def run_screener(top_only=False, save_db=False):
    # Basic ANSI colors without colorama dependency
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    CYAN = '\033[96m'
    BRIGHT = '\033[1m'
    RESET = '\033[0m'

    tickers = get_universe()
    print(f"\n{BRIGHT}{CYAN}=== 🕯️ CANDLESTICK PATTERN SCREENER BEI ==={RESET}")
    print(f"Menganalisis {len(tickers)} Ticker dari Universe...\n")

    bullish_patterns = []
    bearish_patterns = []
    neutral_tickers = []
    failed_tickers = []

    for ticker in tqdm(tickers, desc="Screening Tickers", unit="stock"):
        try:
            # Fetch 1 month data to have enough context for trend & patterns
            df = get_ohlcv(ticker, period="1mo")
            
            if df is None or len(df) < 5:
                failed_tickers.append(ticker)
                continue
                
            patterns = detect_candlestick_patterns(df)
            
            if patterns:
                for p in patterns:
                    sig = p.get("signal", "")
                    # Extract last date
                    last_date = df.index[-1].strftime("%Y-%m-%d") if hasattr(df.index, 'strftime') else str(df.index[-1]).split(' ')[0]
                    
                    data = {
                        "ticker": ticker,
                        "date": last_date,
                        "name": p.get("name", "Unknown"),
                        "win_rate": p.get("win_rate_bei", 0.0) * 100,
                        "direction": sig,
                        "context": p.get("best_context", "-")
                    }
                    
                    if sig in ["BULLISH", "STRONG BULLISH"]:
                        bullish_patterns.append(data)
                    elif sig in ["BEARISH", "STRONG BEARISH"]:
                        bearish_patterns.append(data)
            else:
                neutral_tickers.append(ticker)
                
        except Exception as e:
            failed_tickers.append(ticker)

    # Sort by win rate descending
    bullish_patterns.sort(key=lambda x: x["win_rate"], reverse=True)
    bearish_patterns.sort(key=lambda x: x["win_rate"], reverse=True)

    if save_db:
        print(f"\n{BRIGHT}💾 Menyimpan hasil ke database...{RESET}")
        db = get_db_session()
        today = date.today()
        try:
            # Hapus data hari ini jika sudah ada (upsert logic sederhana)
            db.query(CandlestickSignal).filter(CandlestickSignal.scan_date == today).delete()
            
            all_patterns = bullish_patterns + bearish_patterns
            inserted = 0
            for p in all_patterns:
                signal = CandlestickSignal(
                    scan_date=today,
                    ticker=p["ticker"],
                    pattern_name=p["name"],
                    signal_direction=p["direction"],
                    win_rate=p["win_rate"],
                    context_note=p["context"]
                )
                db.add(signal)
                inserted += 1
            
            db.commit()
            print(f"✅ Berhasil menyimpan {inserted} sinyal pola candlestick untuk hari {today}.")
        except Exception as e:
            db.rollback()
            print(f"{RED}❌ Gagal menyimpan ke DB: {e}{RESET}")
        finally:
            db.close()

    # Output Formatting
    print(f"\n{BRIGHT}{GREEN}🎯 BULLISH REVERSAL / CONTINUATION{RESET}")
    print("-" * 85)
    print(f"{'TICKER':<8} | {'PATTERN':<20} | {'WIN-RATE':<10} | {'CONTEXT'}")
    print("-" * 85)
    if bullish_patterns:
        for p in bullish_patterns:
            print(f"{GREEN}{p['ticker']:<8}{RESET} | {p['name']:<20} | {p['win_rate']:>5.0f}%     | {p['context']}")
    else:
        print("Tidak ada indikasi Bullish yang kuat hari ini.")

    print(f"\n{BRIGHT}{RED}⚠️ BEARISH REVERSAL / CONTINUATION{RESET}")
    print("-" * 85)
    print(f"{'TICKER':<8} | {'PATTERN':<20} | {'WIN-RATE':<10} | {'CONTEXT'}")
    print("-" * 85)
    if bearish_patterns:
        for p in bearish_patterns:
            print(f"{RED}{p['ticker']:<8}{RESET} | {p['name']:<20} | {p['win_rate']:>5.0f}%     | {p['context']}")
    else:
        print("Tidak ada pola Bearish hari ini.")

    print(f"\n{BRIGHT}📊 SUMMARY:{RESET}")
    print(f"- Total Bullish Signals : {GREEN}{len(bullish_patterns)}{RESET}")
    print(f"- Total Bearish Signals : {RED}{len(bearish_patterns)}{RESET}")
    print(f"- No Clear Pattern      : {len(neutral_tickers)}")
    if failed_tickers:
        print(f"- Data Gagal Diambil    : {YELLOW}{len(failed_tickers)}{RESET} tickers")
    print("\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Candlestick Pattern Screener")
    parser.add_argument("--top", action="store_true", help="Hanya tampilkan High Win-Rate")
    parser.add_argument("--save-db", action="store_true", help="Simpan hasil screening ke database")
    args = parser.parse_args()
    
    run_screener(top_only=args.top, save_db=args.save_db)