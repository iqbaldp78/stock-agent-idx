"""
Data Fetcher — Macro
Mengambil data makro: IHSG, USD/IDR, volatilitas pasar.
"""
import yfinance as yf
import pandas as pd


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
        usdidr = yf.Ticker("USDIDR=X")
        usdidr_price = usdidr.info.get("regularMarketPrice")
    except Exception:
        usdidr_price = None

    ihsg_vs_ma20 = _calculate_vs_ma(ihsg, 20) if ihsg else None
    is_volatile = abs(ihsg_change_pct or 0) > 1.5

    return {
        "ihsg_price": ihsg_price,
        "ihsg_change_pct": ihsg_change_pct,
        "usdidr": usdidr_price,
        "ihsg_vs_ma20": ihsg_vs_ma20,
        "is_volatile": is_volatile,
    }


def get_sector_outlook() -> dict:
    """Outlook per sektor berdasarkan indeks sektoral."""
    sectors = {
        "perbankan": "^JKFINA",
        "mining": "^JKMING",
        "consumer": "^JKCONS",
        "infrastructure": "^JKINFR",
        "property": "^JKPROP",
    }

    outlook = {}
    for sector_name, idx_ticker in sectors.items():
        try:
            ticker = yf.Ticker(idx_ticker)
            hist = ticker.history(period="1mo")
            if not hist.empty and len(hist) >= 5:
                change_5d = (hist["Close"].iloc[-1] - hist["Close"].iloc[-5]) / hist["Close"].iloc[-5] * 100
                if change_5d > 2:
                    outlook[sector_name] = "POSITIF"
                elif change_5d < -2:
                    outlook[sector_name] = "NEGATIF"
                else:
                    outlook[sector_name] = "NETRAL"
            else:
                outlook[sector_name] = "NETRAL"
        except Exception:
            outlook[sector_name] = "NETRAL"

    return outlook
