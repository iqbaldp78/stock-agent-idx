"""
Commodity Price Fetcher — Real-time harga komoditi global
Menggunakan Stockbit API untuk data komoditi.
"""
import os
import httpx
import logging
from datetime import datetime
import time

from data.commodity_mapper import (
    COMMODITY_TO_TICKERS,
    get_commodities_for_ticker,
)
from data.fetcher_stockbit import _retry_on_rate_limit

logger = logging.getLogger(__name__)

# Cache dengan TTL 1 jam
_PRICE_CACHE = {}
_CACHE_TTL = 3600  # seconds
_LAST_FETCH_TIME = 0

_STOCKBIT_COMMODITY_URL = "https://exodus.stockbit.com/emitten/v3/sector/73/subsector/74/company"


def _is_cache_valid() -> bool:
    return (time.time() - _LAST_FETCH_TIME) < _CACHE_TTL


@_retry_on_rate_limit(max_attempts=4, base_delay=1.0)
def _fetch_all_stockbit_commodities() -> None:
    """Fetch all commodities from Stockbit API and cache them."""
    global _LAST_FETCH_TIME, _PRICE_CACHE
    
    api_key = os.getenv("STOCKBIT_API_KEY")
    if not api_key:
        logger.warning("STOCKBIT_API_KEY is not set. Cannot fetch commodities.")
        return

    headers = {"Authorization": f"Bearer {api_key}"}
    
    with httpx.Client(timeout=15.0) as client:
        response = client.get(_STOCKBIT_COMMODITY_URL, headers=headers)
        response.raise_for_status()
        payload = response.json()
        
    data = payload.get("data", [])
    if not data:
        logger.warning("Empty data returned from Stockbit commodity endpoint.")
        return
        
    # Build a lookup by symbol (XAU, CPO, OIL, etc.)
    stockbit_data = {item.get("symbol"): item for item in data}
    
    # Process our tracked commodities
    timestamp = str(datetime.now())
    for commodity_id, commodity_info in COMMODITY_TO_TICKERS.items():
        symbol = commodity_info["symbol"]
        api_item = stockbit_data.get(symbol)
        
        if not api_item:
            logger.warning(f"Commodity symbol {symbol} not found in Stockbit response.")
            continue
            
        try:
            current_price = float(api_item.get("last", 0))
            change_value = float(api_item.get("change", 0))
            change_percent = float(api_item.get("percent", 0))
        except (ValueError, TypeError):
            current_price = 0.0
            change_value = 0.0
            change_percent = 0.0
            
        result = {
            "commodity": commodity_id,
            "name": commodity_info["name"],
            "symbol": symbol,
            "current_price": current_price,
            "change_value": change_value,
            "change_percent": change_percent,
            "timestamp": timestamp,
            "currency": commodity_info["currency"],
            "high_52w": 0.0,
            "low_52w": 0.0,
            "exposure": commodity_info["exposure"],
            "related_tickers": commodity_info["tickers"],
            "period_data": {
                "open": 0.0,
                "high": 0.0,
                "low": 0.0,
                "close": 0.0,
                "volume": 0,
            }
        }
        
        _PRICE_CACHE[commodity_id] = result
        logger.info(
            f"[{commodity_id.upper()}] {symbol} → "
            f"{result['currency']} {current_price} ({change_percent:+.2f}%)"
        )
        
    _LAST_FETCH_TIME = time.time()


def get_commodity_price(commodity: str, period: str = "1d") -> dict:
    """
    Ambil harga komoditi terkini dari Stockbit API.
    (period di-ignore karena endpoint baru tidak menyediakannya).
    """
    if commodity not in COMMODITY_TO_TICKERS:
        logger.warning(f"Unknown commodity: {commodity}")
        return {}

    if not _is_cache_valid() or commodity not in _PRICE_CACHE:
        try:
            _fetch_all_stockbit_commodities()
        except Exception as e:
            logger.error(f"Error fetching commodity data from Stockbit: {e}")
            
    if commodity in _PRICE_CACHE:
        return _PRICE_CACHE[commodity]
        
    return {}


def get_all_commodity_prices(period: str = "1d") -> dict:
    """Get harga untuk semua komoditi yang di-track."""
    if not _is_cache_valid():
        try:
            _fetch_all_stockbit_commodities()
        except Exception as e:
            logger.error(f"Error fetching commodity data from Stockbit: {e}")
            
    # Return copy of cache mapping for tracked commodities
    return {k: v for k, v in _PRICE_CACHE.items() if k in COMMODITY_TO_TICKERS}


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
    global _PRICE_CACHE, _LAST_FETCH_TIME
    _PRICE_CACHE = {}
    _LAST_FETCH_TIME = 0
    logger.info("Commodity price cache cleared")


def format_commodity_for_display(commodity_data: dict) -> str:
    """Format commodity data untuk display."""
    if not commodity_data:
        return ""

    return (
        f"{commodity_data['name']} ({commodity_data['symbol']})\n"
        f"  Price: {commodity_data['currency']} {commodity_data['current_price']}\n"
        f"  Change: {commodity_data['change_percent']:+.2f}% ({commodity_data['change_value']:+.2f})\n"
        f"  Related: {', '.join(commodity_data['related_tickers'])}\n"
        f"  Updated: {commodity_data['timestamp']}"
    )


def preload_all_commodities() -> dict:
    """
    Pre-load semua commodity prices sekali di awal workflow.
    Dipanggil di Phase 2 (Scoring) sebelum scoring per-ticker.

    Setelah ini, per-ticker tinggal mapping dari cache (no API call).

    Returns:
        {
            "status": "success" | "partial" | "error",
            "count": int,
            "cached": {commodity_id: price_data},
            "timestamp": str,
        }
    """
    global _PRICE_CACHE, _LAST_FETCH_TIME

    try:
        logger.info("[COMMODITY] Pre-loading all commodities...")

        api_key = os.getenv("STOCKBIT_API_KEY")
        if not api_key:
            logger.error("STOCKBIT_API_KEY not set. Cannot preload commodities.")
            return {
                "status": "error",
                "count": 0,
                "cached": {},
                "message": "STOCKBIT_API_KEY not set",
            }

        # Fetch all commodities from API (single call)
        headers = {"Authorization": f"Bearer {api_key}"}

        with httpx.Client(timeout=15.0) as client:
            response = client.get(_STOCKBIT_COMMODITY_URL, headers=headers)
            response.raise_for_status()
            payload = response.json()

        data = payload.get("data", [])
        if not data:
            logger.warning("[COMMODITY] Empty response from Stockbit endpoint.")
            return {
                "status": "partial",
                "count": 0,
                "cached": {},
                "message": "Empty data from API",
            }

        # Build lookup by symbol
        stockbit_data = {item.get("symbol"): item for item in data}

        # Process all tracked commodities
        timestamp = str(datetime.now())
        success_count = 0

        for commodity_id, commodity_info in COMMODITY_TO_TICKERS.items():
            symbol = commodity_info["symbol"]
            api_item = stockbit_data.get(symbol)

            if not api_item:
                logger.warning(f"[COMMODITY] Symbol {symbol} not found in API response.")
                continue

            try:
                current_price = float(api_item.get("last", 0))
                change_value = float(api_item.get("change", 0))
                change_percent = float(api_item.get("percent", 0))
            except (ValueError, TypeError):
                current_price = 0.0
                change_value = 0.0
                change_percent = 0.0

            result = {
                "commodity": commodity_id,
                "name": commodity_info["name"],
                "symbol": symbol,
                "current_price": current_price,
                "change_value": change_value,
                "change_percent": change_percent,
                "timestamp": timestamp,
                "currency": commodity_info["currency"],
                "high_52w": 0.0,
                "low_52w": 0.0,
                "exposure": commodity_info["exposure"],
                "related_tickers": commodity_info["tickers"],
                "period_data": {
                    "open": 0.0,
                    "high": 0.0,
                    "low": 0.0,
                    "close": 0.0,
                    "volume": 0,
                }
            }

            _PRICE_CACHE[commodity_id] = result
            success_count += 1

            logger.info(
                f"  [{commodity_id.upper()}] {symbol} → "
                f"{result['currency']} {current_price} ({change_percent:+.2f}%)"
            )

        # Update TTL
        _LAST_FETCH_TIME = time.time()

        status = "success" if success_count == len(COMMODITY_TO_TICKERS) else "partial"

        logger.info(
            f"[COMMODITY] Pre-load complete: {success_count}/{len(COMMODITY_TO_TICKERS)} "
            f"commodities cached"
        )

        return {
            "status": status,
            "count": success_count,
            "cached": _PRICE_CACHE.copy(),
            "timestamp": timestamp,
        }

    except Exception as e:
        logger.error(f"[COMMODITY] Pre-load failed: {e}", exc_info=True)
        return {
            "status": "error",
            "count": 0,
            "cached": {},
            "message": str(e),
        }
