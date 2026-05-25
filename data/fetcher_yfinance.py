"""
Data Fetcher — yfinance
Mengambil OHLCV dan info fundamental dari Yahoo Finance.
"""
import yfinance as yf
import pandas as pd
from config import to_yahoo_ticker


def get_ohlcv(ticker: str, period: str = "3mo") -> pd.DataFrame:
    """Ambil data OHLCV untuk 1 saham."""
    df = yf.download(to_yahoo_ticker(ticker), period=period, progress=False)
    # Flatten multi-level columns dari yfinance
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df


def get_stock_info(ticker: str) -> dict:
    """Ambil info fundamental dari Yahoo Finance."""
    try:
        info = yf.Ticker(to_yahoo_ticker(ticker)).info
    except Exception:
        info = {}

    return {
        "ticker": ticker,
        "per": info.get("trailingPE"),
        "pbv": info.get("priceToBook"),
        "market_cap": info.get("marketCap"),
        "roe": info.get("returnOnEquity"),
        "der": info.get("debtToEquity"),
        "revenue_growth": info.get("revenueGrowth"),
        "earnings_growth": info.get("earningsGrowth"),
        "current_price": info.get("currentPrice"),
        "52w_high": info.get("fiftyTwoWeekHigh"),
        "52w_low": info.get("fiftyTwoWeekLow"),
    }


def get_multiple_ohlcv(tickers: list[str], period: str = "3mo") -> dict[str, pd.DataFrame]:
    """Ambil OHLCV untuk banyak saham sekaligus."""
    result = {}
    for ticker in tickers:
        try:
            df = get_ohlcv(ticker, period)
            if not df.empty:
                result[ticker] = df
        except Exception:
            continue
    return result
