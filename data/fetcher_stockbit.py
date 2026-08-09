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
from typing import Optional

import httpx
import pandas as pd
import numpy as np
import dotenv

from db.cache import (
    get_cached_ohlcv,
    save_ohlcv,
    find_missing_dates,
    group_into_ranges,
    get_ohlcv_no_data_dates,
    save_ohlcv_no_data_dates,
    get_cached_stock_info,
    save_stock_info,
    get_cached_broker_daily,
    save_broker_daily,
)
from datetime import date as _date

# shortcut agar tidak konflik dengan parameter bernama 'date' di get_broker_daily
date_module_today = _date.today

logger = logging.getLogger(__name__)


def _get_api_key() -> str:
    """Membaca STOCKBIT_API_KEY secara dinamis dari file .env tanpa restart."""
    env_file = dotenv.find_dotenv()
    if env_file:
        dotenv.load_dotenv(env_file, override=True)
    return os.getenv("STOCKBIT_API_KEY")


def login_stockbit_with_password() -> str:
    """
    Melakukan login otomatis menggunakan STOCKBIT_USERNAME dan STOCKBIT_PASSWORD 
    menggunakan endpoint Mobile API v6 untuk menghindari ReCAPTCHA dan New Device OTP.
    Fungsi ini merupakan fallback atau fungsi manual karena refresh token menjadi metode utama.
    """
    username = os.getenv("STOCKBIT_USERNAME")
    password = os.getenv("STOCKBIT_PASSWORD")
    
    if not username or not password:
        raise ValueError("STOCKBIT_USERNAME or STOCKBIT_PASSWORD is not set in .env")

    import httpx
    
    url = "https://exodus.stockbit.com/login/v6/username"
    
    # Payload mengikuti format mobile API v6 tanpa ReCAPTCHA!
    payload = {
        "user": username,
        "password": password,
        "player_id": os.getenv("STOCKBIT_PLAYER_ID", "c260c141-f3e3-4470-af3a-02ca57204d50")
    }
    
    # Sangat penting menggunakan User-Agent Android resmi agar Stockbit tidak meminta Captcha
    headers = {
        "User-Agent": "Stockbit/5.6.8 (Android; 10; Scale/2.00)",
        "Content-Type": "application/json"
    }
    
    logger.info("Mencoba login via API Mobile v6...")
    with httpx.Client(timeout=15.0) as client:
        response = client.post(url, json=payload, headers=headers)
        
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            logger.error(f"Gagal login API: {e.response.text}")
            raise
            
        data = response.json()
        
    # JSON Path: data -> data -> login -> token_data -> access -> token
    token = data.get("data", {}).get("login", {}).get("token_data", {}).get("access", {}).get("token")
    
    if not token:
        # Fallback format jika terjadi perubahan struktur JSON
        token = data.get("data", {}).get("access_token")
        
    if not token:
        raise ValueError(f"Gagal mendapatkan access_token dari response login: {data}")
        
    # Update current environment
    os.environ["STOCKBIT_API_KEY"] = token
    
    # Update .env file permanently
    env_file = dotenv.find_dotenv()
    if env_file:
        dotenv.set_key(env_file, "STOCKBIT_API_KEY", token)
        logger.info("Stockbit token berhasil direfresh via Mobile API dan disimpan ke .env")
    else:
        logger.warning("File .env tidak ditemukan, token hanya diupdate di memori")
        
    return token


def refresh_stockbit_token() -> str:
    """
    Mendapatkan access_token baru menggunakan STOCKBIT_REFRESH_TOKEN.
    Fungsi ini menggantikan flow login password secara otomatis.
    """
    refresh_token = os.getenv("STOCKBIT_REFRESH_TOKEN")
    if not refresh_token:
        raise ValueError("STOCKBIT_REFRESH_TOKEN is not set in .env")

    import httpx
    import json
    
    url = "https://exodus.stockbit.com/login/refresh"
    headers = {
        "Authorization": f"Bearer {refresh_token}",
        "User-Agent": "Stockbit/5.6.8 (Android; 10; Scale/2.00)",
        "Content-Type": "application/json"
    }
    
    logger.info("Mencoba mendapatkan access_token dari refresh_token...")
    with httpx.Client(timeout=15.0) as client:
        response = client.post(url, headers=headers, json={})
        
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            logger.error(f"Gagal refresh token API: {e.response.text}")
            raise
            
        data = response.json()
        
    # Extract access token
    token = data.get("data", {}).get("access", {}).get("token")
    if not token:
        token = data.get("data", {}).get("access_token")
    if not token:
        token = data.get("data", {}).get("login", {}).get("token_data", {}).get("access", {}).get("token")
        
    if not token:
        logger.error(f"Response JSON structure: {json.dumps(data, indent=2)}")
        raise ValueError(f"Gagal mendapatkan access_token dari response refresh: {data}")
        
    # Optional: Extract new refresh token if stockbit rotates it
    new_refresh_token = data.get("data", {}).get("refresh", {}).get("token")
    if not new_refresh_token:
        new_refresh_token = data.get("data", {}).get("refresh_token")
    if not new_refresh_token:
        new_refresh_token = data.get("data", {}).get("login", {}).get("token_data", {}).get("refresh", {}).get("token")
        
    # Update current environment
    os.environ["STOCKBIT_API_KEY"] = token
    if new_refresh_token:
        os.environ["STOCKBIT_REFRESH_TOKEN"] = new_refresh_token
    
    # Update .env file permanently
    env_file = dotenv.find_dotenv()
    if env_file:
        dotenv.set_key(env_file, "STOCKBIT_API_KEY", token)
        if new_refresh_token:
            dotenv.set_key(env_file, "STOCKBIT_REFRESH_TOKEN", new_refresh_token)
        logger.info("Stockbit access token berhasil direfresh dan disimpan ke .env")
    else:
        logger.warning("File .env tidak ditemukan, token hanya diupdate di memori")
        
    return token


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
                    
                    if status in (401, 403):
                        logger.warning(f"[{func.__name__}] HTTP {status}. Mencoba auto-refresh token...")
                        try:
                            # Auto-refresh token jika expired atau forbidden
                            refresh_stockbit_token()
                            logger.info(f"[{func.__name__}] Auto-refresh berhasil, melanjutkan retry...")
                            # Jeda sedikit sebelum retry
                            time.sleep(1.0)
                            continue
                        except Exception as refresh_exc:
                            logger.error(f"Auto-refresh gagal: {refresh_exc}. Silakan perbarui STOCKBIT_REFRESH_TOKEN di .env secara manual.")
                            raise last_exception

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
    ("BQ", "Ciptadana Sekuritas"),
    ("KI", "Ciptadana Sekuritas"),
    ("SS", "Shinhan Sekuritas"),
    ("IF", "Samuel Sekuritas"),
    ("BB", "Verdhana Sekuritas"),
    ("DH", "Sinarmas Sekuritas"),
    ("CD", "Mega Capital Sekuritas"),
    ("XL", "Stockbit Sekuritas"),
    ("AZ", "Sucor Sekuritas"),
    ("AG", "Alindo Sekuritas"),
    ("YJ", "Phillip Sekuritas"),
    ("XC", "Ajaib Sekuritas"),
    ("KK", "KGI Sekuritas"),
    ("YP", "Mirae Asset Sekuritas"),
    ("AI", "UOB Kay Hian Sekuritas"),
    ("RF", "Lotus Andalan Sekuritas"),
    ("OD", "BRI Danareksa Sekuritas"),
    ("SQ", "BCA Sekuritas"),
    ("HP", "Henan Putihrai Sekuritas"),
    ("DP", "Dinar Sekuritas"),
    ("TP", "OCBC Sekuritas"),
    ("PD", "Indo Premier Sekuritas"),
    ("NI", "BNI Sekuritas"),
    ("CP", "Valbury Sekuritas"),
    ("DR", "RHB Sekuritas"),
    ("ZP", "Maybank Sekuritas"),
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
        return f"{sign}{abs_value / 1_000_000_000:.2f}B"
    if abs_value >= 1_000_000:
        return f"{sign}{abs_value / 1_000_000:.2f}M"
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


@_retry_on_rate_limit(max_attempts=4, base_delay=1.0)
def get_marketdetector_broker_summary(
    ticker: str,
    date_from: str,
    date_to: str,
    transaction_type: str = "TRANSACTION_TYPE_NET",
    market_board: str = "MARKET_BOARD_REGULER",
    investor_type: str = "INVESTOR_TYPE_ALL",
    limit: int = 10,
) -> dict:
    api_key = _get_api_key()
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

    headers = {
        "Authorization": f"Bearer {api_key}",
        "User-Agent": "Stockbit/5.6.8 (Android; 10; Scale/2.00)"
    }
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
    api_key = _get_api_key()
    if not api_key:
        raise ValueError("STOCKBIT_API_KEY is not set")

    url = f"https://exodus.stockbit.com/emitten/{ticker.upper()}/info"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "User-Agent": "Stockbit/5.6.8 (Android; 10; Scale/2.00)"
    }

    with httpx.Client(timeout=15.0) as client:
        response = client.get(url, headers=headers)
        response.raise_for_status()
        payload = response.json()

    if payload.get("message") and "Successfully" not in payload.get("message"):
        logger.info("Stockbit info: %s", payload.get("message"))

    price = payload.get("data", {}).get("price")
    if not price:
        logger.warning("Stockbit info: empty price for %s", ticker)
        return 0.0

    price_val = _parse_number(price)
    logger.info("Stockbit info: %s price=%s", ticker, price_val)
    return price_val


@_retry_on_rate_limit(max_attempts=4, base_delay=1.0)
def get_realtime_stock_info_stockbit(ticker: str) -> dict:
    """
    Fetch realtime stock info (price, prev_close, change, change_pct) dari Stockbit API.
    """
    api_key = _get_api_key()
    if not api_key:
        return {}

    url = f"https://exodus.stockbit.com/emitten/{ticker.upper()}/info"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "User-Agent": "Stockbit/5.6.8 (Android; 10; Scale/2.00)"
    }

    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(url, headers=headers)
            response.raise_for_status()
            payload = response.json()

        data = payload.get("data", {})
        price = _parse_number(data.get("price", 0))
        previous = _parse_number(data.get("previous", 0))
        change = _parse_number(data.get("change", 0))
        percentage = _parse_number(data.get("percentage", 0))

        return {
            "ticker": ticker.upper(),
            "price": price,
            "previous": previous,
            "change": change,
            "change_pct": percentage
        }
    except Exception as e:
        logger.warning("Failed to fetch realtime Stockbit info for %s: %s", ticker, e)
        return {}


@_retry_on_rate_limit(max_attempts=4, base_delay=1.0)
def get_ihsg_realtime_price_stockbit() -> dict:
    """
    Fetch IHSG realtime price dan market info dari Stockbit API.
    Returns: {
        "price": float,
        "prev_close": float,
        "change": float,
        "change_pct": float,
        "timestamp": str (WIB format),
        "currency": str
    }
    """
    api_key = _get_api_key()
    if not api_key:
        logger.warning("[IHSG Realtime] STOCKBIT_API_KEY not set, using fallback")
        return _ihsg_realtime_fallback()

    try:
        url = "https://exodus.stockbit.com/emitten/IHSG/info"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "User-Agent": "Stockbit/5.6.8 (Android; 10; Scale/2.00)"
        }

        with httpx.Client(timeout=15.0) as client:
            response = client.get(url, headers=headers)
            response.raise_for_status()
            payload = response.json()

        data = payload.get("data", {})
        price = _parse_number(data.get("price", 0))
        prev_close = _parse_number(data.get("prev_close", data.get("previous", 0)))
        change = _parse_number(data.get("change", 0)) if "change" in data else (price - prev_close if prev_close > 0 else 0)
        change_pct = _parse_number(data.get("percentage", 0)) if "percentage" in data else ((change / prev_close * 100) if prev_close > 0 else 0)

        # Format timestamp ke WIB (UTC+7)
        from datetime import datetime, timezone, timedelta
        now_utc = datetime.now(timezone.utc)
        wib_tz = timezone(timedelta(hours=7))
        now_wib = now_utc.astimezone(wib_tz)
        timestamp_wib = now_wib.strftime("%Y-%m-%d %H:%M:%S WIB")

        result = {
            "price": price,
            "prev_close": prev_close,
            "change": round(change, 2),
            "change_pct": round(change_pct, 2),
            "timestamp": timestamp_wib,
            "currency": "IDR",
            "source": "stockbit"
        }

        logger.info(f"[IHSG Realtime] Price={price}, Change={change_pct:.2f}%, Time={timestamp_wib}")
        return result

    except Exception as e:
        logger.warning(f"[IHSG Realtime] Stockbit fetch failed: {e}, using fallback")
        return _ihsg_realtime_fallback()


def _ihsg_realtime_fallback() -> dict:
    """Fallback data jika Stockbit API tidak tersedia."""
    from datetime import datetime, timezone, timedelta
    now_utc = datetime.now(timezone.utc)
    wib_tz = timezone(timedelta(hours=7))
    now_wib = now_utc.astimezone(wib_tz)
    timestamp_wib = now_wib.strftime("%Y-%m-%d %H:%M:%S WIB")

    return {
        "price": 0.0,
        "prev_close": 0.0,
        "change": 0.0,
        "change_pct": 0.0,
        "timestamp": timestamp_wib,
        "currency": "IDR",
        "source": "fallback",
        "error": "Stockbit API unavailable"
    }


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


def get_broker_accumulation(
    ticker: str,
    days: int = 7,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
) -> dict:
    """
    Agregasi broker summary untuk N hari trading ke belakang menggunakan NET data.
    Hitung avg price tiap broker = true cost mereka.

    days=7  → timing signal (sedang aktif sekarang?)
    days=30 → true avg cost bandar

    NOTE: Menggunakan Market Detector API dengan TRANSACTION_TYPE_NET untuk full period,
    bukan agregasi harian GROSS.
    """
    if date_from and date_to:
        try:
            d_start = datetime.strptime(date_from, "%Y-%m-%d").date()
            d_end = datetime.strptime(date_to, "%Y-%m-%d").date()
            trading_days = []
            cur = d_start
            while cur <= d_end:
                if cur.weekday() < 5:
                    trading_days.append(cur.strftime("%Y-%m-%d"))
                cur += timedelta(days=1)
            if not trading_days:
                trading_days = [date_from]
            days = len(trading_days)
        except Exception:
            trading_days = [date_from]
            days = 1
    else:
        trading_days = _get_trading_days(days, include_today=True)
        date_from = trading_days[-1]
        date_to = trading_days[0]

    # Hitung keaktifan per broker secara harian (menggunakan cache-first get_broker_daily)
    # Ini sangat cepat jika data historis sudah ada di DB cache.
    broker_active_buy = {}
    broker_active_sell = {}
    for d in trading_days:
        try:
            day_data = get_broker_daily(ticker, d)
            for entry in day_data.get("buy", []):
                code = entry.get("broker")
                if code:
                    broker_active_buy[code] = broker_active_buy.get(code, 0) + 1
            for entry in day_data.get("sell", []):
                code = entry.get("broker")
                if code:
                    broker_active_sell[code] = broker_active_sell.get(code, 0) + 1
        except Exception as e:
            logger.warning(f"Failed to fetch daily broker data for active days calc on {d}: {e}")

    # Single API call untuk NET data full period
    try:
        api_data = get_marketdetector_broker_summary(
            ticker=ticker,
            date_from=date_from,
            date_to=date_to,
            transaction_type="TRANSACTION_TYPE_NET",
        )
    except httpx.HTTPStatusError as e:
        logger.warning(f"Failed to fetch broker accumulation for {ticker}: {e}")
        return {
            "ticker": ticker,
            "window_days": days,
            "period": f"{date_from} s/d {date_to}",
            "top_accumulators": [],
            "top_distributors": [],
            "distribution_top3_value": 0,
            "bandar_detector": {},
            "daily_summary": {},
            "foreign_net": 0,
        }

    # Parse brokers_buy (NET buyers)
    broker_totals = {}
    for entry in api_data.get("brokers_buy", []):
        code = entry.get("broker_code")
        if not code:
            continue

        blot = _parse_number(entry.get("blot"))  # NET buy lot
        bval = _parse_number(entry.get("bval"))  # NET buy value
        avg_price = _int_no_decimal(entry.get("netbs_buy_avg_price"))

        # Ambil hari aktif riil dari perhitungan harian, minimal 1 jika masuk top accumulator tapi data harian kosong
        active_cnt = broker_active_buy.get(code, 1)

        broker_totals[code] = {
            "broker_name": _get_broker_name(code),
            "total_buy_lot": int(blot) if blot else 0,
            "total_buy_value": int(bval) if bval else 0,
            "active_days": active_cnt,
            "daily": {},  # Not available in aggregated NET data
            "avg_price": avg_price if avg_price else 0,
        }

    # Parse brokers_sell (NET sellers)
    distribution_totals = {}
    for entry in api_data.get("brokers_sell", []):
        code = entry.get("broker_code")
        if not code:
            continue

        slot = _parse_number(entry.get("slot"))  # NET sell lot (negative)
        sval = _parse_number(entry.get("sval"))  # NET sell value (negative)
        avg_price = _int_no_decimal(entry.get("netbs_sell_avg_price"))

        # Ambil hari aktif riil dari perhitungan harian, minimal 1 jika masuk top distributor tapi data harian kosong
        active_cnt = broker_active_sell.get(code, 1)

        # Convert negative values to positive for consistency
        distribution_totals[code] = {
            "broker_name": _get_broker_name(code),
            "total_sell_lot": abs(int(slot)) if slot else 0,
            "total_sell_value": abs(int(sval)) if sval else 0,
            "active_days": active_cnt,
            "daily": {},  # Not available in aggregated NET data
            "avg_price": avg_price if avg_price else 0,
            "type": entry.get("type"),
        }

    # === MUTUAL EXCLUSIVITY: Broker hanya bisa accumulator ATAU distributor, tidak keduanya ===
    # Jika broker ada di kedua list, tentukan based on mana yang lebih signifikan (value lebih besar)
    overlapping_brokers = set(broker_totals.keys()) & set(distribution_totals.keys())
    for broker_code in overlapping_brokers:
        buy_val = broker_totals[broker_code]["total_buy_value"]
        sell_val = distribution_totals[broker_code]["total_sell_value"]

        # Remove dari yang lebih kecil valuenya
        if buy_val >= sell_val:
            del distribution_totals[broker_code]
        else:
            del broker_totals[broker_code]

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

    # Calculate foreign net from bandar_detector if available
    bandar_detector = api_data.get("bandar_detector", {})
    foreign_net = 0
    if bandar_detector:
        # Foreign net might be in bandar_detector data
        foreign_buy = _parse_number(bandar_detector.get("foreign_buy", 0))
        foreign_sell = _parse_number(bandar_detector.get("foreign_sell", 0))
        foreign_net = int(foreign_buy - foreign_sell) if foreign_buy or foreign_sell else 0

    return {
        "ticker": ticker,
        "window_days": days,
        "period": f"{date_from} s/d {date_to}",
        "top_accumulators": sorted_brokers[:10],
        "top_distributors": sorted_distributors[:10],
        "distribution_top3_value": top3_sell_total,
        "bandar_detector": bandar_detector,
        "daily_summary": {},  # Not available in NET aggregate mode
        "foreign_net": foreign_net,
    }


def get_full_bandarm_data(
    ticker: str,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
) -> dict:
    """Ambil kedua window sekaligus untuk 1 saham."""
    res = {
        "ticker": ticker,
        "w7": get_broker_accumulation(ticker, days=7),
        "w30": get_broker_accumulation(ticker, days=30),
    }
    if date_from and date_to:
        res["custom_window"] = get_broker_accumulation(ticker, date_from=date_from, date_to=date_to)
    return res


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
    api_key = _get_api_key()
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
    headers = {
        "Authorization": f"Bearer {api_key}",
        "User-Agent": "Stockbit/5.6.8 (Android; 10; Scale/2.00)"
    }
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
        return pd.DataFrame(columns=["Open", "High", "Low", "Close", "Volume", "Frequency", "NetForeign", "AveragePrice", "ChangePercentage"])

    df = pd.DataFrame([
        {
            "Date": pd.to_datetime(item["date"]),
            "Open": float(item["open"]),
            "High": float(item["high"]),
            "Low": float(item["low"]),
            "Close": float(item["close"]),
            "Volume": float(item["volume"]),
            "Frequency": int(item.get("frequency", 0)),
            "NetForeign": int(item.get("net_foreign", 0)),
            "AveragePrice": float(item.get("average", 0.0)),
            "ChangePercentage": float(item.get("change_percentage", 0.0)),
        }
        for item in all_data if all(k in item for k in required_keys)
    ])
    if df.empty or "Date" not in df.columns:
        return pd.DataFrame(columns=["Open", "High", "Low", "Close", "Volume", "Frequency", "NetForeign", "AveragePrice", "ChangePercentage"])
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
    try:
        start_dt = date.fromisoformat(start_date)
        end_dt = date.fromisoformat(end_date)
    except (ValueError, TypeError):
        start_dt = today
        end_dt = today

    fetch_end = min(end_dt, today)
    if start_dt > fetch_end:
        cached = get_cached_ohlcv(ticker, start_date, end_date)
        return cached if cached is not None else pd.DataFrame()

    fetch_end_str = fetch_end.isoformat()
    cached = get_cached_ohlcv(ticker, start_date, fetch_end_str)
    missing = find_missing_dates(cached, start_date, fetch_end_str)

    # Skip tanggal historis yang sudah pernah dipastikan tidak punya data.
    no_data_dates = get_ohlcv_no_data_dates(ticker, start_date, fetch_end_str)
    if no_data_dates:
        missing = [d for d in missing if d not in no_data_dates]

    if not missing:
        logger.info(f"[cache hit] OHLCV {ticker} {start_date}..{end_date}")
        return cached

    # Fetch hanya rentang yang belum ada
    new_frames = [cached] if not cached.empty else []

    # Pecah range panjang menjadi sub-ranges maksimal 90 hari agar tidak ditolak Stockbit
    chunked_ranges = []
    for range_start, range_end in group_into_ranges(missing):
        cur_start = range_start
        while cur_start <= range_end:
            cur_end = min(range_end, cur_start + timedelta(days=90))
            chunked_ranges.append((cur_start, cur_end))
            cur_start = cur_end + timedelta(days=1)

    for range_start, range_end in chunked_ranges:
        try:
            df_new = _fetch_ohlcv_range_api(
                ticker, range_start.isoformat(), range_end.isoformat(), limit
            )

            expected_dates = []
            cur = range_start
            while cur <= range_end:
                if cur.weekday() < 5 and cur < today:
                    expected_dates.append(cur)
                cur += timedelta(days=1)

            if not df_new.empty:
                save_ohlcv(ticker, df_new, today)
                new_frames.append(df_new)

                returned_dates = {
                    idx.date() if hasattr(idx, "date") else idx
                    for idx in df_new.index
                }
                unresolved_no_data = [d for d in expected_dates if d not in returned_dates]
                if unresolved_no_data:
                    save_ohlcv_no_data_dates(ticker, unresolved_no_data)
            elif expected_dates:
                save_ohlcv_no_data_dates(ticker, expected_dates)
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
    Support custom periods like 1y, 3y, 5y, 10y, or max/all.
    """
    end_date = datetime.now().date()

    if period.lower() in ["max", "all"]:
        # Ambil data sejak IHSG aktif panjang, misal tahun 2005 (sudah cukup untuk ML)
        start_date = date(2005, 1, 1)
        return get_ohlcv_range(ticker, start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))

    # Manual parsing for "Xy" or "Xmo"
    import re
    y_match = re.match(r"^(\d+)y$", period.lower())
    mo_match = re.match(r"^(\d+)mo$", period.lower())

    if y_match:
        years = int(y_match.group(1))
        period_days = years * 252
    elif mo_match:
        months = int(mo_match.group(1))
        period_days = months * 22
    else:
        # Default fallback
        period_days = {"1mo": 22, "3mo": 66, "6mo": 132, "1y": 252}.get(period, 22)

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
    api_key = _get_api_key()
    if not api_key:
        raise ValueError("STOCKBIT_API_KEY is not set")
    url = f"https://exodus.stockbit.com/keystats/ratio/v1/{ticker.upper()}?year_limit=10"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "User-Agent": "Stockbit/5.6.8 (Android; 10; Scale/2.00)"
    }
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

    api_key = _get_api_key()
    if not api_key:
        raise ValueError("STOCKBIT_API_KEY is not set")
    url = f"https://exodus.stockbit.com/keystats/ratio/v1/{ticker.upper()}?year_limit=10"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "User-Agent": "Stockbit/5.6.8 (Android; 10; Scale/2.00)"
    }
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
    bvps = _find_fin_item_value(closure_fin_items_results, "Current Book Value Per Share")
    # === Dividend Data Extraction ===
    dividend_yield = _find_fin_item_value(closure_fin_items_results, "Dividend Yield")
    dividend_payout_ratio = _find_fin_item_value(closure_fin_items_results, "Payout Ratio")
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
        "bvps": round(bvps, 2) if bvps is not None else None,
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
        data = cached
    else:
        data = _fetch_stock_info_api(ticker)
        save_stock_info(ticker, today_str, data)

    try:
        live_price = get_current_price_stockbit(ticker)
        if live_price and live_price > 0:
            data["current_price"] = round(float(live_price), 0)
    except Exception as e:
        logger.warning("Failed to refresh live current price for %s: %s", ticker, e)

    return data


def get_multiple_ohlcv(tickers: list[str], period: str = "3mo") -> dict[str, pd.DataFrame]:
    """Ambil OHLCV untuk banyak saham sekaligus."""
    return {ticker: get_ohlcv(ticker, period) for ticker in tickers}


@_retry_on_rate_limit(max_attempts=3, base_delay=1.0)
def fetch_report_notifications(limit: int = 25, last_id: int | str = None) -> dict:
    """
    Fetch report notifications (Research reports, Newsfeed, Corp action, Dividends, etc.) from Stockbit API.
    """
    api_key = _get_api_key()
    if not api_key:
        api_key = refresh_stockbit_token()
        
    url = (
        "https://exodus.stockbit.com/notification?"
        "types=NOTIF_TYPE_NEW_REPORT&"
        "types=NOTIF_TYPE_NEWSFEED&"
        "types=NOTIF_TYPE_COMPANY_PUBLIC_EXPOSE&"
        "types=NOTIF_TYPE_COMPANY_SHAREHOLDING&"
        "types=NOTIF_TYPE_COMPANY_DIVIDEND&"
        "types=NOTIF_TYPE_COMPANY_CORP_ACTION&"
        "types=NOTIF_TYPE_COMPANY_OTHERS&"
        f"limit={limit}"
    )
    if last_id:
        url += f"&last_id={last_id}"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Origin": "https://stockbit.com",
        "Referer": "https://stockbit.com/"
    }
    with httpx.Client(timeout=15.0) as client:
        response = client.get(url, headers=headers)
        response.raise_for_status()
        return response.json()


@_retry_on_rate_limit(max_attempts=3, base_delay=1.0)
def fetch_post_detail(post_id: str | int) -> dict:
    """
    Fetch post detail content from Stockbit API by post_id.
    """
    api_key = _get_api_key()
    if not api_key:
        api_key = refresh_stockbit_token()

    url = f"https://exodus.stockbit.com/stream/v3/post/{post_id}"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Origin": "https://stockbit.com",
        "Referer": "https://stockbit.com/"
    }
    with httpx.Client(timeout=15.0) as client:
        response = client.post(url, headers=headers, json={})
        response.raise_for_status()
        return response.json()

