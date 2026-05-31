# ...existing code...




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


# === Divergence detection functions (moved below imports) ===
def _detect_divergence_rsi(closes: pd.Series, rsi_period: int = 14) -> str:
    """Deteksi bullish/bearish divergence antara harga dan RSI (2 swing terakhir)."""
    if len(closes) < rsi_period * 3:
        return "none"
    # Temukan dua swing low dan swing high harga
    window = rsi_period
    # Reset index agar semua series bisa diakses via posisi
    closes_ = closes.reset_index(drop=True)
    lows = closes.rolling(window, center=True).min().reset_index(drop=True)
    highs = closes.rolling(window, center=True).max().reset_index(drop=True)
    swing_lows = lows[(lows == closes_)].dropna()
    swing_highs = highs[(highs == closes_)].dropna()
    swing_lows_idx = swing_lows.index[-2:]
    swing_highs_idx = swing_highs.index[-2:]
    if len(swing_lows_idx) < 2 or len(swing_highs_idx) < 2:
        return "none"
    def safe_rsi(x):
        val = _calculate_rsi(pd.Series(x), rsi_period)
        return float(val) if val is not None else np.nan
    rsi_raw = closes.rolling(window=rsi_period).apply(safe_rsi).reset_index(drop=True)
    rsi = rsi_raw.dropna()
    # Pastikan rsi dan closes_ sama panjang (ambil tail sesuai rsi)
    min_len = min(len(rsi), len(closes_))
    closes_ = closes_[-min_len:]
    rsi = rsi[-min_len:]
    # Indexing by position, cek out-of-bounds
    low1, low2 = swing_lows_idx[-2], swing_lows_idx[-1]
    high1, high2 = swing_highs_idx[-2], swing_highs_idx[-1]
    max_idx = min(len(closes_), len(rsi)) - 1
    if low2 > max_idx or low1 > max_idx or high2 > max_idx or high1 > max_idx:
        return "none"
    if closes_[low2] < closes_[low1] and rsi.iloc[low2] > rsi.iloc[low1]:
        return "bullish"
    if closes_[high2] > closes_[high1] and rsi.iloc[high2] < rsi.iloc[high1]:
        return "bearish"
    return "none"

def _detect_divergence_macd(closes: pd.Series, macd_period: int = 14) -> str:
    """Deteksi bullish/bearish divergence antara harga dan MACD (2 swing terakhir)."""
    if len(closes) < macd_period * 3:
        return "none"
    window = macd_period
    lows = closes.rolling(window, center=True).min()
    highs = closes.rolling(window, center=True).max()
    swing_lows = lows[(lows == closes)]
    swing_highs = highs[(highs == closes)]
    swing_lows_idx = swing_lows.dropna().index[-2:]
    swing_highs_idx = swing_highs.dropna().index[-2:]
    if len(swing_lows_idx) < 2 or len(swing_highs_idx) < 2:
        return "none"
    # Hitung MACD line
    ema12 = closes.ewm(span=12).mean()
    ema26 = closes.ewm(span=26).mean()
    macd_line = ema12 - ema26
    # Bullish divergence: harga lower low, MACD higher low
    low1, low2 = swing_lows_idx[-2], swing_lows_idx[-1]
    if closes[low2] < closes[low1] and macd_line[low2] > macd_line[low1]:
        return "bullish"
    # Bearish divergence: harga higher high, MACD lower high
    high1, high2 = swing_highs_idx[-2], swing_highs_idx[-1]
    if closes[high2] > closes[high1] and macd_line[high2] < macd_line[high1]:
        return "bearish"
    return "none"


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
    try:
        # Inisialisasi semua variabel output utama dengan default
        score = 5.0
        signal = "HOLD"
        setup_notes = []
        entry_low = None
        entry_high = None
        target = None
        stop_loss = None
        support_near = None
        resistance_near = None
        support_strong = None
        resistance_strong = None
        divergence = {"rsi": None, "macd": None}
        data_used = []
        confidence = "LOW"

        # Ambil data OHLCV 1 tahun penuh agar cukup untuk MA200
        ohlcv = get_ohlcv(ticker, period="1y")
        info = get_stock_info(ticker)
        if ohlcv is None or ohlcv.empty:
            print("[ERROR] OHLCV kosong!")
            return {"ticker": ticker, "error": "OHLCV data kosong/gagal diambil (gabungan)", "trend": "unknown"}
        if len(ohlcv) < 200:
            print(f"[ERROR] Data OHLCV hanya {len(ohlcv)} baris, minimal 200 baris agar MA200 bisa dihitung!")
            return {"ticker": ticker, "error": f"Data OHLCV hanya {len(ohlcv)} baris, minimal 200 baris agar MA200 bisa dihitung!", "trend": "unknown"}
        if info is None or not isinstance(info, dict) or not info.get("current_price"):
            print("[ERROR] Info saham kosong/gagal diambil!")
            return {"ticker": ticker, "error": "Info saham kosong/gagal diambil", "trend": "unknown"}
        for col in ["Close", "Volume", "High", "Low"]:
            if col not in ohlcv.columns:
                print(f"[ERROR] Kolom {col} tidak ada di OHLCV!")
                return {"ticker": ticker, "error": f"Kolom {col} tidak ada di OHLCV", "trend": "unknown"}

        # ...existing code...
        # Gunakan seluruh data OHLCV yang sudah diambil (1 tahun)
        closes = ohlcv["Close"]
        volumes = ohlcv["Volume"]
        current_price = closes.iloc[-1]
        ma200_rolling = closes.rolling(200).mean()

        # === Divergence RSI & MACD ===
        # ...existing code...
        divergence_rsi = _detect_divergence_rsi(closes)
        divergence_macd = _detect_divergence_macd(closes)
        divergence = {"rsi": divergence_rsi, "macd": divergence_macd}
        # ...existing code...
        if divergence_rsi == "bullish":
            score += 2.0
            setup_notes.append("RSI bullish divergence (strong buy signal)")
            data_used.append("RSI divergence: bullish")
        elif divergence_rsi == "bearish":
            score -= 2.0
            setup_notes.append("RSI bearish divergence (strong sell signal)")
            data_used.append("RSI divergence: bearish")
        if divergence_macd == "bullish":
            score += 2.0
            setup_notes.append("MACD bullish divergence (strong buy signal)")
            data_used.append("MACD divergence: bullish")
        elif divergence_macd == "bearish":
            score -= 2.0
            setup_notes.append("MACD bearish divergence (strong sell signal)")
            data_used.append("MACD divergence: bearish")

        # === Support & Resistance Area (terdekat & terkuat) ===
        support_near = None
        resistance_near = None
        support_near_strength = 0
        resistance_near_strength = 0
        support_strong = None
        resistance_strong = None
        support_strong_strength = 0
        resistance_strong_strength = 0
        if len(ohlcv) >= 20:
            lows = ohlcv['Low'][-20:]
            highs = ohlcv['High'][-20:]
            possible_supports = lows[lows < current_price]
            possible_supports = possible_supports[possible_supports > current_price * 0.9]
            if not possible_supports.empty:
                support_near = possible_supports.max()
            else:
                support_near = lows.min()
            possible_resistances = highs[highs > current_price]
            possible_resistances = possible_resistances[possible_resistances < current_price * 1.1]
            if not possible_resistances.empty:
                resistance_near = possible_resistances.min()
            else:
                resistance_near = highs.max()
            support_strong = lows.min()
            resistance_strong = highs.max()
            support_near_strength = (lows <= support_near * 1.01).sum()
            resistance_near_strength = (highs >= resistance_near * 0.99).sum()
            support_strong_strength = (lows <= support_strong * 1.01).sum()
            resistance_strong_strength = (highs >= resistance_strong * 0.99).sum()
            if abs(current_price - support_near) / support_near < 0.03:
                score += 0.7
                setup_notes.append(f"Harga mendekati support terdekat di {support_near:.0f}")
            if abs(current_price - resistance_near) / resistance_near < 0.03:
                score -= 0.5
                setup_notes.append(f"Harga mendekati resistance terdekat di {resistance_near:.0f}")
            data_used.append(f"Support terdekat: {support_near:.0f} (sentuh {support_near_strength}x), Resistance terdekat: {resistance_near:.0f} (sentuh {resistance_near_strength}x)")
            data_used.append(f"Support kuat: {support_strong:.0f} (sentuh {support_strong_strength}x), Resistance kuat: {resistance_strong:.0f} (sentuh {resistance_strong_strength}x)")

        # === Breakout + Volume ===
        breakout_score = 0
        if len(closes) >= 21 and len(volumes) >= 20:
            last_close = closes.iloc[-1]
            prev_20_high = closes[-21:-1].max()
            last_vol = volumes.iloc[-1]
            avg_vol_20 = volumes[-21:-1].mean()
            if last_close > prev_20_high and last_vol > 1.5 * avg_vol_20:
                breakout_score = 2.0
                score += breakout_score
                setup_notes.append("Breakout high 20 hari + volume tinggi")
                data_used.append(f"Breakout: close {last_close:.0f} > high20 {prev_20_high:.0f}, vol {last_vol:.0f} > 1.5x avg20 {avg_vol_20:.0f}")
            elif last_close > prev_20_high:
                breakout_score = 0.5
                score += breakout_score
                setup_notes.append("Breakout high 20 hari (tanpa volume konfirmasi)")
                data_used.append(f"Breakout: close {last_close:.0f} > high20 {prev_20_high:.0f}")

        # === RSI ===
        rsi = _calculate_rsi(closes)
        # ...existing code...
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
            else:
                setup_notes.append("RSI netral")
        else:
            data_used.append("RSI: data tidak cukup")

        # === Moving Averages ===
        ma20 = _calculate_ma(closes, 20)
        ma50 = _calculate_ma(closes, 50)
        ma100 = _calculate_ma(closes, 100)
        ma200 = _calculate_ma(closes, 200)
        # ...existing code...

        # Tambahan: MA100 dan MA200 sebagai support kuat
        if ma100 is not None and abs(current_price - ma100) / ma100 < 0.03:
            score += 0.7
            setup_notes.append(f"Harga mendekati MA100 (support kuat di {ma100:.0f})")
        if ma200 is not None and abs(current_price - ma200) / ma200 < 0.03:
            score += 0.7
            setup_notes.append(f"Harga mendekati MA200 (support kuat di {ma200:.0f})")
        # MA20
        if ma20 is not None:
            data_used.append(f"MA20: {ma20:.0f}")
            if current_price > ma20:
                score += 0.5
                setup_notes.append("Harga di atas MA20 (short-term bullish)")
            else:
                score -= 0.5
                setup_notes.append("Harga di bawah MA20 (short-term bearish)")
        else:
            data_used.append("MA20: data tidak cukup")
        # MA50
        if ma50 is not None:
            data_used.append(f"MA50: {ma50:.0f}")
            if current_price > ma50:
                score += 0.5
                setup_notes.append("Harga di atas MA50 (mid-term bullish)")
            else:
                score -= 0.5
                setup_notes.append("Harga di bawah MA50 (mid-term bearish)")
        else:
            data_used.append("MA50: data tidak cukup")
        # MA100
        if ma100 is not None:
            data_used.append(f"MA100: {ma100:.0f}")
            if current_price > ma100:
                score += 0.5
                setup_notes.append("Harga di atas MA100 (intermediate-term bullish)")
            else:
                score -= 0.5
                setup_notes.append("Harga di bawah MA100 (intermediate-term bearish)")
        else:
            data_used.append("MA100: data tidak cukup")
        # MA200
        if ma200 is not None:
            data_used.append(f"MA200: {ma200:.0f}")
            if current_price > ma200:
                score += 0.5
                setup_notes.append("Harga di atas MA200 (long-term bullish)")
            else:
                score -= 0.5
                setup_notes.append("Harga di bawah MA200 (long-term bearish)")
        else:
            data_used.append("MA200: data tidak cukup")
        # Cross MA20/MA50
        if ma20 is not None and ma50 is not None:
            if ma20 > ma50:
                score += 0.5
                setup_notes.append("Golden cross MA20/MA50")
            else:
                score -= 0.5
                setup_notes.append("Death cross MA20/MA50")
        # Cross MA50/MA100
        if ma50 is not None and ma100 is not None:
            if ma50 > ma100:
                setup_notes.append("Golden cross MA50/MA100 (mid-intermediate bullish)")
            else:
                setup_notes.append("Death cross MA50/MA100 (mid-intermediate bearish)")
        # Cross MA100/MA200
        if ma100 is not None and ma200 is not None:
            if ma100 > ma200:
                setup_notes.append("Golden cross MA100/MA200 (intermediate-long bullish)")
            else:
                setup_notes.append("Death cross MA100/MA200 (intermediate-long bearish)")

        # === MACD ===
        macd = _calculate_macd(closes)
        # ...existing code...
        if macd is not None:
            data_used.append(f"MACD: {macd['cross']}")
            if macd["cross"] == "golden_cross":
                score += 1.5
                setup_notes.append("MACD golden cross")
            elif macd["cross"] == "bullish":
                score += 0.5
                setup_notes.append("MACD bullish momentum")
            elif macd["cross"] == "death_cross":
                score -= 1.5
                setup_notes.append("MACD death cross")
            elif macd["cross"] == "bearish":
                score -= 0.5
                setup_notes.append("MACD bearish momentum")
            else:
                setup_notes.append("MACD netral")
        else:
            data_used.append("MACD: data tidak cukup")

        # === Volume Trend ===
        if len(volumes) >= 20:
            avg_vol_20 = volumes.tail(20).mean()
            avg_vol_5 = volumes.tail(5).mean()
            vol_ratio = avg_vol_5 / avg_vol_20 if avg_vol_20 > 0 else 1
            # ...existing code...
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
            else:
                setup_notes.append("Volume normal")
        else:
            data_used.append("Volume: data tidak cukup")

        # === 52W Position ===
        high_52w = info.get("52w_high")
        low_52w = info.get("52w_low")
        # ...existing code...
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

        # Entry/target/SL berbasis support dan risk/reward
        bb = _calculate_bollinger(closes)
        max_entry_width = 0.07  # 7% maksimal lebar entry zone
        min_rr = 1.5  # minimal risk/reward ratio
        if support_near and ma20:
            entry_low = float(support_near)
            entry_high = float(ma20)
            if (entry_high - entry_low) / entry_low > max_entry_width:
                entry_high = round(entry_low * (1 + max_entry_width), 0)
            else:
                entry_high = round(entry_high, 0)
            entry_low = round(entry_low, 0)
        elif bb and ma20:
            entry_low = round(min(ma20, bb["lower"]), 0)
            entry_high = round(ma20, 0)
            if (entry_high - entry_low) / entry_low > max_entry_width:
                entry_high = round(entry_low * (1 + max_entry_width), 0)
        else:
            entry_low = round(current_price * 0.97, 0)
            entry_high = round(current_price, 0)

        if signal == "BUY":
            tgt = None
            if resistance_near and float(resistance_near) > entry_high:
                tgt = float(resistance_near)
            elif resistance_strong and float(resistance_strong) > entry_high:
                tgt = float(resistance_strong)
            else:
                tgt = entry_high * 1.07
            target = round(tgt, 0)
            if support_strong and float(support_strong) < entry_low:
                stop_loss = round(float(support_strong) * 0.98, 0)
            else:
                stop_loss = round(entry_low * 0.98, 0)
            risk = entry_low - stop_loss
            reward = target - entry_high
            if risk > 0 and reward / risk < min_rr:
                target = round(entry_high + min_rr * risk, 0)
        elif signal == "SELL":
            tgt = None
            min_target = entry_low * 0.85
            if support_near and float(support_near) < entry_low:
                tgt = float(support_near)
            elif support_strong and float(support_strong) < entry_low:
                tgt = float(support_strong)
            else:
                tgt = entry_low * 0.93
            tgt = max(tgt, min_target)
            target = round(tgt, 0)
            if resistance_strong and float(resistance_strong) > entry_high:
                stop_loss = round(float(resistance_strong) * 1.02, 0)
            else:
                stop_loss = round(entry_high * 1.02, 0)
            risk = stop_loss - entry_high
            reward = entry_low - target
            if risk > 0 and reward / risk < min_rr:
                new_target = entry_low - min_rr * risk
                target = round(max(new_target, min_target), 0)
        else:
            target = round(current_price * 1.10, 0)
            stop_loss = round(current_price * 0.95, 0)

        if len(data_used) >= 5:
            confidence = "HIGH"
        elif len(data_used) >= 3:
            confidence = "MEDIUM"
        else:
            confidence = "LOW"

        # === Trend detection logic ===
        trend = "unknown"
        if all(x is not None for x in [ma20, ma50, ma100, ma200]):
            if current_price > ma20 and current_price > ma50 and current_price > ma100 and current_price > ma200:
                trend = "bullish"
            elif current_price < ma20 and current_price < ma50 and current_price < ma100 and current_price < ma200:
                trend = "bearish"
            else:
                trend = "sideways"
        # Skoring berdasarkan trend
        if trend == "bullish":
            score += 1.5
            setup_notes.append("Trend utama: bullish (semua MA major di bawah harga)")
            data_used.append("Trend: bullish (+1.5)")
        elif trend == "bearish":
            score -= 1.0
            setup_notes.append("Trend utama: bearish (semua MA major di atas harga)")
            data_used.append("Trend: bearish (-1.0)")
        elif trend == "sideways":
            setup_notes.append("Trend utama: sideways (harga di antara MA major)")
            data_used.append("Trend: sideways (0)")
        trend = trend if 'trend' in locals() else "unknown"
        result = {
            "ticker": ticker,
            "score": round(score, 1),
            "signal": signal,
            "trend": trend,
            "setup": "; ".join(setup_notes) if setup_notes else "Tidak ada sinyal kuat",
            "entry_zone": f"{entry_low:.0f}-{entry_high:.0f}" if entry_low is not None and entry_high is not None else None,
            "target": f"{target:.0f}" if target is not None else None,
            "stop_loss": f"{stop_loss:.0f}" if stop_loss is not None else None,
            "support_near": f"{support_near:.0f}" if support_near is not None else None,
            "resistance_near": f"{resistance_near:.0f}" if resistance_near is not None else None,
            "support_strong": f"{support_strong:.0f}" if support_strong is not None else None,
            "resistance_strong": f"{resistance_strong:.0f}" if resistance_strong is not None else None,
            "divergence": divergence,
            "data_used": data_used,
            "confidence": confidence,
        }
        return result
    except Exception as e:
        import traceback
        print(f"[ERROR] Exception in analyze: {e}")
        traceback.print_exc()
        return {"ticker": ticker, "error": str(e)}


if __name__ == "__main__":
    import sys
    import json
    ticker = sys.argv[1] if len(sys.argv) > 1 else "ANTM"
    result = analyze(ticker)
    print(json.dumps(result, indent=2, ensure_ascii=False))
