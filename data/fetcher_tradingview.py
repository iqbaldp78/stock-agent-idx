from tradingview_ta import TA_Handler, Interval, Exchange
import logging
import time
import threading

logger = logging.getLogger(__name__)

# Global state for rate limiting
_tv_lock = threading.Lock()
_last_tv_call = 0.0
TV_RATE_LIMIT_DELAY = 1.0  # 1 detik jeda minimum antar request ke TradingView

def get_technical_analysis(symbol: str, interval: str = "1d", screener: str = "indonesia", exchange: str = "IDX", max_retries: int = 3) -> dict:
    """
    Mengambil data full Technical Analysis dari TradingView yang mencakup RSI, MACD, Bollinger Bands,
    dan 20+ indikator lainnya beserta status BUY/SELL/HOLD.
    
    Args:
        symbol (str): Ticker saham (misal: ANTM)
        interval (str): Timeframe ('1m', '5m', '15m', '30m', '1h', '2h', '4h', '1d', '1W', '1M')
        screener (str): Negara/Screener (default: indonesia)
        exchange (str): Bursa (default: IDX)
        
    Returns:
        dict: Berisi indikator lengkap dan summary rekomendasi
    """
    
    # Mapping interval string to tradingview_ta Interval
    interval_map = {
        "1m": Interval.INTERVAL_1_MINUTE,
        "5m": Interval.INTERVAL_5_MINUTES,
        "15m": Interval.INTERVAL_15_MINUTES,
        "30m": Interval.INTERVAL_30_MINUTES,
        "1h": Interval.INTERVAL_1_HOUR,
        "2h": Interval.INTERVAL_2_HOURS,
        "4h": Interval.INTERVAL_4_HOURS,
        "1d": Interval.INTERVAL_1_DAY,
        "1W": Interval.INTERVAL_1_WEEK,
        "1M": Interval.INTERVAL_1_MONTH,
    }
    
    tv_interval = interval_map.get(interval, Interval.INTERVAL_1_DAY)
    
    global _last_tv_call
    
    for attempt in range(max_retries):
        try:
            with _tv_lock:
                now = time.time()
                time_since_last = now - _last_tv_call
                if time_since_last < TV_RATE_LIMIT_DELAY:
                    time.sleep(TV_RATE_LIMIT_DELAY - time_since_last)
                
                _last_tv_call = time.time()
                
            handler = TA_Handler(
                symbol=symbol,
                screener=screener,
                exchange=exchange,
                interval=tv_interval
            )
            
            analysis = handler.get_analysis()
            
            return {
                "status": "success",
                "symbol": symbol,
                "interval": interval,
                "summary": analysis.summary,
                "indicators": analysis.indicators
            }
        except Exception as e:
            if attempt < max_retries - 1:
                logger.warning(f"Rate limited or error fetching {symbol} from TradingView, retrying in 2s... (Attempt {attempt+1}/{max_retries}): {e}")
                time.sleep(2)
            else:
                logger.error(f"Error fetching technical analysis for {symbol} from TradingView after {max_retries} attempts: {e}")
                return {
                    "status": "error",
                    "message": str(e),
                    "symbol": symbol
                }

if __name__ == "__main__":
    import json
    result = get_technical_analysis("ANTM")
    print(json.dumps(result, indent=2))
