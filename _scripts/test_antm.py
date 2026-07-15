from tradingview_ta import TA_Handler, Interval, Exchange

def test_antm():
    print("Mencoba mengambil data indikator teknikal untuk ANTM (Bursa IDX)...")
    handler = TA_Handler(
        symbol="ANTM",
        screener="indonesia",
        exchange="IDX",
        interval=Interval.INTERVAL_1_DAY
    )
    
    analysis = handler.get_analysis()
    
    print("\n--- Indikator Teknikal (Daily) ---")
    print(f"RSI (14): {analysis.indicators.get('RSI')}")
    print(f"MACD: {analysis.indicators.get('MACD.macd')}")
    print(f"MACD Signal: {analysis.indicators.get('MACD.signal')}")
    print(f"EMA (20): {analysis.indicators.get('EMA20')}")
    print(f"SMA (20): {analysis.indicators.get('SMA20')}")
    print(f"Bollinger Bands (Upper): {analysis.indicators.get('BBUpper')}")
    print(f"Bollinger Bands (Lower): {analysis.indicators.get('BBLower')}")
    
    print("\n--- Kesimpulan (Summary) ---")
    print(analysis.summary)

if __name__ == "__main__":
    test_antm()
