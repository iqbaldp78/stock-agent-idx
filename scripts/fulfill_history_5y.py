#!/usr/bin/env python3
"""
scripts/fulfill_history_5y.py
==============================
Script untuk mendeteksi dan melengkapi (fulfill) data OHLCV & Bandarmologi
(broker accumulation) selama 5 tahun ke belakang (atau N tahun) untuk semua
ticker aktif di database universe.

Fitur:
1. Scanning database untuk mengecek kelengkapan data (min date & missing dates)
   setiap ticker aktif di universe.
2. Memfilter secara otomatis ticker yang datanya < 5 tahun ke belakang.
3. Melakukan backfill OHLCV via Stockbit API.
4. Melakukan backfill Bandarmologi via Stockbit API (memperhitungkan IPO limit: 15 hari berturut-turut kosong).
5. Opsi CLI: --years, --tickers, --dry-run, --delay-min, --delay-max.

Usage:
  # Scan & Fulfill semua ticker aktif untuk 5 tahun ke belakang
  python scripts/fulfill_history_5y.py

  # Dry-run: hanya scan & laporkan status tanpa download/save
  python scripts/fulfill_history_5y.py --dry-run

  # Ticker tertentu & 3 tahun ke belakang
  python scripts/fulfill_history_5y.py --tickers BBCA TLKM --years 3
"""

import argparse
import logging
import os
import random
import sys
import time
from datetime import date, timedelta

# ── Path setup ─────────────────────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import dotenv
dotenv.load_dotenv()

from sqlalchemy import text
from db import SessionLocal
from db.models import Universe, OhlcvPrice, BrokerAccumulation
from db.cache import get_cached_broker_daily, save_broker_daily, _weekdays_between
from data.fetcher_stockbit import get_ohlcv_range
from scripts.backfill_bandarmology import backfill_ticker

# ── Logging Setup ───────────────────────────────────────────────────────────
os.makedirs("logs", exist_ok=True)
stream_handler = logging.StreamHandler(sys.stdout)
file_handler = logging.FileHandler("logs/fulfill_history_5y.log", encoding="utf-8")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[stream_handler, file_handler],
)
logger = logging.getLogger("fulfill_5y")


def get_active_tickers(filter_tickers: list = None) -> list:
    """Ambil list ticker aktif dari tabel universe."""
    db = SessionLocal()
    try:
        query = db.query(Universe.ticker).filter(Universe.active == True)
        if filter_tickers:
            filter_tickers_upper = [t.upper() for t in filter_tickers]
            query = query.filter(Universe.ticker.in_(filter_tickers_upper))
        rows = query.order_by(Universe.ticker).all()
        return [r.ticker for r in rows]
    finally:
        db.close()


def scan_ticker_data_status(ticker: str, target_start: date, today: date) -> dict:
    """
    Scan status data OHLCV & Bandarmologi untuk satu ticker.
    Mengembalikan dict berisi min_date, missing_count, dan flag needs_fulfill.
    """
    db = SessionLocal()
    try:
        # Scan OHLCV
        ohlcv_row = db.execute(
            text("""
                SELECT MIN(trade_date), COUNT(DISTINCT trade_date)
                FROM ohlcv_prices
                WHERE ticker = :ticker AND trade_date >= :target_start
            """),
            {"ticker": ticker, "target_start": target_start}
        ).fetchone()

        min_ohlcv_date = ohlcv_row[0] if ohlcv_row else None
        count_ohlcv = ohlcv_row[1] if ohlcv_row else 0

        # Scan Bandarmologi
        bandar_row = db.execute(
            text("""
                SELECT MIN(trade_date), COUNT(DISTINCT trade_date)
                FROM broker_accumulation
                WHERE ticker = :ticker AND trade_date >= :target_start
            """),
            {"ticker": ticker, "target_start": target_start}
        ).fetchone()

        min_bandar_date = bandar_row[0] if bandar_row else None
        count_bandar = bandar_row[1] if bandar_row else 0

        # Target expected trading days
        expected_days = len(_weekdays_between(target_start, today))

        needs_ohlcv = (min_ohlcv_date is None) or (min_ohlcv_date > target_start + timedelta(days=30)) or (count_ohlcv < expected_days * 0.85)
        needs_bandarmology = (min_bandar_date is None) or (min_bandar_date > target_start + timedelta(days=30)) or (count_bandar < expected_days * 0.85)

        return {
            "ticker": ticker,
            "min_ohlcv_date": min_ohlcv_date,
            "count_ohlcv": count_ohlcv,
            "min_bandar_date": min_bandar_date,
            "count_bandar": count_bandar,
            "expected_days": expected_days,
            "needs_ohlcv": needs_ohlcv,
            "needs_bandarmology": needs_bandarmology,
            "needs_fulfill": needs_ohlcv or needs_bandarmology
        }
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(
        description="Fullfill OHLCV dan Bandarmologi 5 Tahun ke Belakang untuk Ticker Universe."
    )
    parser.add_argument(
        "--years",
        type=int,
        default=5,
        help="Target berapa tahun ke belakang (default: 5)",
    )
    parser.add_argument(
        "--tickers",
        nargs="+",
        metavar="TICKER",
        help="Target ticker tertentu (opsional, default: semua ticker aktif di universe)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Hanya scan & laporkan ticker yang perlu fulfill tanpa menulis ke DB",
    )
    parser.add_argument(
        "--delay-min",
        type=float,
        default=0.2,
        help="Delay minimal per request dalam detik (default: 0.2)",
    )
    parser.add_argument(
        "--delay-max",
        type=float,
        default=0.5,
        help="Delay maksimal per request dalam detik (default: 0.5)",
    )

    args = parser.parse_args()

    today = date.today()
    target_start = today - timedelta(days=args.years * 365)

    logger.info("=" * 70)
    logger.info(f"STARTING 5-YEAR DATA FULFILLMENT SCRIPT")
    logger.info(f"Target Period : {target_start.isoformat()} to {today.isoformat()} ({args.years} years)")
    logger.info(f"Dry Run Mode  : {args.dry_run}")
    logger.info("=" * 70)

    # 1. Scope Tickers
    tickers = get_active_tickers(args.tickers)
    if not tickers:
        logger.error("Tidak ada ticker aktif yang ditemukan di universe!")
        sys.exit(1)

    logger.info(f"Total Ticker Active di-scan: {len(tickers)}")

    # 2. Scan Phase
    scan_results = []
    to_fulfill = []

    for t in tickers:
        status = scan_ticker_data_status(t, target_start, today)
        scan_results.append(status)
        if status["needs_fulfill"]:
            to_fulfill.append(status)

    logger.info("-" * 70)
    logger.info(f"SCAN SUMMARY: {len(to_fulfill)} / {len(tickers)} ticker memerlukan fulfillment data.")
    logger.info("-" * 70)

    print(f"\n{'TICKER':<8} | {'OHLCV MIN DATE':<14} | {'OHLCV ROWS':<10} | {'BANDAR MIN DATE':<15} | {'BANDAR ROWS':<11} | {'ACTION REQUIRED'}", flush=True)
    print("-" * 90, flush=True)
    for s in scan_results:
        min_o = s['min_ohlcv_date'].isoformat() if s['min_ohlcv_date'] else 'NO DATA'
        min_b = s['min_bandar_date'].isoformat() if s['min_bandar_date'] else 'NO DATA'
        actions = []
        if s['needs_ohlcv']:
            actions.append("OHLCV")
        if s['needs_bandarmology']:
            actions.append("BANDARMOLOGY")
        action_str = " + ".join(actions) if actions else "OK (LENGKAP)"
        print(f"{s['ticker']:<8} | {min_o:<14} | {s['count_ohlcv']:<10} | {min_b:<15} | {s['count_bandar']:<11} | {action_str}", flush=True)
    print("-" * 90 + "\n", flush=True)

    if args.dry_run:
        logger.info("[DRY RUN COMPLETE] Tidak ada data yang diunduh atau disimpan.")
        sys.exit(0)

    if not to_fulfill:
        logger.info("Semua ticker sudah memiliki data lengkap untuk 5 tahun ke belakang! Selesai.")
        sys.exit(0)

    # 3. Fulfillment Phase
    total_fulfilled = 0
    max_days = args.years * 365

    for idx, item in enumerate(to_fulfill, 1):
        ticker = item["ticker"]
        logger.info(f"\n[{idx}/{len(to_fulfill)}] Processing Fulfillment for {ticker}...")

        # 3a. OHLCV Fulfill
        if item["needs_ohlcv"]:
            logger.info(f"  -> Fetching OHLCV ({target_start} .. {today}) via Stockbit API...")
            try:
                df_ohlcv = get_ohlcv_range(ticker, target_start.isoformat(), today.isoformat())
                ohlcv_count = len(df_ohlcv) if df_ohlcv is not None else 0
                logger.info(f"  -> OHLCV Done: {ohlcv_count} rows retrieved/cached for {ticker}.")
            except Exception as e:
                logger.error(f"  -> OHLCV Error for {ticker}: {e}")

        # 3b. Bandarmologi Fulfill
        if item["needs_bandarmology"]:
            logger.info(f"  -> Fetching Bandarmologi (max {max_days} days back) via Stockbit API...")
            try:
                stats = backfill_ticker(
                    ticker=ticker,
                    start_date=today,
                    max_days=max_days,
                    dry_run=False
                )
                logger.info(
                    f"  -> Bandarmologi Done for {ticker}: "
                    f"fetched={stats['fetched']}, skipped={stats['skipped']}, "
                    f"empty={stats['empty']}, api_errors={stats['api_errors']}, "
                    f"stopped_at={stats.get('stopped_at', 'end of range')}"
                )
            except Exception as e:
                logger.error(f"  -> Bandarmologi Error for {ticker}: {e}")

        total_fulfilled += 1
        time.sleep(random.uniform(args.delay_min, args.delay_max))

    logger.info("=" * 70)
    logger.info(f"FULFILLMENT PROCESS COMPLETED: {total_fulfilled} tickers processed.")
    logger.info("=" * 70)


if __name__ == "__main__":
    main()
