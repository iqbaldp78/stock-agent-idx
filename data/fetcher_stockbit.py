"""
Data Fetcher — Stockbit (Mock)
Mengambil data broker summary, OHLCV, dan fundamental saham.
Saat ini menggunakan mock data yang deterministik (random.seed berdasarkan ticker+date).

Menyediakan:
  - get_ohlcv()       → OHLCV DataFrame
  - get_stock_info()  → fundamental info dict
  - Broker summary + avg price per broker

Window:
  - 7 hari  → timing signal (sedang aktif akumulasi?)
  - 30 hari → true avg cost bandar
"""
import random
import pandas as pd
import numpy as np
from datetime import datetime, timedelta


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


def _generate_mock_price(base_price: float) -> float:
    """Generate harga acak di sekitar base price."""
    return round(base_price * random.uniform(0.95, 1.05), 0)


def get_broker_daily(ticker: str, date: str) -> dict:
    """
    Broker summary untuk 1 saham di 1 tanggal.
    MOCK: Generate data random yang realistis.
    """
    random.seed(hash(f"{ticker}{date}") % 2**32)

    base_price = _get_base_price(ticker)
    num_buyers = random.randint(3, 7)
    num_sellers = random.randint(3, 7)

    buyers = random.sample(BROKER_LIST, num_buyers)
    sellers = random.sample(BROKER_LIST, num_sellers)

    buy_entries = []
    for broker_code, broker_name in buyers:
        lot = random.randint(1000, 20000)
        avg_price = _generate_mock_price(base_price)
        value = int(lot * 100 * avg_price)
        buy_entries.append({
            "broker": broker_code,
            "broker_name": broker_name,
            "lot": lot,
            "value": value,
            "avg_price": avg_price,
        })

    sell_entries = []
    for broker_code, broker_name in sellers:
        lot = random.randint(1000, 15000)
        avg_price = _generate_mock_price(base_price)
        value = int(lot * 100 * avg_price)
        sell_entries.append({
            "broker": broker_code,
            "broker_name": broker_name,
            "lot": lot,
            "value": value,
            "avg_price": avg_price,
        })

    total_buy = sum(e["value"] for e in buy_entries)
    total_sell = sum(e["value"] for e in sell_entries)
    foreign_net = int((total_buy - total_sell) * random.uniform(0.3, 0.7))

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
    daily_data = {d: get_broker_daily(ticker, d) for d in trading_days}

    broker_totals: dict = {}
    for date, data in daily_data.items():
        for entry in data["buy"]:
            b = entry["broker"]
            if b not in broker_totals:
                broker_totals[b] = {
                    "broker_name": entry["broker_name"],
                    "total_buy_lot": 0,
                    "total_buy_value": 0,
                    "active_days": 0,
                    "daily": {},
                }
            broker_totals[b]["total_buy_lot"] += entry["lot"]
            broker_totals[b]["total_buy_value"] += entry["value"]
            broker_totals[b]["active_days"] += 1
            broker_totals[b]["daily"][date] = {
                "lot": entry["lot"],
                "avg_price": entry["avg_price"],
            }

    # Hitung weighted avg price per broker
    for b, data in broker_totals.items():
        if data["total_buy_lot"] > 0:
            data["avg_price"] = round(
                data["total_buy_value"] / (data["total_buy_lot"] * 100), 2
            )
        else:
            data["avg_price"] = 0

    sorted_brokers = sorted(
        broker_totals.items(),
        key=lambda x: x[1]["total_buy_value"],
        reverse=True,
    )

    foreign_net = sum(d["foreign_net"] for d in daily_data.values())

    return {
        "ticker": ticker,
        "window_days": days,
        "period": f"{trading_days[-1]} s/d {trading_days[0]}",
        "top_accumulators": sorted_brokers[:5],
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
