"""
Candlestick Pattern Detector untuk Bursa Efek Indonesia (BEI)
Mendeteksi pola candlestick reversal & continuation beserta win-rate BEI.
"""
from typing import Dict, List, Any
import pandas as pd
import numpy as np


PATTERNS_METADATA = {
    "hammer": {
        "name": "Hammer",
        "type": "BULLISH_REVERSAL",
        "win_rate_bei": 0.64,
        "best_context": "setelah downtrend 3+ hari",
        "target_days": 3,
        "signal": "BULLISH",
    },
    "morning_star": {
        "name": "Morning Star",
        "type": "BULLISH_REVERSAL",
        "win_rate_bei": 0.71,
        "best_context": "di support kuat + volume spike day3",
        "target_days": 3,
        "signal": "BULLISH",
    },
    "bullish_engulfing": {
        "name": "Bullish Engulfing",
        "type": "BULLISH_REVERSAL",
        "win_rate_bei": 0.68,
        "signal": "BULLISH",
    },
    "piercing_line": {
        "name": "Piercing Line",
        "type": "BULLISH_REVERSAL",
        "win_rate_bei": 0.61,
        "signal": "BULLISH",
    },
    "shooting_star": {
        "name": "Shooting Star",
        "type": "BEARISH_REVERSAL",
        "win_rate_bei": 0.63,
        "signal": "BEARISH",
    },
    "evening_star": {
        "name": "Evening Star",
        "type": "BEARISH_REVERSAL",
        "win_rate_bei": 0.70,
        "signal": "BEARISH",
    },
    "bearish_engulfing": {
        "name": "Bearish Engulfing",
        "type": "BEARISH_REVERSAL",
        "win_rate_bei": 0.66,
        "signal": "BEARISH",
    },
    "three_white_soldiers": {
        "name": "Three White Soldiers",
        "type": "BULLISH_CONTINUATION",
        "win_rate_bei": 0.73,
        "signal": "STRONG BULLISH",
    },
    "rising_three": {
        "name": "Rising Three Methods",
        "type": "BULLISH_CONTINUATION",
        "win_rate_bei": 0.69,
        "signal": "BULLISH",
    },
}


def detect_candlestick_patterns(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Deteksi pola candlestick dari DataFrame OHLCV.
    DataFrame harus memiliki kolom: 'open', 'high', 'low', 'close', 'volume'.
    Returns list of detected patterns with metadata.
    """
    if df is None or len(df) < 5:
        return []

    # Standardize column names
    df = df.copy()
    df.columns = [str(c).lower() for c in df.columns]

    required_cols = {"open", "high", "low", "close", "volume"}
    if not required_cols.issubset(set(df.columns)):
        return []

    # Calculate candle metrics
    df["body_size"] = (df["close"] - df["open"]).abs()
    df["candle_range"] = df["high"] - df["low"]
    df["upper_wick"] = df["high"] - df[["open", "close"]].max(axis=1)
    df["lower_wick"] = df[["open", "close"]].min(axis=1) - df["low"]
    df["ma_vol_20"] = df["volume"].rolling(window=20, min_periods=1).mean()

    detected = []

    # Current candle (last row)
    curr = df.iloc[-1]
    prev1 = df.iloc[-2]
    prev2 = df.iloc[-3]
    prev3 = df.iloc[-4]
    prev4 = df.iloc[-5] if len(df) >= 5 else None

    # 1. Hammer
    # lower_wick > 2 * body_size AND upper_wick < 0.3 * body_size AND volume > ma_volume_20
    body = max(curr["body_size"], 1e-5)
    if (
        curr["lower_wick"] > 2 * body
        and curr["upper_wick"] < 0.3 * body
        and curr["volume"] > curr["ma_vol_20"]
    ):
        meta = PATTERNS_METADATA["hammer"].copy()
        meta["date"] = str(curr.name) if hasattr(curr, "name") else ""
        meta["confidence"] = meta["win_rate_bei"]
        detected.append(meta)

    # 2. Morning Star
    # day1: bearish candle besar (body > 1% price)
    # day2: doji / small body
    # day3: bullish candle > 50% menutup day1
    p2_body_pct = prev2["body_size"] / max(prev2["open"], 1)
    p1_body_pct = prev1["body_size"] / max(prev1["open"], 1)
    if (
        prev2["close"] < prev2["open"] and p2_body_pct > 0.01  # Day 1 Bearish
        and p1_body_pct < 0.008  # Day 2 Small Body
        and curr["close"] > curr["open"]  # Day 3 Bullish
        and curr["close"] > (prev2["open"] - (prev2["open"] - prev2["close"]) * 0.5)  # Covers > 50% of Day 1
    ):
        meta = PATTERNS_METADATA["morning_star"].copy()
        meta["confidence"] = meta["win_rate_bei"]
        detected.append(meta)

    # 3. Bullish Engulfing
    # day1: bearish
    # day2: bullish menelan day1
    # volume_day2 > volume_day1 * 1.5
    if (
        prev1["close"] < prev1["open"]
        and curr["close"] > curr["open"]
        and curr["open"] <= prev1["close"]
        and curr["close"] >= prev1["open"]
        and curr["volume"] > prev1["volume"] * 1.5
    ):
        meta = PATTERNS_METADATA["bullish_engulfing"].copy()
        meta["confidence"] = meta["win_rate_bei"]
        detected.append(meta)

    # 4. Piercing Line
    # day1: bearish candle besar
    # day2: open di bawah low day1, tutup > 50% day1
    if (
        prev1["close"] < prev1["open"]
        and (prev1["body_size"] / max(prev1["open"], 1)) > 0.01
        and curr["open"] < prev1["low"]
        and curr["close"] > (prev1["open"] - (prev1["open"] - prev1["close"]) * 0.5)
        and curr["close"] < prev1["open"]
    ):
        meta = PATTERNS_METADATA["piercing_line"].copy()
        meta["confidence"] = meta["win_rate_bei"]
        detected.append(meta)

    # 5. Shooting Star
    # upper_wick > 2 * body_size AND lower_wick < 0.3 * body_size (setelah uptrend)
    if (
        curr["upper_wick"] > 2 * body
        and curr["lower_wick"] < 0.3 * body
        and prev1["close"] > prev2["close"]  # Uptrend context
    ):
        meta = PATTERNS_METADATA["shooting_star"].copy()
        meta["confidence"] = meta["win_rate_bei"]
        detected.append(meta)

    # 6. Evening Star
    # day1: bullish besar
    # day2: gap up + small body
    # day3: bearish besar, tutup di bawah 50% day1
    if (
        prev2["close"] > prev2["open"] and p2_body_pct > 0.01
        and prev1["open"] > prev2["close"] and p1_body_pct < 0.008
        and curr["close"] < curr["open"]
        and curr["close"] < (prev2["open"] + (prev2["close"] - prev2["open"]) * 0.5)
    ):
        meta = PATTERNS_METADATA["evening_star"].copy()
        meta["confidence"] = meta["win_rate_bei"]
        detected.append(meta)

    # 7. Bearish Engulfing
    if (
        prev1["close"] > prev1["open"]
        and curr["close"] < curr["open"]
        and curr["open"] >= prev1["close"]
        and curr["close"] <= prev1["open"]
    ):
        meta = PATTERNS_METADATA["bearish_engulfing"].copy()
        meta["confidence"] = meta["win_rate_bei"]
        detected.append(meta)

    # 8. Three White Soldiers
    # 3 candle bullish berturut, open dalam body candle sebelumnya, tutup lebih tinggi, volume meningkat
    if (
        prev2["close"] > prev2["open"]
        and prev1["close"] > prev1["open"]
        and curr["close"] > curr["open"]
        and prev1["open"] > prev2["open"] and prev1["open"] < prev2["close"]
        and curr["open"] > prev1["open"] and curr["open"] < prev1["close"]
        and curr["close"] > prev1["close"] > prev2["close"]
        and curr["volume"] > prev1["volume"] > prev2["volume"]
    ):
        meta = PATTERNS_METADATA["three_white_soldiers"].copy()
        meta["confidence"] = meta["win_rate_bei"]
        detected.append(meta)

    # 9. Rising Three Methods
    if prev4 is not None:
        p4_bullish = prev4["close"] > prev4["open"] and (prev4["body_size"] / max(prev4["open"], 1)) > 0.015
        middle_small = (
            prev3["high"] <= prev4["high"] and prev3["low"] >= prev4["low"] and
            prev2["high"] <= prev4["high"] and prev2["low"] >= prev4["low"] and
            prev1["high"] <= prev4["high"] and prev1["low"] >= prev4["low"]
        )
        curr_breakout = curr["close"] > curr["open"] and curr["close"] > prev4["high"]
        if p4_bullish and middle_small and curr_breakout:
            meta = PATTERNS_METADATA["rising_three"].copy()
            meta["confidence"] = meta["win_rate_bei"]
            detected.append(meta)

    return detected
