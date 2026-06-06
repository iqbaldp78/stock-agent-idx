"""
Data Fetcher — yfinance
Mengambil OHLCV dan info fundamental dari Yahoo Finance.
"""
import yfinance as yf
import pandas as pd
from datetime import date, timedelta

from config import to_yahoo_ticker
from db.cache import (
    get_cached_ohlcv,
    save_ohlcv,
    find_missing_dates,
    group_into_ranges,
    _period_to_dates,
)


def get_ohlcv(ticker: str, period: str = "3mo") -> pd.DataFrame:
    """
    Ambil OHLCV dengan cache-first strategy.
    - History: ambil dari ohlcv_prices, fetch yfinance hanya untuk tanggal yang belum ada.
    - Today: di-upsert dari API.
    """
    today = date.today()
    start_date_str, end_date_str = _period_to_dates(period)

    cached = get_cached_ohlcv(ticker, start_date_str, end_date_str)
    missing = find_missing_dates(cached, start_date_str, end_date_str)

    if not missing:
        if not cached.empty:
            return cached

    yahoo = to_yahoo_ticker(ticker)
    new_frames = [cached] if not cached.empty else []

    if missing:
        for range_start, range_end in group_into_ranges(missing):
            try:
                df_new = yf.download(
                    yahoo,
                    start=range_start.isoformat(),
                    end=(range_end + timedelta(days=1)).isoformat(),
                    progress=False,
                )
                if isinstance(df_new.columns, pd.MultiIndex):
                    df_new.columns = df_new.columns.get_level_values(0)
                if not df_new.empty:
                    save_ohlcv(ticker, df_new, today, source="yfinance")
                    new_frames.append(df_new)
            except Exception:
                pass

    if not new_frames:
        # Fallback: fetch full period
        df = yf.download(yahoo, period=period, progress=False)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        if not df.empty:
            save_ohlcv(ticker, df, today, source="yfinance")
        return df

    result = pd.concat(new_frames).sort_index()
    result = result[~result.index.duplicated(keep="last")]
    return result


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
