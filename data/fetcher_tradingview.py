from tradingview_ta import TA_Handler, Interval, Exchange
import logging

logger = logging.getLogger(__name__)

def get_technical_analysis(symbol: str, interval: str = "1d", screener: str = "indonesia", exchange: str = "IDX") -> dict:
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
