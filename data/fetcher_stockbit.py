"""
Data Fetcher — Stockbit
Mengambil data broker summary (real API), OHLCV, dan fundamental saham.

Menyediakan:
    - get_ohlcv()       → OHLCV DataFrame (mock)
    - get_stock_info()  → fundamental info dict (mock)
    - Broker summary + avg price per broker (real API)

Window:
    - 7 hari  → timing signal (sedang aktif akumulasi?)
    - 30 hari → true avg cost bandar
"""
import logging
import os
import random
import time
from datetime import date, datetime, timedelta
from functools import wraps

import httpx
import pandas as pd
import numpy as np

from db.cache import (
    get_cached_ohlcv,
    save_ohlcv,
    find_missing_dates,
    group_into_ranges,
    get_cached_stock_info,
    save_stock_info,
    get_cached_broker_daily,
    save_broker_daily,
)
from datetime import date as _date

# shortcut agar tidak konflik dengan parameter bernama 'date' di get_broker_daily
date_module_today = _date.today

logger = logging.getLogger(__name__)


def _retry_on_rate_limit(max_attempts: int = 4, base_delay: float = 1.0):
    """
    Decorator untuk retry pada rate limit (429) dan server errors (500, 502, 503, 504).
    Menggunakan exponential backoff.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except httpx.HTTPStatusError as exc:
                    status = exc.response.status_code
                    last_exception = exc
                    
                    # Retry jika 429 (rate limit) atau 5xx errors
                    if status in (429, 500, 502, 503, 504) and attempt < max_attempts - 1:
                        wait_time = base_delay * (2 ** attempt)
                        logger.warning(
                            f"[{func.__name__}] HTTP {status} on attempt {attempt + 1}/{max_attempts}. "
                            f"Retrying in {wait_time:.1f}s..."
                        )
                        time.sleep(wait_time)
                        continue
                    
                    # Jika status code lain atau attempt terakhir, raise exception
                    raise
            
            # Jika semua attempt gagal
            if last_exception:
                raise last_exception
        
        return wrapper
    return decorator


# Daftar broker IDX
BROKER_LIST = [
    ("BK", "JP Morgan"),
    ("YU", "CIMB Sekuritas"),
    ("CC", "Mandiri Sekuritas"),
    ("AK", "UBS Securities"),
    ("DX", "BNI Sekuritas"),
    ("KZ", "Daewoo Securities"),
    ("RX", "Macquarie Securities"),
    ("GR", "Goldman Sachs"),
    ("CG", "CGS-CIMB"),
    ("LG", "Trimegah Sekuritas"),
]

_BROKER_NAME_MAP = {code: name for code, name in BROKER_LIST}

STOCKBIT_MARKETDETECTOR_URL = "https://exodus.stockbit.com/marketdetectors/{ticker}"
STOCKBIT_ORDERBOOK_URL = "https://exodus.stockbit.com/company-price-feed/v2/orderbook/companies/{ticker}"

# Market cap realistis per ticker (dalam IDR)
_MARKET_CAPS = {
    "BBCA": 1_200_000_000_000_000, "BBRI": 800_000_000_000_000,
    "BMRI": 500_000_000_000_000, "TLKM": 350_000_000_000_000,
    "ASII": 250_000_000_000_000, "UNVR": 180_000_000_000_000,
    "ICBP": 120_000_000_000_000, "KLBF": 80_000_000_000_000,
    "ANTM": 60_000_000_000_000, "INDF": 90_000_000_000_000,
    "GOTO": 150_000_000_000_000, "BYAN": 120_000_000_000_000,
    "MDKA": 45_000_000_000_000, "ADMR": 20_000_000_000_000,
    "PGEO": 25_000_000_000_000, "ADRO": 90_000_000_000_000,
    "AKRA": 30_000_000_000_000, "AMMN": 80_000_000_000_000,
    "AMRT": 55_000_000_000_000, "ARTO": 40_000_000_000_000,
    "BBNI": 180_000_000_000_000, "BBTN": 35_000_000_000_000,
    "BRPT": 50_000_000_000_000, "BUKA": 20_000_000_000_000,
    "CPIN": 70_000_000_000_000, "ESSA": 15_000_000_000_000,
    "EXCL": 45_000_000_000_000, "HRUM": 25_000_000_000_000,
    "INCO": 55_000_000_000_000, "INKP": 60_000_000_000_000,
    "INTP": 50_000_000_000_000, "ISAT": 65_000_000_000_000,
    "ITMG": 40_000_000_000_000, "MAPI": 22_000_000_000_000,
    "MEDC": 35_000_000_000_000, "MIKA": 45_000_000_000_000,
    "PGAS": 55_000_000_000_000, "PTBA": 40_000_000_000_000,
    "SIDO": 25_000_000_000_000, "SMGR": 60_000_000_000_000,
    "TBIG": 50_000_000_000_000, "TINS": 15_000_000_000_000,
    "TOWR": 55_000_000_000_000, "UNTR": 100_000_000_000_000,
    "ACES": 18_000_000_000_000,
}

# Base prices per ticker
_BASE_PRICES = {
    "BBCA": 9500, "BBRI": 4800, "BMRI": 6500, "TLKM": 3800,
    "ASII": 5200, "UNVR": 4200, "ICBP": 10500, "KLBF": 1600,
    "ANTM": 1800, "INDF": 7500, "GOTO": 85, "BYAN": 18000,
    "MDKA": 2800, "ADMR": 1200, "PGEO": 1400, "ADRO": 2800,
    "AKRA": 1500, "AMMN": 9000, "AMRT": 2900, "ARTO": 2400,
    "BBNI": 5200, "BBTN": 1400, "BRPT": 1100, "BUKA": 140,
    "CPIN": 5500, "ESSA": 900, "EXCL": 2400, "HRUM": 1500,
    "INCO": 4200, "INKP": 9500, "INTP": 7500, "ISAT": 8500,
    "ITMG": 28000, "MAPI": 1700, "MEDC": 1400, "MIKA": 2800,
    "PGAS": 1600, "PTBA": 2800, "SIDO": 800, "SMGR": 4200,
    "TBIG": 2200, "TINS": 1100, "TOWR": 1050, "UNTR": 26000,
    "ACES": 700,
}


def _get_trading_days(days: int, include_today: bool = True) -> list[str]:
    """Hitung N hari trading ke belakang (skip weekend)."""
    result = []
    current = datetime.now().date()
    if include_today and current.weekday() < 5:
        result.append(current.strftime("%Y-%m-%d"))
    while len(result) < days:
        current -= timedelta(days=1)
        if current.weekday() < 5:  # Mon-Fri
            result.append(current.strftime("%Y-%m-%d"))
    return result[:days]


def _get_broker_name(code: str) -> str:
    return _BROKER_NAME_MAP.get(code, "Unknown")


def _parse_number(value) -> float:
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value))
    except ValueError:
        return 0.0


def _format_idr_compact(value: float) -> str:
    sign = "-" if value < 0 else ""
    abs_value = abs(value)
    if abs_value >= 1_000_000_000_000:
        return f"{sign}{abs_value / 1_000_000_000_000:.2f}T"
    if abs_value >= 1_000_000_000:
        return f"{sign}{abs_value / 1_000_000_000:.2f}M"
    return f"{sign}{abs_value:.0f}"


def _int_no_decimal(value) -> int:
    return int(round(_parse_number(value)))


def _normalize_broker_buy(entry: dict) -> dict:
    bval = _parse_number(entry.get("bval"))
    return {
        "broker_code": entry.get("netbs_broker_code"),
        "blot": _int_no_decimal(entry.get("blot")),
        "bval": bval,
        "bval_fmt": _format_idr_compact(bval),
        "netbs_buy_avg_price": _int_no_decimal(entry.get("netbs_buy_avg_price")),
        "type": entry.get("type"),
    }


def _normalize_broker_sell(entry: dict) -> dict:
    sval = _parse_number(entry.get("sval"))
    return {
        "broker_code": entry.get("netbs_broker_code"),
        "slot": _int_no_decimal(entry.get("slot")),
        "sval": sval,
        "sval_fmt": _format_idr_compact(sval),
        "netbs_sell_avg_price": _int_no_decimal(entry.get("netbs_sell_avg_price")),
        "type": entry.get("type"),
    }


def _normalize_bandar_detector(raw: dict) -> dict:
    if not raw:
        return {}
    avg = raw.get("avg", {}) or {}
    top3 = raw.get("top3", {}) or {}
    top5 = raw.get("top5", {}) or {}
    return {
        "broker_accdist": raw.get("broker_accdist"),
        "avg_accdist": avg.get("accdist"),
        "avg_amount": _parse_number(avg.get("amount")),
        "top3_accdist": top3.get("accdist"),
        "top3_amount": _parse_number(top3.get("amount")),
        "top5_accdist": top5.get("accdist"),
        "top5_amount": _parse_number(top5.get("amount")),
        "value": _parse_number(raw.get("value")),
        "volume": _parse_number(raw.get("volume")),
    }


def get_marketdetector_broker_summary(
    ticker: str,
    date_from: str,
    date_to: str,
    transaction_type: str = "TRANSACTION_TYPE_NET",
    market_board: str = "MARKET_BOARD_REGULER",
    investor_type: str = "INVESTOR_TYPE_ALL",
    limit: int = 10,
) -> dict:
    api_key = os.getenv("STOCKBIT_API_KEY")
    if not api_key:
        raise ValueError("STOCKBIT_API_KEY is not set")

    params = {
        "from": date_from,
        "to": date_to,
        "transaction_type": transaction_type,
        "market_board": market_board,
        "investor_type": investor_type,
        "limit": str(limit),
    }

    headers = {"Authorization": f"Bearer {api_key}"}
    url = STOCKBIT_MARKETDETECTOR_URL.format(ticker=ticker)

    with httpx.Client(timeout=30.0) as client:
        for attempt in range(3):
            try:
                response = client.get(url, params=params, headers=headers)
                response.raise_for_status()
                payload = response.json()
                break
            except httpx.HTTPStatusError as exc:
                status = exc.response.status_code
                if status in (429, 500, 502, 503, 504) and attempt < 2:
                    time.sleep(1.5 * (2 ** attempt))
                    continue
                raise

    data = payload.get("data", {})
    broker_summary = data.get("broker_summary", {})
    brokers_buy = broker_summary.get("brokers_buy", [])
    brokers_sell = broker_summary.get("brokers_sell", [])
    bandar_detector = _normalize_bandar_detector(data.get("bandar_detector", {}))

    return {
        "ticker": ticker,
        "from": data.get("from", date_from),
        "to": data.get("to", date_to),
        "brokers_buy": [_normalize_broker_buy(item) for item in brokers_buy],
        "brokers_sell": [_normalize_broker_sell(item) for item in brokers_sell],
        "bandar_detector": bandar_detector,
    }


@_retry_on_rate_limit(max_attempts=4, base_delay=1.0)
def get_current_price_stockbit(ticker: str) -> float:
    api_key = os.getenv("STOCKBIT_API_KEY")
    if not api_key:
        raise ValueError("STOCKBIT_API_KEY is not set")

    url = STOCKBIT_ORDERBOOK_URL.format(ticker=ticker.lower())
    headers = {"Authorization": f"Bearer {api_key}"}

    with httpx.Client(timeout=15.0) as client:
        response = client.get(url, headers=headers)
        response.raise_for_status()
        payload = response.json()

    if payload.get("message"):
        logger.info("Stockbit orderbook: %s", payload.get("message"))

    bid_list = payload.get("bid", []) or payload.get("data", {}).get("bid", [])
    if not bid_list:
        logger.warning("Stockbit orderbook: empty bid list for %s", ticker)
        return 0.0
    price = _parse_number(bid_list[0].get("price"))
    logger.info("Stockbit orderbook: %s bid[0]=%s", ticker, price)
    return price


def _fetch_broker_daily_api(ticker: str, date: str) -> dict:
    """
    Broker summary untuk 1 saham di 1 tanggal langsung dari API (no cache).
    """
    api_data = get_marketdetector_broker_summary(
        ticker=ticker,
        date_from=date,
        date_to=date,
    )

    buy_entries = []
    for entry in api_data.get("brokers_buy", []):
        code = entry.get("broker_code")
        bval = _parse_number(entry.get("bval"))
        buy_entries.append({
            "broker": code,
            "broker_name": _get_broker_name(code),
            "lot": _int_no_decimal(entry.get("blot")),
            "value": int(round(bval)),
            "avg_price": _int_no_decimal(entry.get("netbs_buy_avg_price")),
            "type": entry.get("type"),
        })

    sell_entries = []
    for entry in api_data.get("brokers_sell", []):
        code = entry.get("broker_code")
        sval = _parse_number(entry.get("sval"))
        sell_entries.append({
            "broker": code,
            "broker_name": _get_broker_name(code),
            "lot": _int_no_decimal(entry.get("slot")),
            "value": int(round(sval)),
            "avg_price": _int_no_decimal(entry.get("netbs_sell_avg_price")),
            "type": entry.get("type"),
        })

    foreign_buy = sum(e["value"] for e in buy_entries if e.get("type") == "Asing")
    foreign_sell = sum(e["value"] for e in sell_entries if e.get("type") == "Asing")
    foreign_net = int(foreign_buy - foreign_sell)

    return {
        "ticker": ticker,
        "date": date,
        "buy": sorted(buy_entries, key=lambda x: x["value"], reverse=True),
        "sell": sorted(sell_entries, key=lambda x: x["value"], reverse=True),
        "foreign_net": foreign_net,
    }


def get_broker_daily(ticker: str, date: str) -> dict:
    """
    Broker summary dengan cache-first strategy.
    - History (< today): ambil dari broker_accumulation jika sudah ada.
    - Today: selalu fetch API terbaru lalu upsert.
    - Jika tidak ada di cache, fetch dari API lalu simpan.
    """
    today_str = date_module_today().isoformat()
    is_today = (date == today_str)

    if not is_today:
        cached = get_cached_broker_daily(ticker, date)
        if cached is not None:
            logger.info(f"[cache hit] broker_daily {ticker} {date}")
            return cached

    day_data = _fetch_broker_daily_api(ticker, date)
    save_broker_daily(ticker, date, day_data)
    return day_data


def get_broker_accumulation(ticker: str, days: int) -> dict:
    """
    Agregasi broker summary untuk N hari trading ke belakang.
    Hitung avg price tiap broker = true cost mereka.

    days=7  → timing signal (sedang aktif sekarang?)
    days=30 → true avg cost bandar
    """
    trading_days = _get_trading_days(days, include_today=True)
    date_from = trading_days[-1]
    date_to = trading_days[0]

    # Agregasi dari data harian (cache-first), sehingga history tidak perlu hit API berulang.
    broker_totals: dict = {}
    distribution_totals: dict = {}

    daily_data = {}
    foreign_net = 0
    for date in trading_days:
        try:
            day_data = get_broker_daily(ticker, date)
        except httpx.HTTPStatusError:
            continue

        daily_data[date] = day_data
        foreign_net += day_data.get("foreign_net", 0)

        for entry in day_data.get("buy", []):
            code = entry.get("broker")
            if not code:
                continue
            if code not in broker_totals:
                broker_totals[code] = {
                    "broker_name": entry.get("broker_name") or _get_broker_name(code),
                    "total_buy_lot": 0,
                    "total_buy_value": 0,
                    "active_days": 0,
                    "daily": {},
                    "avg_price": 0,
                }
            broker_totals[code]["total_buy_lot"] += int(entry.get("lot") or 0)
            broker_totals[code]["total_buy_value"] += int(entry.get("value") or 0)
            broker_totals[code]["active_days"] += 1
            broker_totals[code]["daily"][date] = {
                "lot": entry.get("lot"),
                "avg_price": entry.get("avg_price"),
            }
            total_lot = broker_totals[code]["total_buy_lot"]
            total_value = broker_totals[code]["total_buy_value"]
            broker_totals[code]["avg_price"] = int(round(total_value / max(total_lot * 100, 1)))

        for entry in day_data.get("sell", []):
            code = entry.get("broker")
            if not code:
                continue
            if code not in distribution_totals:
                distribution_totals[code] = {
                    "broker_name": entry.get("broker_name") or _get_broker_name(code),
                    "total_sell_lot": 0,
                    "total_sell_value": 0,
                    "active_days": 0,
                    "daily": {},
                    "avg_price": 0,
                    "type": entry.get("type"),
                }
            distribution_totals[code]["total_sell_lot"] += int(entry.get("lot") or 0)
            distribution_totals[code]["total_sell_value"] += int(entry.get("value") or 0)
            distribution_totals[code]["active_days"] += 1
            distribution_totals[code]["daily"][date] = {
                "lot": entry.get("lot"),
                "avg_price": entry.get("avg_price"),
            }
            total_lot = distribution_totals[code]["total_sell_lot"]
            total_value = distribution_totals[code]["total_sell_value"]
            distribution_totals[code]["avg_price"] = int(round(total_value / max(total_lot * 100, 1)))

    sorted_brokers = sorted(
        broker_totals.items(),
        key=lambda x: x[1]["total_buy_value"],
        reverse=True,
    )

    sorted_distributors = sorted(
        distribution_totals.items(),
        key=lambda x: x[1]["total_sell_value"],
        reverse=True,
    )

    top3_sell_total = sum(d[1]["total_sell_value"] for d in sorted_distributors[:3])

    return {
        "ticker": ticker,
        "window_days": days,
        "period": f"{date_from} s/d {date_to}",
        "top_accumulators": sorted_brokers[:5],
        "top_distributors": sorted_distributors[:5],
        "distribution_top3_value": top3_sell_total,
        "bandar_detector": {},
        "daily_summary": daily_data,
        "foreign_net": foreign_net,
    }


def get_full_bandarm_data(ticker: str) -> dict:
    """Ambil kedua window sekaligus untuk 1 saham."""
    return {
        "ticker": ticker,
        "w7": get_broker_accumulation(ticker, days=7),
        "w30": get_broker_accumulation(ticker, days=30),
    }


def _get_base_price(ticker: str) -> float:
    """Base price per ticker untuk mock data yang realistis."""
    return _BASE_PRICES.get(ticker, 2000)


# ============================================================
# OHLCV & Fundamental Data
# ============================================================


@_retry_on_rate_limit(max_attempts=4, base_delay=1.0)
def _fetch_ohlcv_range_api(ticker: str, start_date: str, end_date: str, limit: int = 50) -> pd.DataFrame:
    """
    Ambil data OHLCV langsung dari Stockbit API (no cache).
    """
    api_key = os.getenv("STOCKBIT_API_KEY")
    if not api_key:
        raise ValueError("STOCKBIT_API_KEY is not set")
    url = f"https://exodus.stockbit.com/company-price-feed/historical/summary/{ticker.upper()}"
    params = {
        "period": "HS_PERIOD_DAILY",
        "start_date": start_date,
        "end_date": end_date,
        "limit": str(limit),
        "page": "1",
    }
    headers = {"Authorization": f"Bearer {api_key}"}
    all_data = []
    required_keys = ("date", "open", "high", "low", "close", "volume")
    page = 1
    while True:
        page_params = params.copy()
        page_params["page"] = str(page)
        response = httpx.get(url, params=page_params, headers=headers, timeout=30.0)
        response.raise_for_status()
        payload = response.json()
        data = payload.get("data", {})
        result = data.get("result", [])
        if not result:
            break
        valid_items = [
            item for item in result
            if isinstance(item, dict) and all(k in item for k in required_keys)
        ]
        all_data.extend(valid_items)
        paginate = data.get("paginate", {})
        next_page = paginate.get("next_page")
        if not next_page:
            break
        page += 1

    # Hari libur bursa / data tidak tersedia: kembalikan DataFrame kosong tanpa warning keras.
    if not all_data:
        return pd.DataFrame(columns=["Open", "High", "Low", "Close", "Volume"])

    df = pd.DataFrame([
        {
            "Date": pd.to_datetime(item["date"]),
            "Open": float(item["open"]),
            "High": float(item["high"]),
            "Low": float(item["low"]),
            "Close": float(item["close"]),
            "Volume": float(item["volume"]),
        }
        for item in all_data if all(k in item for k in required_keys)
    ])
    if df.empty or "Date" not in df.columns:
        return pd.DataFrame(columns=["Open", "High", "Low", "Close", "Volume"])
    df.set_index("Date", inplace=True)
    df = df.sort_index()
    return df


def get_ohlcv_range(ticker: str, start_date: str, end_date: str, limit: int = 50) -> pd.DataFrame:
    """
    Ambil OHLCV dengan cache-first strategy.
    - History (< today): ambil dari DB, fetch API hanya untuk tanggal yang belum ada.
    - Today: selalu di-upsert dari API.
    """
    today = date.today()
    cached = get_cached_ohlcv(ticker, start_date, end_date)
    missing = find_missing_dates(cached, start_date, end_date)

    if not missing:
        logger.info(f"[cache hit] OHLCV {ticker} {start_date}..{end_date}")
        return cached

    # Fetch hanya rentang yang belum ada
    new_frames = [cached] if not cached.empty else []
    for range_start, range_end in group_into_ranges(missing):
        try:
            df_new = _fetch_ohlcv_range_api(
                ticker, range_start.isoformat(), range_end.isoformat(), limit
            )
            if not df_new.empty:
                save_ohlcv(ticker, df_new, today)
                new_frames.append(df_new)
        except Exception as e:
            logger.warning(f"[fetcher_stockbit] get_ohlcv_range {ticker} {range_start}..{range_end}: {e}")

    if not new_frames:
        return pd.DataFrame()
    result = pd.concat(new_frames).sort_index()
    result = result[~result.index.duplicated(keep="last")]
    return result


def get_ohlcv(ticker: str, period: str = "3mo") -> pd.DataFrame:
    """
    Backward compatible: tetap bisa pakai period string.
    """
    period_days = {"1mo": 22, "3mo": 66, "6mo": 132, "1y": 252}.get(period, 22)
    end_date = datetime.now().date()
    start_date = end_date
    days_added = 0
    while days_added < period_days:
        start_date -= timedelta(days=1)
        if start_date.weekday() < 5:
            days_added += 1
    return get_ohlcv_range(ticker, start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))


@_retry_on_rate_limit(max_attempts=4, base_delay=1.0)
def _fetch_stock_info_api(ticker: str) -> dict:
    """Ambil fundamental langsung dari Stockbit API (no cache)."""
    api_key = os.getenv("STOCKBIT_API_KEY")
    if not api_key:
        raise ValueError("STOCKBIT_API_KEY is not set")
    url = f"https://exodus.stockbit.com/keystats/ratio/v1/{ticker.upper()}?year_limit=10"
    headers = {"Authorization": f"Bearer {api_key}"}
    with httpx.Client(timeout=15.0) as client:
        response = client.get(url, headers=headers)
        response.raise_for_status()
        payload = response.json()
    data = payload.get("data", {})
    # Extract dividend yield history from financial_year_parent
    dividend_yield_history = []
    fy_parent = data.get("financial_year_parent", {})
    # Extract historical Net Income, EPS, Revenue from annualised_value if available
    net_income_history = []
    eps_history = []
    revenue_history = []
    for group in fy_parent.get("financial_year_groups", []):
        # Dividend yield history (all groups)
        for val in group.get("financial_year_values", []):
            year = val.get("year")
            dy = val.get("dividend_yield")
            if dy is not None and year:
                try:
                    dy_val = float(str(dy).replace("%", "").replace(",", ""))
                    dividend_yield_history.append({"year": year, "value": dy_val})
                except Exception:
                    continue
        # Net Income: only from group with fitem_name == 'Net Income'
        if group.get("fitem_name") == "Net Income":
            for val in group.get("financial_year_values", []):
                year = val.get("year")
                net_income_ann = val.get("annualised_value")
                if net_income_ann is not None and year:
                    try:
                        ni_val = float(str(net_income_ann).replace(",", "").replace(" B", ""))
                        net_income_history.append({"year": year, "value": ni_val})
                    except Exception:
                        pass
        # EPS: only from group with fitem_name == 'EPS'
        if group.get("fitem_name") == "EPS":
            for val in group.get("financial_year_values", []):
                year = val.get("year")
                eps_ann = val.get("annualised_value")
                if eps_ann is not None and year:
                    try:
                        eps_val = float(str(eps_ann).replace(",", ""))
                        eps_history.append({"year": year, "value": eps_val})
                    except Exception:
                        pass
        # Revenue: only from group with fitem_name == 'Revenue'
        if group.get("fitem_name") == "Revenue":
            for val in group.get("financial_year_values", []):
                year = val.get("year")
                revenue_ann = val.get("annualised_value")
                if revenue_ann is not None and year:
                    try:
                        rev_val = float(str(revenue_ann).replace(",", "").replace(" B", ""))
                        revenue_history.append({"year": year, "value": rev_val})
                    except Exception:
                        pass
    """
    Generate fundamental info yang realistis per ticker.
    Deterministic: same ticker = same data.
    """
    rng = random.Random(hash(f"{ticker}_info") % 2**32)
    base_price = _get_base_price(ticker)
    mcap = None
    def _find_fin_item_value(closure_fin_items_results, name):
        if not isinstance(closure_fin_items_results, list):
            return None
        for group in closure_fin_items_results:
            fin_name_results = group.get("fin_name_results", [])
            for fin in fin_name_results:
                fitem = fin.get("fitem", {})
                if fitem.get("name", "").strip().lower() == name.strip().lower():
                    val = fitem.get("value")
                    # Remove commas and percent, convert to float if possible
                    if isinstance(val, str):
                        val = val.replace(",", "").replace("%", "")
                    try:
                        return float(val)
                    except (TypeError, ValueError):
                        return None
        return None

    api_key = os.getenv("STOCKBIT_API_KEY")
    if not api_key:
        raise ValueError("STOCKBIT_API_KEY is not set")
    url = f"https://exodus.stockbit.com/keystats/ratio/v1/{ticker.upper()}?year_limit=10"
    headers = {"Authorization": f"Bearer {api_key}"}
    with httpx.Client(timeout=15.0) as client:
        response = client.get(url, headers=headers)
        response.raise_for_status()
        payload = response.json()
    data = payload.get("data", {})
    closure_fin_items_results = data.get("closure_fin_items_results", [])
    # Ambil market cap dari data['stats']['market_cap']
    stats = data.get("stats", {})
    mcap_str = stats.get("market_cap")
    if not mcap_str:
        raise ValueError(f"Market cap tidak ditemukan untuk {ticker}")
    try:
        mcap = float(mcap_str.replace(",", "").replace("B", "")) * 1e9 if "B" in mcap_str else float(mcap_str.replace(",", ""))
    except Exception:
        raise ValueError(f"Market cap tidak valid untuk {ticker}: {mcap_str}")
    # Ambil current price dari orderbook
    current_price = get_current_price_stockbit(ticker)
    # 52w high/low
    high_52w = None
    low_52w = None
    for group in closure_fin_items_results:
        fin_name_results = group.get("fin_name_results", [])
        for fin in fin_name_results:
            fitem = fin.get("fitem", {})
            fname = fitem.get("name", "").strip().lower()
            if fname == "52 week high":
                try:
                    high_52w = float(fitem.get("value", "").replace(",", ""))
                except Exception:
                    pass
            if fname == "52 week low":
                try:
                    low_52w = float(fitem.get("value", "").replace(",", ""))
                except Exception:
                    pass
    # Fundamental dari closure_fin_items_results
    per = _find_fin_item_value(closure_fin_items_results, "Current PE Ratio (Annualised)")
    pbv = _find_fin_item_value(closure_fin_items_results, "Current Price to Book Value")
    roe = _find_fin_item_value(closure_fin_items_results, "Return on Equity (TTM)")
    der = _find_fin_item_value(closure_fin_items_results, "Debt to Equity Ratio (Quarter)")
    rev_growth = _find_fin_item_value(closure_fin_items_results, "Revenue (Quarter YoY Growth)")
    earn_growth = _find_fin_item_value(closure_fin_items_results, "Net Income (Quarter YoY Growth)")
    # === Dividend Data Extraction ===
    dividend_yield = _find_fin_item_value(closure_fin_items_results, "Dividend Yield")
    dividend_payout_ratio = _find_fin_item_value(closure_fin_items_results, "Dividend Payout Ratio")
    dividend_per_share = _find_fin_item_value(closure_fin_items_results, "Dividend per Share")
    # Extract 5-year historical data for all main metrics
    historical = {
        "per": [],
        "pbv": [],
        "roe": [],
        "der": [],
        "revenue_growth": [],
        "earnings_growth": [],
        "dividend_yield": [],
        "net_income": net_income_history,
        "eps": eps_history,
        "revenue": revenue_history,
    }
    for group in closure_fin_items_results:
        year = group.get("year") or group.get("period")
        fin_name_results = group.get("fin_name_results", [])
        values = {}
        for fin in fin_name_results:
            fitem = fin.get("fitem", {})
            fname = fitem.get("name", "").strip().lower()
            val = fitem.get("value")
            if isinstance(val, str):
                val = val.replace(",", "").replace("%", "")
            try:
                val = float(val)
            except (TypeError, ValueError):
                continue
            values[fname] = val
        # Map to historical keys if present
        if year:
            if "current pe ratio (annualised)" in values:
                historical["per"].append({"year": year, "value": values["current pe ratio (annualised)"]})
            if "current price to book value" in values:
                historical["pbv"].append({"year": year, "value": values["current price to book value"]})
            if "return on equity (ttm)" in values:
                historical["roe"].append({"year": year, "value": values["return on equity (ttm)"]})
            if "debt to equity ratio (quarter)" in values:
                historical["der"].append({"year": year, "value": values["debt to equity ratio (quarter)"]})
            if "revenue (quarter yoy growth)" in values:
                historical["revenue_growth"].append({"year": year, "value": values["revenue (quarter yoy growth)"]})
            if "net income (quarter yoy growth)" in values:
                historical["earnings_growth"].append({"year": year, "value": values["net income (quarter yoy growth)"]})
            if "dividend yield" in values:
                historical["dividend_yield"].append({"year": year, "value": values["dividend yield"]})
            if "net income" in values:
                historical["net_income"].append({"year": year, "value": values["net income"]})
            if "eps" in values:
                historical["eps"].append({"year": year, "value": values["eps"]})
            if "revenue" in values:
                historical["revenue"].append({"year": year, "value": values["revenue"]})
    # Raise error jika ada field penting yang None
    if high_52w is None or low_52w is None:
        raise ValueError(f"52w high/low tidak ditemukan untuk {ticker}")
    if per is None:
        raise ValueError(f"PER tidak ditemukan untuk {ticker}")
    if pbv is None:
        raise ValueError(f"PBV tidak ditemukan untuk {ticker}")
    if roe is None:
        raise ValueError(f"ROE tidak ditemukan untuk {ticker}")
    # DER boleh None jika tidak ditemukan (misal bank)
    # if der is None:
    #     raise ValueError(f"DER tidak ditemukan untuk {ticker}")
    if rev_growth is None:
        raise ValueError(f"Revenue growth tidak ditemukan untuk {ticker}")
    if earn_growth is None:
        raise ValueError(f"Earnings growth tidak ditemukan untuk {ticker}")
    return {
        "ticker": ticker,
        "per": round(per, 2),
        "pbv": round(pbv, 2),
        "market_cap": mcap,
        "roe": round(roe, 4),
        "der": round(der, 2) if der is not None else None,
        "revenue_growth": round(rev_growth, 4),
        "earnings_growth": round(earn_growth, 4),
        "current_price": round(current_price, 0),
        "52w_high": round(float(high_52w), 0),
        "52w_low": round(float(low_52w), 0),
        "dividend_yield": round(dividend_yield, 4) if dividend_yield is not None else None,
        "dividend_payout_ratio": round(dividend_payout_ratio, 4) if dividend_payout_ratio is not None else None,
        "dividend_per_share": round(dividend_per_share, 4) if dividend_per_share is not None else None,
        "history": {**historical, "dividend_yield": dividend_yield_history},
    }


def get_stock_info(ticker: str) -> dict:
    """
    Ambil fundamental dengan cache-first strategy.
    - Today: cek DB dulu, jika ada return dari cache (upsert saat save).
    - Jika tidak ada di cache, fetch dari API lalu simpan.
    """
    today_str = date.today().isoformat()
    cached = get_cached_stock_info(ticker, today_str)
    if cached is not None:
        logger.info(f"[cache hit] stock_info {ticker} {today_str}")
        return cached

    data = _fetch_stock_info_api(ticker)
    save_stock_info(ticker, today_str, data)
    return data


def get_multiple_ohlcv(tickers: list[str], period: str = "3mo") -> dict[str, pd.DataFrame]:
    """Ambil OHLCV untuk banyak saham sekaligus."""
    return {ticker: get_ohlcv(ticker, period) for ticker in tickers}
