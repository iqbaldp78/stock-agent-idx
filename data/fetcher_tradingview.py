from tradingview_ta import TA_Handler, Interval, Exchange
import time
import logging

logger = logging.getLogger(__name__)

_is_banned = False
_banned_until = 0

def get_technical_analysis(symbol: str, interval: str = "1d", screener: str = "indonesia", exchange: str = "IDX") -> dict:
    """
    Mengambil data full Technical Analysis dari TradingView yang mencakup RSI, MACD, Bollinger Bands,
    dan 20+ indikator lainnya beserta status BUY/SELL/HOLD.
    """
    global _is_banned, _banned_until
    
    if _is_banned and time.time() < _banned_until:
        return {
            "status": "error",
            "message": "TradingView API rate limit (429) active. Skipping to save time.",
            "symbol": symbol
        }
        
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
    
    # Proactive throttle to avoid triggering the rate limit in the first place
    time.sleep(1.0)
    
    max_retries = 3
    base_delay = 3

    for attempt in range(max_retries):
        try:
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
            if "429" in str(e):
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    logger.warning(f"Rate limited by TradingView (429) for {symbol}. Retrying in {delay} seconds... (Attempt {attempt + 1}/{max_retries})")
                    time.sleep(delay)
                else:
                    logger.error(f"TradingView IP Ban detected (429). Disabling TA fetch for 5 minutes.")
                    _is_banned = True
                    _banned_until = time.time() + 300
                    return {
                        "status": "error",
                        "message": str(e),
                        "symbol": symbol
                    }
            else:
                logger.error(f"Error fetching technical analysis for {symbol} from TradingView: {e}")
                return {
                    "status": "error",
                    "message": str(e),
                    "symbol": symbol
                }

if __name__ == "__main__":
    import json
    result = get_technical_analysis("ANTM")
    print(json.dumps(result, indent=2))
