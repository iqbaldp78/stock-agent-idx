"""
DB Cache Layer — Read/write helpers untuk raw data fetchers.

Strategi insert:
  trade_date < today  →  INSERT ... ON CONFLICT DO NOTHING   (data final, tidak berubah)
  trade_date = today  →  INSERT ... ON CONFLICT DO UPDATE SET (realtime upsert, market buka)
"""
import json
import logging
from datetime import date, timedelta
from typing import Optional

import pandas as pd
from sqlalchemy import text

from db import SessionLocal

logger = logging.getLogger(__name__)


# ─── Date Utilities ────────────────────────────────────────────────────────

def _weekdays_between(start: date, end: date) -> list[date]:
    """Semua hari kerja (Sen-Jum) antara start dan end (inklusif)."""
    result = []
    current = start
    while current <= end:
        if current.weekday() < 5:
            result.append(current)
        current += timedelta(days=1)
    return result


def find_missing_dates(cached_df: pd.DataFrame, start_date: str, end_date: str) -> list[date]:
    """
    Temukan hari kerja dalam rentang yang belum ada di cached_df.
    cached_df harus punya DatetimeIndex.
    """
    start = date.fromisoformat(start_date)
    end = date.fromisoformat(end_date)
    expected = set(_weekdays_between(start, end))

    if cached_df is None or cached_df.empty:
        return sorted(expected)

    cached_dates = set(
        d.date() if hasattr(d, "date") else d
        for d in cached_df.index
    )
    return sorted(expected - cached_dates)


def group_into_ranges(dates: list[date]) -> list[tuple[date, date]]:
    """
    Group list of dates menjadi (start, end) tuples untuk contiguous ranges.
    Menjembatani weekend (gap ≤ 3 hari kalender dianggap contiguous).
    E.g. [Mon, Tue, Thu] → [(Mon, Tue), (Thu, Thu)]
    """
    if not dates:
        return []
    ranges = []
    start = prev = dates[0]
    for d in dates[1:]:
        if (d - prev).days <= 3:
            prev = d
        else:
            ranges.append((start, prev))
            start = prev = d
    ranges.append((start, prev))
    return ranges


def _period_to_dates(period: str) -> tuple[str, str]:
    """Konversi period string (3mo, 1y, 8y, dst) ke (start_date, end_date) ISO string."""
    today = date.today()
    end_date = today
    if period.endswith("y"):
        years = int(period[:-1])
        try:
            start_date = today.replace(year=today.year - years)
        except ValueError:
            start_date = today.replace(year=today.year - years, day=28)
    elif period.endswith("mo"):
        months = int(period[:-2])
        start_date = today - timedelta(days=months * 30)
    elif period.endswith("d"):
        days = int(period[:-1])
        start_date = today - timedelta(days=days)
    else:
        start_date = today - timedelta(days=90)
    return start_date.isoformat(), end_date.isoformat()


# ─── OHLCV per ticker ──────────────────────────────────────────────────────

def get_cached_ohlcv(ticker: str, start_date: str, end_date: str) -> pd.DataFrame:
    """Baca ohlcv_prices dari DB. Returns DataFrame dengan DatetimeIndex."""
    db = SessionLocal()
    try:
        rows = db.execute(
            text("""
                SELECT trade_date, open, high, low, close, volume
                FROM ohlcv_prices
                WHERE ticker = :ticker
                  AND trade_date BETWEEN :start AND :end
                ORDER BY trade_date
            """),
            {"ticker": ticker, "start": start_date, "end": end_date},
        ).fetchall()
    except Exception as e:
        logger.warning(f"[cache] get_cached_ohlcv({ticker}) error: {e}")
        return pd.DataFrame()
    finally:
        db.close()

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows, columns=["Date", "Open", "High", "Low", "Close", "Volume"])
    df["Date"] = pd.to_datetime(df["Date"])
    df.set_index("Date", inplace=True)
    for col in ["Open", "High", "Low", "Close", "Volume"]:
        df[col] = df[col].astype(float)
    return df


def save_ohlcv(
    ticker: str,
    df: pd.DataFrame,
    today_date: Optional[date] = None,
    source: str = "stockbit",
) -> None:
    """Simpan OHLCV ke DB. Today → UPSERT. History → INSERT IGNORE."""
    if df is None or df.empty:
        return
    if today_date is None:
        today_date = date.today()

    db = SessionLocal()
    try:
        for idx, row in df.iterrows():
            trade_date = idx.date() if hasattr(idx, "date") else idx
            params = {
                "ticker": ticker,
                "trade_date": trade_date,
                "open": float(row.get("Open", 0) or 0),
                "high": float(row.get("High", 0) or 0),
                "low": float(row.get("Low", 0) or 0),
                "close": float(row.get("Close", 0) or 0),
                "volume": int(row.get("Volume", 0) or 0),
                "source": source,
            }
            if trade_date == today_date:
                db.execute(text("""
                    INSERT INTO ohlcv_prices
                        (ticker, trade_date, open, high, low, close, volume, source)
                    VALUES
                        (:ticker, :trade_date, :open, :high, :low, :close, :volume, :source)
                    ON CONFLICT (ticker, trade_date) DO UPDATE SET
                        open = EXCLUDED.open, high = EXCLUDED.high,
                        low  = EXCLUDED.low,  close = EXCLUDED.close,
                        volume = EXCLUDED.volume, created_at = NOW()
                """), params)
            else:
                db.execute(text("""
                    INSERT INTO ohlcv_prices
                        (ticker, trade_date, open, high, low, close, volume, source)
                    VALUES
                        (:ticker, :trade_date, :open, :high, :low, :close, :volume, :source)
                    ON CONFLICT (ticker, trade_date) DO NOTHING
                """), params)
        db.commit()
        logger.debug(f"[cache] Saved OHLCV {ticker}: {len(df)} rows")
    except Exception as e:
        db.rollback()
        logger.error(f"[cache] save_ohlcv({ticker}) error: {e}")
    finally:
        db.close()


def get_ohlcv_no_data_dates(ticker: str, start_date: str, end_date: str, source: str = "stockbit") -> set[date]:
    """Ambil tanggal no-data marker untuk ticker dalam rentang tertentu."""
    db = SessionLocal()
    try:
        rows = db.execute(
            text("""
                SELECT trade_date
                FROM ohlcv_no_data
                WHERE ticker = :ticker
                  AND source = :source
                  AND trade_date BETWEEN :start AND :end
            """),
            {
                "ticker": ticker,
                "source": source,
                "start": start_date,
                "end": end_date,
            },
        ).fetchall()
        return {row[0] for row in rows}
    except Exception as e:
        logger.warning(f"[cache] get_ohlcv_no_data_dates({ticker}) error: {e}")
        return set()
    finally:
        db.close()


def save_ohlcv_no_data_dates(
    ticker: str,
    dates: list[date],
    source: str = "stockbit",
) -> None:
    """Simpan marker untuk tanggal yang dipastikan tidak memiliki data OHLCV."""
    if not dates:
        return

    db = SessionLocal()
    try:
        for d in dates:
            db.execute(
                text("""
                    INSERT INTO ohlcv_no_data (ticker, trade_date, source)
                    VALUES (:ticker, :trade_date, :source)
                    ON CONFLICT (ticker, trade_date, source) DO NOTHING
                """),
                {
                    "ticker": ticker,
                    "trade_date": d,
                    "source": source,
                },
            )
        db.commit()
    except Exception as e:
        db.rollback()
        logger.warning(f"[cache] save_ohlcv_no_data_dates({ticker}) error: {e}")
    finally:
        db.close()


# ─── IHSG OHLCV ────────────────────────────────────────────────────────────

def get_cached_ihsg_ohlcv(start_date: str, end_date: str) -> pd.DataFrame:
    """Baca ihsg_ohlcv dari DB. Returns DataFrame dengan DatetimeIndex."""
    db = SessionLocal()
    try:
        rows = db.execute(
            text("""
                SELECT trade_date, open, high, low, close, volume
                FROM ihsg_ohlcv
                WHERE trade_date BETWEEN :start AND :end
                ORDER BY trade_date
            """),
            {"start": start_date, "end": end_date},
        ).fetchall()
    except Exception as e:
        logger.warning(f"[cache] get_cached_ihsg_ohlcv error: {e}")
        return pd.DataFrame()
    finally:
        db.close()

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows, columns=["Date", "Open", "High", "Low", "Close", "Volume"])
    df["Date"] = pd.to_datetime(df["Date"])
    df.set_index("Date", inplace=True)
    for col in ["Open", "High", "Low", "Close", "Volume"]:
        df[col] = df[col].astype(float)
    return df


def save_ihsg_ohlcv(df: pd.DataFrame, today_date: Optional[date] = None) -> None:
    """Simpan IHSG OHLCV ke DB. Today → UPSERT. History → INSERT IGNORE."""
    if df is None or df.empty:
        return
    if today_date is None:
        today_date = date.today()

    db = SessionLocal()
    try:
        for idx, row in df.iterrows():
            trade_date = idx.date() if hasattr(idx, "date") else idx
            params = {
                "trade_date": trade_date,
                "open": float(row.get("Open", 0) or 0),
                "high": float(row.get("High", 0) or 0),
                "low": float(row.get("Low", 0) or 0),
                "close": float(row.get("Close", 0) or 0),
                "volume": int(row.get("Volume", 0) or 0),
            }
            if trade_date == today_date:
                db.execute(text("""
                    INSERT INTO ihsg_ohlcv (trade_date, open, high, low, close, volume)
                    VALUES (:trade_date, :open, :high, :low, :close, :volume)
                    ON CONFLICT (trade_date) DO UPDATE SET
                        open = EXCLUDED.open, high = EXCLUDED.high,
                        low  = EXCLUDED.low,  close = EXCLUDED.close,
                        volume = EXCLUDED.volume, created_at = NOW()
                """), params)
            else:
                db.execute(text("""
                    INSERT INTO ihsg_ohlcv (trade_date, open, high, low, close, volume)
                    VALUES (:trade_date, :open, :high, :low, :close, :volume)
                    ON CONFLICT (trade_date) DO NOTHING
                """), params)
        db.commit()
        logger.debug(f"[cache] Saved IHSG OHLCV: {len(df)} rows")
    except Exception as e:
        db.rollback()
        logger.error(f"[cache] save_ihsg_ohlcv error: {e}")
    finally:
        db.close()


def get_ihsg_no_data_dates(start_date: str, end_date: str) -> set[date]:
    """Ambil tanggal no-data marker IHSG (libur IDX) dalam rentang tertentu."""
    db = SessionLocal()
    try:
        rows = db.execute(
            text("""
                SELECT trade_date
                FROM ihsg_no_data
                WHERE trade_date BETWEEN :start AND :end
            """),
            {"start": start_date, "end": end_date},
        ).fetchall()
        return {row[0] for row in rows}
    except Exception as e:
        logger.warning(f"[cache] get_ihsg_no_data_dates error: {e}")
        return set()
    finally:
        db.close()


def save_ihsg_no_data_dates(dates: list[date]) -> None:
    """Simpan marker tanggal IHSG yang kosong (libur IDX) agar tidak di-fetch ulang."""
    if not dates:
        return
    db = SessionLocal()
    try:
        for d in dates:
            db.execute(
                text("""
                    INSERT INTO ihsg_no_data (trade_date)
                    VALUES (:trade_date)
                    ON CONFLICT (trade_date) DO NOTHING
                """),
                {"trade_date": d},
            )
        db.commit()
        logger.debug(f"[cache] Saved {len(dates)} IHSG no-data markers")
    except Exception as e:
        db.rollback()
        logger.warning(f"[cache] save_ihsg_no_data_dates error: {e}")
    finally:
        db.close()


# ─── Stock Info Snapshot ────────────────────────────────────────────────────

def get_cached_stock_info(ticker: str, snapshot_date: str) -> Optional[dict]:
    """
    Baca fundamental snapshot dari DB.
    Returns dict dalam format yang sama dengan get_stock_info(), atau None jika tidak ada.
    """
    db = SessionLocal()
    try:
        row = db.execute(
            text("""
                SELECT per, pbv, roe, der, market_cap, current_price,
                       revenue_growth, earnings_growth, high_52w, low_52w,
                       dividend_yield, dividend_payout_ratio, dividend_per_share,
                       net_income_history, eps_history, revenue_history, extra_data
                FROM stock_info_snapshot
                WHERE ticker = :ticker AND snapshot_date = :snapshot_date
                LIMIT 1
            """),
            {"ticker": ticker, "snapshot_date": snapshot_date},
        ).fetchone()
    except Exception as e:
        logger.warning(f"[cache] get_cached_stock_info({ticker}) error: {e}")
        return None
    finally:
        db.close()

    if not row:
        return None

    (per, pbv, roe, der, market_cap, current_price,
     revenue_growth, earnings_growth, high_52w, low_52w,
     dividend_yield, dividend_payout_ratio, dividend_per_share,
     net_income_history, eps_history, revenue_history, extra_data) = row

    extra = extra_data or {}
    return {
        "ticker": ticker,
        "per": float(per) if per is not None else None,
        "pbv": float(pbv) if pbv is not None else None,
        "roe": float(roe) if roe is not None else None,
        "der": float(der) if der is not None else None,
        "market_cap": float(market_cap) if market_cap is not None else None,
        "current_price": float(current_price) if current_price is not None else None,
        "revenue_growth": float(revenue_growth) if revenue_growth is not None else None,
        "earnings_growth": float(earnings_growth) if earnings_growth is not None else None,
        "52w_high": float(high_52w) if high_52w is not None else None,
        "52w_low": float(low_52w) if low_52w is not None else None,
        "dividend_yield": float(dividend_yield) if dividend_yield is not None else None,
        "dividend_payout_ratio": float(dividend_payout_ratio) if dividend_payout_ratio is not None else None,
        "dividend_per_share": float(dividend_per_share) if dividend_per_share is not None else None,
        "history": {
            "net_income": net_income_history or [],
            "eps": eps_history or [],
            "revenue": revenue_history or [],
            **extra.get("history", {}),
        },
        **{k: v for k, v in extra.items() if k != "history"},
    }


def save_stock_info(ticker: str, snapshot_date: str, data: dict) -> None:
    """Simpan fundamental snapshot ke DB. Today → UPSERT. History → INSERT IGNORE."""
    if not data:
        return

    is_today = (snapshot_date == date.today().isoformat())
    history = data.get("history", {})
    net_income_history = history.get("net_income", [])
    eps_history = history.get("eps", [])
    revenue_history = history.get("revenue", [])

    # Sisa history fields & non-standard keys masuk extra_data
    extra_history = {k: v for k, v in history.items() if k not in ("net_income", "eps", "revenue")}
    _standard_keys = {
        "ticker", "per", "pbv", "roe", "der", "market_cap", "current_price",
        "revenue_growth", "earnings_growth", "52w_high", "52w_low",
        "dividend_yield", "dividend_payout_ratio", "dividend_per_share", "history",
    }
    extra_data: dict = {k: v for k, v in data.items() if k not in _standard_keys}
    if extra_history:
        extra_data["history"] = extra_history

    params = {
        "ticker": ticker,
        "snapshot_date": snapshot_date,
        "per": data.get("per"),
        "pbv": data.get("pbv"),
        "roe": data.get("roe"),
        "der": data.get("der"),
        "market_cap": data.get("market_cap"),
        "current_price": data.get("current_price"),
        "revenue_growth": data.get("revenue_growth"),
        "earnings_growth": data.get("earnings_growth"),
        "high_52w": data.get("52w_high"),
        "low_52w": data.get("52w_low"),
        "dividend_yield": data.get("dividend_yield"),
        "dividend_payout_ratio": data.get("dividend_payout_ratio"),
        "dividend_per_share": data.get("dividend_per_share"),
        "net_income_history": json.dumps(net_income_history),
        "eps_history": json.dumps(eps_history),
        "revenue_history": json.dumps(revenue_history),
        "extra_data": json.dumps(extra_data) if extra_data else None,
    }

    _cols = """ticker, snapshot_date, per, pbv, roe, der, market_cap, current_price,
               revenue_growth, earnings_growth, high_52w, low_52w,
               dividend_yield, dividend_payout_ratio, dividend_per_share,
               net_income_history, eps_history, revenue_history, extra_data"""
    _vals = """:ticker, :snapshot_date, :per, :pbv, :roe, :der, :market_cap, :current_price,
               :revenue_growth, :earnings_growth, :high_52w, :low_52w,
               :dividend_yield, :dividend_payout_ratio, :dividend_per_share,
               :net_income_history, :eps_history, :revenue_history, :extra_data"""

    db = SessionLocal()
    try:
        if is_today:
            db.execute(text(f"""
                INSERT INTO stock_info_snapshot ({_cols}) VALUES ({_vals})
                ON CONFLICT (ticker, snapshot_date) DO UPDATE SET
                    per = EXCLUDED.per, pbv = EXCLUDED.pbv,
                    roe = EXCLUDED.roe, der = EXCLUDED.der,
                    market_cap = EXCLUDED.market_cap,
                    current_price = EXCLUDED.current_price,
                    revenue_growth = EXCLUDED.revenue_growth,
                    earnings_growth = EXCLUDED.earnings_growth,
                    high_52w = EXCLUDED.high_52w, low_52w = EXCLUDED.low_52w,
                    dividend_yield = EXCLUDED.dividend_yield,
                    dividend_payout_ratio = EXCLUDED.dividend_payout_ratio,
                    dividend_per_share = EXCLUDED.dividend_per_share,
                    net_income_history = EXCLUDED.net_income_history,
                    eps_history = EXCLUDED.eps_history,
                    revenue_history = EXCLUDED.revenue_history,
                    extra_data = EXCLUDED.extra_data, created_at = NOW()
            """), params)
        else:
            db.execute(text(f"""
                INSERT INTO stock_info_snapshot ({_cols}) VALUES ({_vals})
                ON CONFLICT (ticker, snapshot_date) DO NOTHING
            """), params)
        db.commit()
        logger.debug(f"[cache] Saved stock_info {ticker} for {snapshot_date}")
    except Exception as e:
        db.rollback()
        logger.error(f"[cache] save_stock_info({ticker}) error: {e}")
    finally:
        db.close()


# ─── Sector OHLCV ──────────────────────────────────────────────────────────

def get_cached_sector_ohlcv(sector_code: str, start_date: str, end_date: str) -> pd.DataFrame:
    """Baca sector_ohlcv dari DB. Returns DataFrame dengan DatetimeIndex."""
    db = SessionLocal()
    try:
        rows = db.execute(
            text("""
                SELECT trade_date, open, high, low, close
                FROM sector_ohlcv
                WHERE sector_code = :sector_code
                  AND trade_date BETWEEN :start AND :end
                ORDER BY trade_date
            """),
            {"sector_code": sector_code, "start": start_date, "end": end_date},
        ).fetchall()
    except Exception as e:
        logger.warning(f"[cache] get_cached_sector_ohlcv({sector_code}) error: {e}")
        return pd.DataFrame()
    finally:
        db.close()

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows, columns=["Date", "Open", "High", "Low", "Close"])
    df["Date"] = pd.to_datetime(df["Date"])
    df.set_index("Date", inplace=True)
    for col in ["Open", "High", "Low", "Close"]:
        df[col] = df[col].astype(float)
    return df


def save_sector_ohlcv(
    sector_code: str,
    df: pd.DataFrame,
    today_date: Optional[date] = None,
) -> None:
    """Simpan sektor OHLCV ke DB. Today → UPSERT. History → INSERT IGNORE."""
    if df is None or df.empty:
        return
    if today_date is None:
        today_date = date.today()

    db = SessionLocal()
    try:
        for idx, row in df.iterrows():
            trade_date = idx.date() if hasattr(idx, "date") else idx
            close_val = row.get("Close") or row.get("Adj Close")
            if close_val is None:
                continue
            params = {
                "sector_code": sector_code,
                "trade_date": trade_date,
                "open": float(row.get("Open", 0) or 0),
                "high": float(row.get("High", 0) or 0),
                "low": float(row.get("Low", 0) or 0),
                "close": float(close_val),
            }
            if trade_date == today_date:
                db.execute(text("""
                    INSERT INTO sector_ohlcv (sector_code, trade_date, open, high, low, close)
                    VALUES (:sector_code, :trade_date, :open, :high, :low, :close)
                    ON CONFLICT (sector_code, trade_date) DO UPDATE SET
                        open = EXCLUDED.open, high = EXCLUDED.high,
                        low  = EXCLUDED.low,  close = EXCLUDED.close,
                        created_at = NOW()
                """), params)
            else:
                db.execute(text("""
                    INSERT INTO sector_ohlcv (sector_code, trade_date, open, high, low, close)
                    VALUES (:sector_code, :trade_date, :open, :high, :low, :close)
                    ON CONFLICT (sector_code, trade_date) DO NOTHING
                """), params)
        db.commit()
        logger.debug(f"[cache] Saved sector OHLCV {sector_code}: {len(df)} rows")
    except Exception as e:
        db.rollback()
        logger.error(f"[cache] save_sector_ohlcv({sector_code}) error: {e}")
    finally:
        db.close()


# ─── Broker Daily ──────────────────────────────────────────────────────────

def get_cached_broker_daily(ticker: str, trade_date: str) -> Optional[dict]:
    """
    Baca data broker harian dari broker_accumulation.
    Returns dict dalam format yang sama dengan get_broker_daily(), atau None jika tidak ada.
    """
    db = SessionLocal()
    try:
        rows = db.execute(
            text("""
                SELECT broker_code, broker_name,
                       buy_lot, buy_value, avg_price,
                       sell_lot, sell_value,
                       broker_type, day_foreign_net
                FROM broker_accumulation
                WHERE ticker = :ticker AND trade_date = :trade_date
            """),
            {"ticker": ticker, "trade_date": trade_date},
        ).fetchall()
    except Exception as e:
        logger.warning(f"[cache] get_cached_broker_daily({ticker}, {trade_date}) error: {e}")
        return None
    finally:
        db.close()

    if not rows:
        return None

    buy = []
    sell = []
    foreign_net = 0
    for (broker_code, broker_name, buy_lot, buy_value, avg_price,
         sell_lot, sell_value, broker_type, day_fn) in rows:
        if buy_lot and buy_lot > 0:
            buy.append({
                "broker": broker_code,
                "broker_name": broker_name or "",
                "lot": int(buy_lot),
                "value": int(buy_value or 0),
                "avg_price": int(avg_price or 0),
                "type": broker_type or "",
            })
        if sell_lot and sell_lot != 0:
            sell.append({
                "broker": broker_code,
                "broker_name": broker_name or "",
                "lot": abs(int(sell_lot)),
                "value": abs(int(sell_value or 0)),
                "avg_price": int(avg_price or 0),
                "type": broker_type or "",
            })
        if day_fn is not None:
            foreign_net = int(day_fn)

    return {
        "ticker": ticker,
        "date": trade_date,
        "buy": sorted(buy, key=lambda x: x["value"], reverse=True),
        "sell": sorted(sell, key=lambda x: x["value"], reverse=True),
        "foreign_net": foreign_net,
    }


def save_broker_daily(
    ticker: str,
    trade_date: str,
    day_data: dict,
    today_date: Optional[date] = None,
) -> None:
    """
    Simpan hasil get_broker_daily() ke broker_accumulation.
    Merge buy & sell per broker_code dalam 1 row.
    Today → UPSERT. History → INSERT IGNORE.
    """
    if not day_data:
        return
    if today_date is None:
        today_date = date.today()

    is_today = (trade_date == today_date.isoformat())
    foreign_net = day_data.get("foreign_net", 0)

    # Merge buy dan sell per broker_code
    brokers: dict[str, dict] = {}
    for entry in day_data.get("buy", []):
        code = entry.get("broker")
        if not code:
            continue
        brokers[code] = {
            "broker_name": entry.get("broker_name", ""),
            "buy_lot": entry.get("lot", 0),
            "buy_value": entry.get("value", 0),
            "avg_price": entry.get("avg_price", 0),
            "sell_lot": 0,
            "sell_value": 0,
            "broker_type": entry.get("type") or None,
        }
    for entry in day_data.get("sell", []):
        code = entry.get("broker")
        if not code:
            continue
        if code not in brokers:
            brokers[code] = {
                "broker_name": entry.get("broker_name", ""),
                "buy_lot": 0,
                "buy_value": 0,
                "avg_price": entry.get("avg_price", 0),
                "sell_lot": 0,
                "sell_value": 0,
                "broker_type": entry.get("type") or None,
            }
        brokers[code]["sell_lot"] = entry.get("lot", 0)
        brokers[code]["sell_value"] = entry.get("value", 0)
        if not brokers[code]["broker_type"]:
            brokers[code]["broker_type"] = entry.get("type") or None

    if not brokers:
        return

    db = SessionLocal()
    try:
        for code, data in brokers.items():
            params = {
                "ticker": ticker,
                "trade_date": trade_date,
                "broker_code": code,
                "broker_name": data["broker_name"],
                "buy_lot": data["buy_lot"],
                "buy_value": data["buy_value"],
                "avg_price": data["avg_price"],
                "sell_lot": data["sell_lot"],
                "sell_value": data["sell_value"],
                "broker_type": data["broker_type"],
                "day_foreign_net": foreign_net,
            }
            _cols = """ticker, trade_date, broker_code, broker_name,
                       buy_lot, buy_value, avg_price,
                       sell_lot, sell_value, broker_type, day_foreign_net"""
            _vals = """:ticker, :trade_date, :broker_code, :broker_name,
                       :buy_lot, :buy_value, :avg_price,
                       :sell_lot, :sell_value, :broker_type, :day_foreign_net"""
            if is_today:
                db.execute(text(f"""
                    INSERT INTO broker_accumulation ({_cols}) VALUES ({_vals})
                    ON CONFLICT (ticker, trade_date, broker_code) DO UPDATE SET
                        buy_lot = EXCLUDED.buy_lot, buy_value = EXCLUDED.buy_value,
                        avg_price = EXCLUDED.avg_price,
                        sell_lot = EXCLUDED.sell_lot, sell_value = EXCLUDED.sell_value,
                        broker_type = EXCLUDED.broker_type,
                        day_foreign_net = EXCLUDED.day_foreign_net,
                        created_at = NOW()
                """), params)
            else:
                db.execute(text(f"""
                    INSERT INTO broker_accumulation ({_cols}) VALUES ({_vals})
                    ON CONFLICT (ticker, trade_date, broker_code) DO NOTHING
                """), params)
        db.commit()
        logger.debug(f"[cache] Saved broker daily {ticker} {trade_date}: {len(brokers)} brokers")
    except Exception as e:
        db.rollback()
        logger.error(f"[cache] save_broker_daily({ticker}, {trade_date}) error: {e}")
    finally:
        db.close()
