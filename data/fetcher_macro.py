"""
Data Fetcher — Macro
Mengambil data makro: IHSG, USD/IDR, volatilitas pasar.
"""
import yfinance as yf
import pandas as pd
from datetime import date, datetime, timedelta

from db.cache import (
    get_cached_sector_ohlcv,
    save_sector_ohlcv,
    find_missing_dates,
    group_into_ranges,
)


def _calculate_vs_ma(ticker_obj, period: int = 20) -> float | None:
    """Hitung posisi harga vs MA."""
    try:
        hist = ticker_obj.history(period="3mo")
        if hist.empty or len(hist) < period:
            return None
        ma = hist["Close"].rolling(period).mean().iloc[-1]
        current = hist["Close"].iloc[-1]
        return round((current - ma) / ma * 100, 2)
    except Exception:
        return None

def _get_usdidr_trend() -> dict:
    """Mengambil pergerakan day-by-day USD/IDR selama 1 bulan menggunakan endpoint non-yfinance."""
    try:
        import requests
        url = "https://query1.finance.yahoo.com/v8/finance/chart/USDIDR=X?range=1mo&interval=1d"
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(url, headers=headers, timeout=5)
        data = resp.json()
        result = data["chart"]["result"][0]
        closes = result["indicators"]["quote"][0]["close"]
        
        # Filter out None values
        valid_closes = [c for c in closes if c is not None]
        
        if len(valid_closes) >= 2:
            current = valid_closes[-1]
            prev = valid_closes[-2]
            month_ago = valid_closes[0]
            
            day_change_pct = (current - prev) / prev * 100
            month_change_pct = (current - month_ago) / month_ago * 100
            
            return {
                "usdidr_1d_change_pct": round(day_change_pct, 2),
                "usdidr_1m_change_pct": round(month_change_pct, 2),
                "trend_narrative": f"Naik {day_change_pct:.2f}% (harian)" if day_change_pct > 0 else f"Turun {abs(day_change_pct):.2f}% (harian)"
            }
    except Exception as e:
        print(f"[DEBUG] _get_usdidr_trend error: {e}")
    
    return {
        "usdidr_1d_change_pct": 0.0,
        "usdidr_1m_change_pct": 0.0,
        "trend_narrative": "Tidak tersedia"
    }


def get_macro_data() -> dict:
    """Ambil data makro pasar Indonesia."""
    try:
        ihsg = yf.Ticker("^JKSE")
        ihsg_info = ihsg.info
        ihsg_price = ihsg_info.get("regularMarketPrice")
        ihsg_change_pct = ihsg_info.get("regularMarketChangePercent", 0)
    except Exception:
        ihsg = None
        ihsg_price = None
        ihsg_change_pct = 0

    try:
        import requests
        resp = requests.get("https://open.er-api.com/v6/latest/USD", timeout=5)
        usdidr_price = resp.json()["rates"]["IDR"]
    except Exception:
        try:
            usdidr = yf.Ticker("USDIDR=X")
            usdidr_price = usdidr.info.get("regularMarketPrice")
        except Exception:
            usdidr_price = None

    ihsg_vs_ma20 = _calculate_vs_ma(ihsg, 20) if ihsg else None
    is_volatile = abs(ihsg_change_pct or 0) > 1.5

    usdidr_trend = _get_usdidr_trend()

    return {
        "ihsg_price": ihsg_price,
        "ihsg_change_pct": ihsg_change_pct,
        "usdidr": usdidr_price,
        "usdidr_1d_change_pct": usdidr_trend["usdidr_1d_change_pct"],
        "usdidr_1m_change_pct": usdidr_trend["usdidr_1m_change_pct"],
        "usdidr_trend_narrative": usdidr_trend["trend_narrative"],
        "ihsg_vs_ma20": ihsg_vs_ma20,
        "is_volatile": is_volatile,
    }


_SECTOR_CACHE = {}
_SECTOR_CACHE_TIME = None

def get_sector_outlook() -> dict:
    """
    Outlook per sektor berdasarkan indeks sektoral (diambil dari data rotasi).
    In-memory TTL 1 jam untuk menghindari DB query berulang dalam 1 sesi.
    """
    global _SECTOR_CACHE, _SECTOR_CACHE_TIME

    # Return in-memory cache jika masih fresh (< 1 jam)
    if _SECTOR_CACHE and _SECTOR_CACHE_TIME:
        age = datetime.now() - _SECTOR_CACHE_TIME
        if age < timedelta(hours=1):
            print(f"[DEBUG] Returning in-memory sector outlook (age: {age.total_seconds():.0f}s)")
            return _SECTOR_CACHE

    from data.fetcher_ihsg import get_sector_rotation
    
    rot = get_sector_rotation()
    outlook = {}
    
    for sector_name, data in rot.get("sectors", {}).items():
        change_5d = data.get("5d_return", 0.0)
        print(f"[DEBUG] {sector_name} change_5d: {change_5d:.2f}%")
        if change_5d > 2.0:
            outlook[sector_name] = "POSITIF"
        elif change_5d < -2.0:
            outlook[sector_name] = "NEGATIF"
        else:
            outlook[sector_name] = "NETRAL"

    # Cache in-memory
    _SECTOR_CACHE = outlook
    _SECTOR_CACHE_TIME = datetime.now()

    return outlook
