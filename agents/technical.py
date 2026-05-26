"""
Agent — Technical
Analisis teknikal: trend, momentum, support/resistance.
Rule-based scoring menggunakan indikator klasik.
"""
import numpy as np
import pandas as pd
from data.fetcher_stockbit import get_ohlcv, get_stock_info


def _calculate_rsi(closes: pd.Series, period: int = 14) -> float | None:
    """Hitung RSI."""
    if len(closes) < period + 1:
        return None
    delta = closes.diff()
    gain = delta.where(delta > 0, 0).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return round(rsi.iloc[-1], 1)


def _calculate_ma(closes: pd.Series, period: int) -> float | None:
    """Hitung Moving Average."""
    if len(closes) < period:
        return None
    return round(closes.rolling(period).mean().iloc[-1], 2)


def _calculate_macd(closes: pd.Series) -> dict | None:
    """Hitung MACD (12, 26, 9)."""
    if len(closes) < 26:
        return None
    ema12 = closes.ewm(span=12).mean()
    ema26 = closes.ewm(span=26).mean()
    macd_line = ema12 - ema26
    signal_line = macd_line.ewm(span=9).mean()
    histogram = macd_line - signal_line
    return {
        "macd": round(macd_line.iloc[-1], 2),
        "signal": round(signal_line.iloc[-1], 2),
        "histogram": round(histogram.iloc[-1], 2),
        "cross": "golden_cross" if histogram.iloc[-1] > 0 and histogram.iloc[-2] <= 0
                 else "death_cross" if histogram.iloc[-1] < 0 and histogram.iloc[-2] >= 0
                 else "bullish" if histogram.iloc[-1] > 0
                 else "bearish",
    }


def _calculate_bollinger(closes: pd.Series, period: int = 20) -> dict | None:
    """Hitung Bollinger Bands."""
    if len(closes) < period:
        return None
    ma = closes.rolling(period).mean()
    std = closes.rolling(period).std()
    upper = ma + 2 * std
    lower = ma - 2 * std
    current = closes.iloc[-1]
    position = (current - lower.iloc[-1]) / (upper.iloc[-1] - lower.iloc[-1])
    return {
        "upper": round(upper.iloc[-1], 2),
        "middle": round(ma.iloc[-1], 2),
        "lower": round(lower.iloc[-1], 2),
        "position": round(position, 2),  # 0=lower, 1=upper
    }


def analyze(ticker: str) -> dict:
    """
    Scoring teknikal berdasarkan:
    - RSI (momentum)
    - MA cross (trend)
    - MACD (momentum confirmation)
    - Volume trend
    - Price vs 52W high/low
    """
    ohlcv = get_ohlcv(ticker, period="3mo")
    info = get_stock_info(ticker)

    if ohlcv.empty:
        return {
            "ticker": ticker,
            "score": 5.0,
            "signal": "HOLD",
            "setup": "No data available",
            "entry_zone": None,
            "target": None,
            "stop_loss": None,
            "data_used": [],
            "confidence": "LOW",
        }

    closes = ohlcv["Close"]
    volumes = ohlcv["Volume"]
    current_price = closes.iloc[-1]

    score = 5.0
    data_used = []
    setup_notes = []

    # === RSI ===
    rsi = _calculate_rsi(closes)
    if rsi is not None:
        data_used.append(f"RSI: {rsi}")
        if rsi < 30:
            score += 1.5
            setup_notes.append("RSI oversold")
        elif rsi < 40:
            score += 0.5
            setup_notes.append("RSI mendekati oversold")
        elif rsi > 70:
            score -= 1.0
            setup_notes.append("RSI overbought")
        elif 50 < rsi < 65:
            score += 0.5
            setup_notes.append("RSI bullish momentum")

    # === Moving Averages ===
    ma20 = _calculate_ma(closes, 20)
    ma50 = _calculate_ma(closes, 50)

    if ma20 is not None:
        data_used.append(f"MA20: {ma20:.0f}")
        if current_price > ma20:
            score += 0.5
            setup_notes.append("Harga di atas MA20")
        else:
            score -= 0.5

    if ma50 is not None:
        data_used.append(f"MA50: {ma50:.0f}")
        if current_price > ma50:
            score += 0.5
        else:
            score -= 0.5

    if ma20 is not None and ma50 is not None:
        if ma20 > ma50:
            score += 0.5
            setup_notes.append("Golden cross MA20/MA50")
        else:
            score -= 0.5
            setup_notes.append("Death cross MA20/MA50")

    # === MACD ===
    macd = _calculate_macd(closes)
    if macd is not None:
        data_used.append(f"MACD: {macd['cross']}")
        if macd["cross"] == "golden_cross":
            score += 1.5
            setup_notes.append("MACD golden cross")
        elif macd["cross"] == "bullish":
            score += 0.5
        elif macd["cross"] == "death_cross":
            score -= 1.5
            setup_notes.append("MACD death cross")
        elif macd["cross"] == "bearish":
            score -= 0.5

    # === Volume Trend ===
    if len(volumes) >= 20:
        avg_vol_20 = volumes.tail(20).mean()
        avg_vol_5 = volumes.tail(5).mean()
        vol_ratio = avg_vol_5 / avg_vol_20 if avg_vol_20 > 0 else 1
        data_used.append(f"Vol ratio 5/20: {vol_ratio:.2f}")
        if vol_ratio > 1.5:
            score += 1.0
            setup_notes.append("Volume naik signifikan")
        elif vol_ratio > 1.2:
            score += 0.5
            setup_notes.append("Volume meningkat")
        elif vol_ratio < 0.5:
            score -= 0.5
            setup_notes.append("Volume turun drastis")

    # === 52W Position ===
    high_52w = info.get("52w_high")
    low_52w = info.get("52w_low")
    if high_52w and low_52w and high_52w != low_52w:
        position_52w = (current_price - low_52w) / (high_52w - low_52w)
        data_used.append(f"52W pos: {position_52w:.0%}")
        if position_52w < 0.3:
            score += 0.5
            setup_notes.append("Dekat 52W low — potential reversal")
        elif position_52w > 0.9:
            score -= 0.5
            setup_notes.append("Dekat 52W high — waspada koreksi")

    # Clamp score 1-10
    score = max(1.0, min(10.0, score))

    # Signal
    if score >= 7.5:
        signal = "BUY"
    elif score >= 5.5:
        signal = "HOLD"
    else:
        signal = "SELL"

    # Entry/target/SL berdasarkan MA dan Bollinger
    bb = _calculate_bollinger(closes)
    if bb and ma20:
        entry_low = round(min(ma20, bb["lower"]), 0)
        entry_high = round(ma20, 0)
        target = round(current_price * 1.10, 0)  # 10% target
        stop_loss = round(bb["lower"] * 0.98, 0)
    else:
        entry_low = round(current_price * 0.97, 0)
        entry_high = round(current_price, 0)
        target = round(current_price * 1.10, 0)
        stop_loss = round(current_price * 0.95, 0)

    # Confidence
    if len(data_used) >= 5:
        confidence = "HIGH"
    elif len(data_used) >= 3:
        confidence = "MEDIUM"
    else:
        confidence = "LOW"

    return {
        "ticker": ticker,
        "score": round(score, 1),
        "signal": signal,
        "setup": "; ".join(setup_notes) if setup_notes else "Tidak ada sinyal kuat",
        "entry_zone": f"{entry_low:.0f}-{entry_high:.0f}",
        "target": f"{target:.0f}",
        "stop_loss": f"{stop_loss:.0f}",
        "data_used": data_used,
        "confidence": confidence,
    }
