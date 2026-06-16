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


_SECTOR_CACHE = {}
_SECTOR_CACHE_TIME = None

def get_sector_outlook() -> dict:
    """
    Outlook per sektor berdasarkan indeks sektoral.
    Cache-first: baca sector_ohlcv dari DB, fetch yfinance hanya untuk tanggal yang belum ada.
    In-memory TTL 1 jam untuk menghindari DB query berulang dalam 1 sesi.
    """
    global _SECTOR_CACHE, _SECTOR_CACHE_TIME

    # Return in-memory cache jika masih fresh (< 1 jam)
    if _SECTOR_CACHE and _SECTOR_CACHE_TIME:
        age = datetime.now() - _SECTOR_CACHE_TIME
        if age < timedelta(hours=1):
            print(f"[DEBUG] Returning in-memory sector outlook (age: {age.total_seconds():.0f}s)")
            return _SECTOR_CACHE

    sectors = {
        "perbankan": "^JKFINA",
        "mining": "^JKMING",
        "consumer": "^JKCONS",
        "infrastructure": "^JKINFR",
        "property": "^JKPROP",
    }

    today = date.today()
    end_date_str = today.isoformat()
    start_date_str = (today - timedelta(days=35)).isoformat()  # ~1 bulan + buffer

    outlook = {name: "NETRAL" for name in sectors}

    for sector_name, idx_ticker in sectors.items():
        try:
            from db.cache import get_ohlcv_no_data_dates, save_ohlcv_no_data_dates
            
            # Cek DB dulu
            cached = get_cached_sector_ohlcv(idx_ticker, start_date_str, end_date_str)
            missing = find_missing_dates(cached, start_date_str, end_date_str)

            no_data_dates = get_ohlcv_no_data_dates(idx_ticker, start_date_str, end_date_str, source="yfinance")
            if no_data_dates:
                missing = [d for d in missing if d not in no_data_dates]

            # Fetch hanya tanggal yang belum ada
            if missing:
                for range_start, range_end in group_into_ranges(missing):
                    try:
                        df_new = yf.download(
                            idx_ticker,
                            start=range_start.isoformat(),
                            end=(range_end + timedelta(days=1)).isoformat(),
                            progress=False,
                            auto_adjust=True,
                        )
                        
                        expected_dates = []
                        cur = range_start
                        while cur <= range_end:
                            if cur.weekday() < 5 and cur < today:
                                expected_dates.append(cur)
                            cur += timedelta(days=1)
                        
                        if not df_new.empty:
                            # Flatten MultiIndex jika ada
                            if isinstance(df_new.columns, pd.MultiIndex):
                                df_new.columns = df_new.columns.get_level_values(0)
                            save_sector_ohlcv(idx_ticker, df_new, today)
                            cached = pd.concat([cached, df_new]).sort_index()
                            cached = cached[~cached.index.duplicated(keep="last")]
                            
                            returned_dates = {idx.date() if hasattr(idx, "date") else idx for idx in df_new.index}
                            unresolved_no_data = [d for d in expected_dates if d not in returned_dates]
                            if unresolved_no_data:
                                save_ohlcv_no_data_dates(idx_ticker, unresolved_no_data, source="yfinance")
                        elif expected_dates:
                            save_ohlcv_no_data_dates(idx_ticker, expected_dates, source="yfinance")
                    except Exception as e:
                        print(f"[DEBUG] {sector_name} fetch {range_start}..{range_end}: {e}")

            if not cached.empty and len(cached) >= 5:
                change_5d = (
                    (cached["Close"].iloc[-1] - cached["Close"].iloc[-5])
                    / cached["Close"].iloc[-5] * 100
                )
                print(f"[DEBUG] {sector_name} change_5d: {change_5d:.2f}%")
                if change_5d > 2:
                    outlook[sector_name] = "POSITIF"
                elif change_5d < -2:
                    outlook[sector_name] = "NEGATIF"
                else:
                    outlook[sector_name] = "NETRAL"
            else:
                print(f"[DEBUG] {sector_name} data empty or <5 rows")

        except Exception as e:
            print(f"[DEBUG] {sector_name} error: {e}")

    # Cache in-memory
    _SECTOR_CACHE = outlook
    _SECTOR_CACHE_TIME = datetime.now()

    return outlook
