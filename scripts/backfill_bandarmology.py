#!/usr/bin/env python3
"""
scripts/backfill_bandarmology.py
=================================
Scrape semua data broker_daily (bandarmologi) dari Stockbit API untuk semua
ticker aktif di tabel universe, mundur ke belakang sampai API tidak lagi
punya data.

Tujuan: Feed ML model dengan historical broker_accumulation data yang akurat
per tanggal agar backtest bandarmologi bisa dilakukan pada setiap tanggal
historis (rolling 7d/30d bandar features di prepare_training_data).

Usage:
  # Default: semua ticker, sejauh mungkin ke belakang
  python scripts/backfill_bandarmology.py

  # Hanya ticker tertentu
  python scripts/backfill_bandarmology.py --tickers BBCA TLKM ANTM

  # Mulai dari tanggal tertentu (override default "dari kemarin")
  python scripts/backfill_bandarmology.py --start-date 2025-01-01

  # Batas mundur maksimal (safety net, default: tidak terbatas)
  python scripts/backfill_bandarmology.py --max-days 365

  # Dry-run: tidak simpan ke DB, hanya print apa yang akan dilakukan
  python scripts/backfill_bandarmology.py --dry-run
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

# ── Logging ─────────────────────────────────────────────────────────────────
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("logs/backfill_bandarmology.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)

# ── Constants ────────────────────────────────────────────────────────────────
# Berapa hari berturut-turut empty/error sampai kita stop backfill untuk ticker tsb.
# Di-set 15 agar tidak false-stop saat libur panjang (Lebaran IDX ~5-8 hari kerja,
# plus buffer untuk long weekend & cuti bersama tambahan).
CONSECUTIVE_EMPTY_STOP = 15
# Delay default antar request (detik)
DELAY_MIN = 0.3
DELAY_MAX = 0.7


# ════════════════════════════════════════════════════════════════════════════
# Core logic
# ════════════════════════════════════════════════════════════════════════════

def _get_active_tickers() -> list:
    """Ambil semua ticker aktif dari tabel universe."""
    from db import SessionLocal
    from db.models import Universe

    db = SessionLocal()
    try:
        rows = db.query(Universe.ticker).filter(Universe.active == True).all()
        return [r.ticker for r in rows]
    finally:
        db.close()


def _is_weekday(d: date) -> bool:
    return d.weekday() < 5  # Mon=0 ... Fri=4


def _iter_trading_days(start: date):
    """
    Generator: yield tanggal trading mundur dari `start` (inclusive),
    skip Sabtu & Minggu.
    """
    current = start
    while True:
        if _is_weekday(current):
            yield current
        current -= timedelta(days=1)


# Sentinel untuk membedakan "kosong" vs "exception"
_EMPTY = object()
_API_ERROR = object()


def _fetch_day(ticker: str, date_str: str):
    """
    Fetch broker daily dari API (no save).
    Return:
        dict       -> data valid
        _EMPTY     -> API sukses tapi data kosong (hari libur / suspend / tidak ada transaksi)
        _API_ERROR -> exception / HTTP error
    """
    from data.fetcher_stockbit import _fetch_broker_daily_api

    try:
        day_data = _fetch_broker_daily_api(ticker, date_str)
        if not day_data:
            return _EMPTY
        # Stockbit return 200 OK tapi buy & sell kosong -> tidak ada data untuk hari ini
        if not day_data.get("buy") and not day_data.get("sell"):
            return _EMPTY
        return day_data
    except Exception as e:
        logger.debug(f"  [{ticker}] {date_str} api error: {type(e).__name__}: {e}")
        return _API_ERROR


def backfill_ticker(
    ticker: str,
    start_date: date,
    max_days=None,
    dry_run: bool = False,
) -> dict:
    """
    Backfill broker_daily untuk satu ticker, mundur dari `start_date`.

    Returns:
        dict dengan keys: fetched, skipped, empty, api_errors, stopped_at
    """
    from db.cache import get_cached_broker_daily, save_broker_daily

    stats = {"fetched": 0, "skipped": 0, "empty": 0, "api_errors": 0, "stopped_at": None}
    consecutive_empty = 0
    days_checked = 0

    for trade_date in _iter_trading_days(start_date):
        date_str = trade_date.isoformat()

        # Safety: batas max hari
        if max_days is not None and days_checked >= max_days:
            stats["stopped_at"] = f"{date_str} (max_days={max_days} reached)"
            break

        days_checked += 1

        # ── Cache-first: skip jika sudah ada di DB ──────────────────────
        cached = get_cached_broker_daily(ticker, date_str)
        if cached is not None:
            if cached.get("buy") or cached.get("sell"):
                stats["skipped"] += 1
                consecutive_empty = 0
                time.sleep(0.01)
                continue
            # Cache kosong -> treated as empty
            consecutive_empty += 1
            stats["empty"] += 1
            if consecutive_empty >= CONSECUTIVE_EMPTY_STOP:
                stats["stopped_at"] = (
                    f"{date_str} ({consecutive_empty} consecutive empty)"
                )
                break
            continue

        # ── Fetch dari API ───────────────────────────────────────────────
        if not dry_run:
            result = _fetch_day(ticker, date_str)
        else:
            # Dry-run: simulasi — data > 2 tahun anggap kosong
            cutoff = date.today() - timedelta(days=730)
            result = (
                {"buy": [{"broker": "DRY"}], "sell": [], "foreign_net": 0}
                if trade_date > cutoff else _EMPTY
            )

        if result is _EMPTY:
            consecutive_empty += 1
            stats["empty"] += 1
            logger.debug(
                f"  [{ticker}] {date_str} -> empty (hari libur/suspend/no data) "
                f"[consecutive={consecutive_empty}]"
            )
            if consecutive_empty >= CONSECUTIVE_EMPTY_STOP:
                stats["stopped_at"] = (
                    f"{date_str} ({consecutive_empty} consecutive empty)"
                )
                break

        elif result is _API_ERROR:
            consecutive_empty += 1
            stats["api_errors"] += 1
            logger.warning(f"  [{ticker}] {date_str} -> API error [consecutive={consecutive_empty}]")
            if consecutive_empty >= CONSECUTIVE_EMPTY_STOP:
                stats["stopped_at"] = (
                    f"{date_str} ({consecutive_empty} consecutive empty/error)"
                )
                break

        else:
            # Valid data dict
            day_data = result
            consecutive_empty = 0
            if not dry_run:
                try:
                    save_broker_daily(ticker, date_str, day_data)
                    stats["fetched"] += 1
                    logger.debug(
                        f"  [{ticker}] {date_str} -> saved "
                        f"({len(day_data.get('buy', []))} buy / "
                        f"{len(day_data.get('sell', []))} sell brokers)"
                    )
                except Exception as e:
                    logger.warning(f"  [{ticker}] {date_str} save error: {e}")
                    stats["api_errors"] += 1
            else:
                stats["fetched"] += 1

        # ── Rate limiting ────────────────────────────────────────────────
        if not dry_run:
            time.sleep(random.uniform(DELAY_MIN, DELAY_MAX))

    return stats


def backfill_new_ticker(
    ticker: str,
    max_days: int = 365,
    dry_run: bool = False,
) -> dict:
    """
    Backfill data bandarmologi untuk satu ticker baru yang baru ditambahkan
    ke universe. Cocok dipanggil dari endpoint / skrip lain.

    Contoh:
        from scripts.backfill_bandarmology import backfill_new_ticker
        backfill_new_ticker("NEWT")

    Args:
        ticker:   Kode saham (e.g. "BBCA")
        max_days: Batas mundur maksimal (default 365 hari)
        dry_run:  Jika True, tidak simpan ke DB

    Returns:
        dict dengan stats: fetched, skipped, errors, stopped_at
    """
    logger.info(
        f"[backfill_new_ticker] Starting backfill for {ticker} (max_days={max_days})"
    )
    start = date.today() - timedelta(days=1)
    stats = backfill_ticker(ticker, start, max_days=max_days, dry_run=dry_run)
    logger.info(
        f"[backfill_new_ticker] {ticker} done -- "
        f"fetched={stats['fetched']} skipped={stats['skipped']} "
        f"errors={stats['errors']} stopped_at={stats.get('stopped_at', 'end of range')}"
    )
    return stats


# ════════════════════════════════════════════════════════════════════════════
# CLI Entry Point
# ════════════════════════════════════════════════════════════════════════════

def main():
    # Override global delay constants (declare at top to avoid SyntaxError)
    global DELAY_MIN, DELAY_MAX

    parser = argparse.ArgumentParser(
        description=(
            "Backfill data broker_daily (bandarmologi) dari Stockbit "
            "untuk semua ticker universe."
        )
    )
    parser.add_argument(
        "--tickers",
        nargs="+",
        metavar="TICKER",
        help="List ticker yang mau di-backfill (default: semua ticker aktif di universe)",
    )
    parser.add_argument(
        "--start-date",
        metavar="YYYY-MM-DD",
        help="Tanggal mulai mundur (default: kemarin)",
    )
    parser.add_argument(
        "--max-days",
        type=int,
        default=None,
        metavar="N",
        help="Batas maksimal hari ke belakang per ticker (default: tidak terbatas)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Dry-run: tidak simpan ke DB, hanya simulasi",
    )
    parser.add_argument(
        "--delay-min",
        type=float,
        default=DELAY_MIN,
        metavar="SEC",
        help=f"Delay minimum antar request (default: {DELAY_MIN}s)",
    )
    parser.add_argument(
        "--delay-max",
        type=float,
        default=DELAY_MAX,
        metavar="SEC",
        help=f"Delay maksimum antar request (default: {DELAY_MAX}s)",
    )
    args = parser.parse_args()

    # Apply parsed delay values
    DELAY_MIN = args.delay_min
    DELAY_MAX = args.delay_max

    # ── Resolve tickers ──────────────────────────────────────────────────
    if args.tickers:
        tickers = [t.upper() for t in args.tickers]
        logger.info(f"Tickers (manual): {tickers}")
    else:
        tickers = _get_active_tickers()
        logger.info(f"Tickers (dari universe): {len(tickers)} ticker aktif")

    if not tickers:
        logger.error(
            "Tidak ada ticker yang ditemukan. Pastikan tabel universe sudah terisi."
        )
        sys.exit(1)

    # ── Resolve start date ───────────────────────────────────────────────
    if args.start_date:
        try:
            start_date = date.fromisoformat(args.start_date)
        except ValueError:
            logger.error(
                f"Format --start-date tidak valid: '{args.start_date}'. Gunakan YYYY-MM-DD."
            )
            sys.exit(1)
    else:
        start_date = date.today() - timedelta(days=1)

    # ── Try importing tqdm ────────────────────────────────────────────────
    try:
        from tqdm import tqdm
    except ImportError:
        logger.warning("tqdm tidak terinstall. Install dengan: pip install tqdm")
        tqdm = None

    # ── Banner ───────────────────────────────────────────────────────────
    print()
    print("=" * 60)
    print("  Bandarmologi Backfill Scraper")
    print("=" * 60)
    print(f"  Tickers    : {len(tickers)}")
    print(f"  Start date : {start_date} (mundur ke belakang)")
    print(f"  Max days   : {args.max_days or 'tidak terbatas'}")
    print(f"  Dry-run    : {'YA' if args.dry_run else 'tidak'}")
    print(f"  Delay      : {DELAY_MIN}-{DELAY_MAX}s per request")
    print(f"  Stop cond  : {CONSECUTIVE_EMPTY_STOP} hari berturut-turut empty")
    print("=" * 60)
    print()

    if args.dry_run:
        print("DRY-RUN MODE: Tidak ada data yang disimpan ke DB.\n")

    # ── Main loop per ticker ─────────────────────────────────────────────
    all_stats = {}
    ticker_iter = tqdm(tickers, desc="Tickers", unit="ticker") if tqdm else tickers

    for ticker in ticker_iter:
        if tqdm and hasattr(ticker_iter, "set_postfix"):
            ticker_iter.set_postfix({"current": ticker})

        logger.info(f"\n{'─'*50}")
        logger.info(f"Backfill: {ticker} | start={start_date} | max_days={args.max_days}")

        if tqdm:
            with tqdm(
                desc=f"  {ticker}",
                unit="day",
                leave=False,
                bar_format="{desc}: {n_fmt} days [{elapsed}, {rate_fmt}]",
            ) as day_bar:
                stats = _backfill_ticker_with_bar(
                    ticker, start_date, args.max_days, args.dry_run, day_bar
                )
        else:
            stats = backfill_ticker(ticker, start_date, args.max_days, args.dry_run)

        all_stats[ticker] = stats
        logger.info(
            f"  > {ticker}: fetched={stats['fetched']} skipped={stats['skipped']} "
            f"empty={stats['empty']} api_errors={stats['api_errors']} "
            f"stopped_at={stats.get('stopped_at', 'end of range')}"
        )

    # ── Final summary ─────────────────────────────────────────────────────
    total_fetched   = sum(s["fetched"]    for s in all_stats.values())
    total_skipped   = sum(s["skipped"]    for s in all_stats.values())
    total_empty     = sum(s["empty"]      for s in all_stats.values())
    total_api_err   = sum(s["api_errors"] for s in all_stats.values())

    print()
    print("=" * 70)
    print("  SUMMARY")
    print("=" * 70)
    print(f"  Total ticker diproses        : {len(all_stats)}")
    print(f"  Total hari berhasil di-fetch : {total_fetched:,}")
    print(f"  Total hari diskip (cache hit): {total_skipped:,}")
    print(f"  Total hari kosong (libur/suspend): {total_empty:,}  <- normal, bukan error")
    print(f"  Total API error (exception)  : {total_api_err:,}")
    print()

    # Per-ticker detail (hanya jika jumlah ticker tidak terlalu banyak)
    if len(all_stats) <= 20:
        print(f"  {'Ticker':<10} {'Fetched':>8} {'Skipped':>8} {'Empty':>7} {'APIErr':>7}  Stopped at")
        print(f"  {'-'*10} {'-'*8} {'-'*8} {'-'*7} {'-'*7}  {'-'*25}")
        for t, s in all_stats.items():
            stopped = s.get("stopped_at") or "—"
            if len(stopped) > 30:
                stopped = stopped[:30] + "..."
            print(
                f"  {t:<10} {s['fetched']:>8,} {s['skipped']:>8,} "
                f"{s['empty']:>7,} {s['api_errors']:>7,}  {stopped}"
            )
    else:
        print("  (Detail per ticker tersedia di logs/backfill_bandarmology.log)")

    print()
    print(f"  Log lengkap: logs/backfill_bandarmology.log")
    print(f"  Catatan: 'Empty' = API return kosong (normal: hari libur/suspend/tidak ada transaksi)")
    print(f"           'APIErr' = Exception / HTTP error (tidak normal, cek log)")
    print("=" * 70)
    if args.dry_run:
        print("\n  DRY-RUN: Tidak ada data yang disimpan.")
    print()


def _backfill_ticker_with_bar(
    ticker: str,
    start_date: date,
    max_days,
    dry_run: bool,
    pbar,
) -> dict:
    """
    Versi backfill_ticker yang update tqdm progress bar setiap langkah.
    Dipisah agar backfill_ticker tetap clean dan reusable tanpa dependency tqdm.
    """
    from db.cache import get_cached_broker_daily, save_broker_daily

    stats = {"fetched": 0, "skipped": 0, "empty": 0, "api_errors": 0, "stopped_at": None}
    consecutive_empty = 0
    days_checked = 0

    for trade_date in _iter_trading_days(start_date):
        date_str = trade_date.isoformat()

        if max_days is not None and days_checked >= max_days:
            stats["stopped_at"] = f"{date_str} (max_days={max_days} reached)"
            break

        days_checked += 1
        pbar.update(1)
        pbar.set_postfix(
            fetched=stats["fetched"],
            skipped=stats["skipped"],
            empty=stats["empty"],
            date=date_str,
        )

        # Cache-first
        cached = get_cached_broker_daily(ticker, date_str)
        if cached is not None:
            if cached.get("buy") or cached.get("sell"):
                stats["skipped"] += 1
                consecutive_empty = 0
                time.sleep(0.01)
                continue
            consecutive_empty += 1
            stats["empty"] += 1
            if consecutive_empty >= CONSECUTIVE_EMPTY_STOP:
                stats["stopped_at"] = (
                    f"{date_str} ({consecutive_empty} consecutive empty)"
                )
                break
            continue

        # Fetch
        if not dry_run:
            result = _fetch_day(ticker, date_str)
        else:
            cutoff = date.today() - timedelta(days=730)
            result = (
                {"buy": [{"broker": "DRY"}], "sell": [], "foreign_net": 0}
                if trade_date > cutoff else _EMPTY
            )

        if result is _EMPTY:
            consecutive_empty += 1
            stats["empty"] += 1
            if consecutive_empty >= CONSECUTIVE_EMPTY_STOP:
                stats["stopped_at"] = (
                    f"{date_str} ({consecutive_empty} consecutive empty)"
                )
                break

        elif result is _API_ERROR:
            consecutive_empty += 1
            stats["api_errors"] += 1
            if consecutive_empty >= CONSECUTIVE_EMPTY_STOP:
                stats["stopped_at"] = (
                    f"{date_str} ({consecutive_empty} consecutive empty/error)"
                )
                break

        else:
            day_data = result
            consecutive_empty = 0
            if not dry_run:
                try:
                    save_broker_daily(ticker, date_str, day_data)
                    stats["fetched"] += 1
                except Exception as e:
                    logger.warning(f"  [{ticker}] {date_str} save error: {e}")
                    stats["api_errors"] += 1
            else:
                stats["fetched"] += 1

        if not dry_run:
            time.sleep(random.uniform(DELAY_MIN, DELAY_MAX))

    return stats


if __name__ == "__main__":
    main()
