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
from datetime import datetime, timedelta

import httpx
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


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


def _get_trading_days(days: int) -> list[str]:
    """Hitung N hari trading ke belakang (skip weekend)."""
    result = []
    current = datetime.now()
    while len(result) < days:
        current -= timedelta(days=1)
        if current.weekday() < 5:  # Mon-Fri
            result.append(current.strftime("%Y-%m-%d"))
    return result


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


def get_broker_daily(ticker: str, date: str) -> dict:
    """
    Broker summary untuk 1 saham di 1 tanggal.
    Real data dari Stockbit marketdetector endpoint.
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


def get_broker_accumulation(ticker: str, days: int) -> dict:
    """
    Agregasi broker summary untuk N hari trading ke belakang.
    Hitung avg price tiap broker = true cost mereka.

    days=7  → timing signal (sedang aktif sekarang?)
    days=30 → true avg cost bandar
    """
    trading_days = _get_trading_days(days)
    date_from = trading_days[-1]
    date_to = trading_days[0]

    window_data = get_marketdetector_broker_summary(
        ticker=ticker,
        date_from=date_from,
        date_to=date_to,
        limit=10,
    )

    broker_totals: dict = {}
    for entry in window_data.get("brokers_buy", []):
        code = entry.get("broker_code")
        if not code:
            continue
        broker_totals[code] = {
            "broker_name": _get_broker_name(code),
            "total_buy_lot": _int_no_decimal(entry.get("blot")),
            "total_buy_value": int(round(_parse_number(entry.get("bval")))),
            "active_days": 0,
            "daily": {},
            "avg_price": _int_no_decimal(entry.get("netbs_buy_avg_price")),
        }

    distribution_totals: dict = {}
    for entry in window_data.get("brokers_sell", []):
        code = entry.get("broker_code")
        if not code:
            continue
        sval = abs(_parse_number(entry.get("sval")))
        distribution_totals[code] = {
            "broker_name": _get_broker_name(code),
            "total_sell_lot": _int_no_decimal(entry.get("slot")),
            "total_sell_value": int(round(sval)),
            "active_days": 0,
            "daily": {},
            "avg_price": _int_no_decimal(entry.get("netbs_sell_avg_price")),
            "type": entry.get("type"),
        }

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
            if code not in broker_totals:
                continue
            broker_totals[code]["active_days"] += 1
            broker_totals[code]["daily"][date] = {
                "lot": entry.get("lot"),
                "avg_price": entry.get("avg_price"),
            }

        for entry in day_data.get("sell", []):
            code = entry.get("broker")
            if code not in distribution_totals:
                continue
            distribution_totals[code]["active_days"] += 1
            distribution_totals[code]["daily"][date] = {
                "lot": entry.get("lot"),
                "avg_price": entry.get("avg_price"),
            }

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
        "bandar_detector": window_data.get("bandar_detector", {}),
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

def get_ohlcv(ticker: str, period: str = "3mo") -> pd.DataFrame:
    """
    Generate OHLCV data yang realistis untuk saham IDX.
    Deterministic berdasarkan ticker (same ticker = same data).
    """
    base_price = _get_base_price(ticker)

    # Determine number of trading days from period
    period_days = {"1mo": 22, "3mo": 66, "6mo": 132, "1y": 252}.get(period, 22)

    # Generate trading days (exclude weekends)
    dates = []
    current = datetime.now()
    while len(dates) < period_days:
        current -= timedelta(days=1)
        if current.weekday() < 5:
            dates.append(current)
    dates.reverse()

    # Deterministic random walk for price
    rng = random.Random(hash(f"{ticker}_ohlcv") % 2**32)
    prices = []
    price = base_price * rng.uniform(0.90, 0.98)  # start slightly below base

    for _ in range(period_days):
        # Daily return: slight upward bias with volatility
        daily_return = rng.gauss(0.001, 0.02)  # mean 0.1%, std 2%
        price *= (1 + daily_return)
        price = max(price, base_price * 0.7)  # floor

        high = price * rng.uniform(1.005, 1.03)
        low = price * rng.uniform(0.97, 0.995)
        open_p = rng.uniform(low, high)
        close = rng.uniform(low, high)

        # Volume based on market cap (bigger stock = more volume)
        mcap = _MARKET_CAPS.get(ticker, 30_000_000_000_000)
        base_vol = max(1_000_000, int(mcap / base_price / 500))
        volume = int(base_vol * rng.uniform(0.5, 2.5))

        prices.append({
            "Open": round(open_p, 0),
            "High": round(high, 0),
            "Low": round(low, 0),
            "Close": round(close, 0),
            "Volume": volume,
        })

    df = pd.DataFrame(prices, index=pd.DatetimeIndex(dates))
    df.index.name = "Date"
    return df


def get_stock_info(ticker: str) -> dict:
    """
    Generate fundamental info yang realistis per ticker.
    Deterministic: same ticker = same data.
    """
    rng = random.Random(hash(f"{ticker}_info") % 2**32)
    base_price = _get_base_price(ticker)
    mcap = _MARKET_CAPS.get(ticker, 30_000_000_000_000)

    # Generate realistic fundamentals based on sector heuristics
    per = rng.uniform(8, 35)
    pbv = rng.uniform(0.8, 5.0)
    roe = rng.uniform(0.05, 0.25)
    der = rng.uniform(0.2, 2.5)
    rev_growth = rng.uniform(-0.05, 0.30)
    earn_growth = rng.uniform(-0.10, 0.40)

    try:
        current_price = get_current_price_stockbit(ticker)
    except (httpx.HTTPError, ValueError):
        current_price = base_price * rng.uniform(0.95, 1.05)
    high_52w = current_price * rng.uniform(1.10, 1.40)
    low_52w = current_price * rng.uniform(0.60, 0.90)

    return {
        "ticker": ticker,
        "per": round(per, 2),
        "pbv": round(pbv, 2),
        "market_cap": mcap,
        "roe": round(roe, 4),
        "der": round(der, 2),
        "revenue_growth": round(rev_growth, 4),
        "earnings_growth": round(earn_growth, 4),
        "current_price": round(current_price, 0),
        "52w_high": round(high_52w, 0),
        "52w_low": round(low_52w, 0),
    }


def get_multiple_ohlcv(tickers: list[str], period: str = "3mo") -> dict[str, pd.DataFrame]:
    """Ambil OHLCV untuk banyak saham sekaligus."""
    return {ticker: get_ohlcv(ticker, period) for ticker in tickers}
