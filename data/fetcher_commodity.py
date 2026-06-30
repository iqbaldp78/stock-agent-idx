"""
Commodity Price Fetcher — Real-time harga komoditi global
Menggunakan yfinance untuk futures & indices.
"""
import logging
from datetime import datetime, timedelta
import yfinance as yf
import pandas as pd
from functools import lru_cache
import time

from data.commodity_mapper import (
    COMMODITY_TO_TICKERS,
    get_commodities_for_ticker,
)

logger = logging.getLogger(__name__)

# Cache dengan TTL 1 jam
_PRICE_CACHE = {}
_CACHE_TTL = 3600  # seconds


def _get_cache_key(symbol: str, period: str = "1d") -> str:
    return f"{symbol}:{period}"


def _is_cache_valid(timestamp: float) -> bool:
    return (time.time() - timestamp) < _CACHE_TTL


@lru_cache(maxsize=128)
def get_commodity_price(commodity: str, period: str = "1d") -> dict:
    """
    Ambil harga komoditi terkini + historical data.

    Args:
        commodity: nama komoditi (e.g., 'gold', 'coal', 'oil')
        period: historical period ('1d', '5d', '1mo', '3mo', '1y')

    Returns:
        {
            "commodity": "gold",
            "symbol": "GC=F",
            "current_price": 2050.50,
            "change_percent": +1.23,
            "change_value": +25.00,
            "timestamp": "2026-06-29 14:45:00",
            "currency": "USD/Oz",
            "high_52w": 2150.00,
            "low_52w": 1850.00,
            "related_tickers": ["ANTM"],
            "period_data": {...}  # OHLCV DataFrame
        }
    """
    if commodity not in COMMODITY_TO_TICKERS:
        logger.warning(f"Unknown commodity: {commodity}")
        return {}

    cache_key = _get_cache_key(commodity, period)
    if cache_key in _PRICE_CACHE:
        cached_data, timestamp = _PRICE_CACHE[cache_key]
        if _is_cache_valid(timestamp):
            logger.info(f"[CACHE HIT] Commodity price: {commodity}")
            return cached_data

    try:
        commodity_info = COMMODITY_TO_TICKERS[commodity]
        symbol = commodity_info["symbol"]

        # Fetch data from yfinance
        ticker = yf.Ticker(symbol)

        # Get current price
        current_data = ticker.info
        current_price = current_data.get("currentPrice") or current_data.get("regularMarketPrice", 0)

        # Get historical data
        hist = ticker.history(period=period)

        if hist.empty:
            logger.warning(f"No data for commodity: {commodity} ({symbol})")
            return {}

        # Calculate metrics
        latest = hist.iloc[-1]
        previous = hist.iloc[-2] if len(hist) > 1 else latest

        change_value = latest["Close"] - previous["Close"]
        change_percent = (change_value / previous["Close"] * 100) if previous["Close"] != 0 else 0

        # 52-week highs/lows
        year_data = ticker.history(period="1y")
        high_52w = year_data["High"].max() if not year_data.empty else current_price
        low_52w = year_data["Low"].min() if not year_data.empty else current_price

        result = {
            "commodity": commodity,
            "name": commodity_info["name"],
            "symbol": symbol,
            "current_price": round(latest["Close"], 2),
            "change_value": round(change_value, 2),
            "change_percent": round(change_percent, 2),
            "timestamp": str(datetime.now()),
            "currency": commodity_info["currency"],
            "high_52w": round(high_52w, 2),
            "low_52w": round(low_52w, 2),
            "exposure": commodity_info["exposure"],
            "related_tickers": commodity_info["tickers"],
            "period_data": {
                "open": round(latest["Open"], 2),
                "high": round(latest["High"], 2),
                "low": round(latest["Low"], 2),
                "close": round(latest["Close"], 2),
                "volume": int(latest.get("Volume", 0)),
            }
        }

        # Cache result
        _PRICE_CACHE[cache_key] = (result, time.time())

        logger.info(
            f"[{commodity.upper()}] {result['symbol']} → "
            f"${result['current_price']} ({result['change_percent']:+.2f}%)"
        )

        return result

    except Exception as e:
        logger.error(f"Error fetching commodity price for {commodity}: {e}")
        return {}


def get_all_commodity_prices(period: str = "1d") -> dict:
    """Get harga untuk semua komoditi yang di-track."""
    prices = {}
    for commodity in COMMODITY_TO_TICKERS.keys():
        price_data = get_commodity_price(commodity, period)
        if price_data:
            prices[commodity] = price_data
    return prices


def get_ticker_commodities_prices(ticker: str, period: str = "1d") -> dict:
    """
    Get harga semua komoditi yang terkait dengan ticker tertentu.
    Misal: ANTM -> Gold price
    """
    commodities = get_commodities_for_ticker(ticker)
    result = {
        "ticker": ticker,
        "commodities": []
    }

    for commodity_info in commodities:
        commodity = commodity_info["commodity"]
        price_data = get_commodity_price(commodity, period)
        if price_data:
            result["commodities"].append({
                **commodity_info,
                "price": price_data
            })

    return result


def clear_commodity_cache():
    """Clear semua commodity price cache."""
    global _PRICE_CACHE
    _PRICE_CACHE = {}
    # Also clear lru_cache
    get_commodity_price.cache_clear()
    logger.info("Commodity price cache cleared")


def format_commodity_for_display(commodity_data: dict) -> str:
    """Format commodity data untuk display."""
    if not commodity_data:
        return ""

    return (
        f"{commodity_data['name']} ({commodity_data['symbol']})\n"
        f"  Price: {commodity_data['currency']} {commodity_data['current_price']}\n"
        f"  Change: {commodity_data['change_percent']:+.2f}% ({commodity_data['change_value']:+.2f})\n"
        f"  52W Range: {commodity_data['low_52w']} - {commodity_data['high_52w']}\n"
        f"  Related: {', '.join(commodity_data['related_tickers'])}\n"
        f"  Updated: {commodity_data['timestamp']}"
    )
