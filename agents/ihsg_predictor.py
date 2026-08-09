from agents.llm_client import invoke_json_im
import json
"""
IHSG Predictor Agent
Prediksi direction IHSG (BULLISH/BEARISH/SIDEWAYS) dengan D1/D3/D5/D7 price targets.
Rule-based scoring (4 components) + optional LLM narrative.
"""
import logging
from datetime import datetime
import pandas as pd
import numpy as np

from data.fetcher_ihsg import get_ihsg_ohlcv, get_market_breadth, get_sector_rotation, get_ihsg_technical_analysis
from agents.macro import analyze as macro_analyze
from config import LLM_ENABLED, LLM_MODEL_INVESTMENT_MANAGER, LLM_MODEL_IM_FALLBACK
from agents.debate.personas import IM_SYSTEM_PROMPT

logger = logging.getLogger(__name__)


def _calculate_rsi(prices: pd.Series, period: int = 14) -> float:
    """Calculate RSI fallback."""
    if len(prices) < period + 1:
        return 50.0
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss.replace(0, 1e-10)
    rsi = 100 - (100 / (1 + rs))
    return float(rsi.iloc[-1]) if not pd.isna(rsi.iloc[-1]) else 50.0


def _calculate_macd(prices: pd.Series) -> tuple[float, float]:
    """Calculate MACD and signal line fallback. Returns (macd, signal)."""
    if len(prices) < 26:
        return 0.0, 0.0
    ema12 = prices.ewm(span=12, adjust=False).mean()
    ema26 = prices.ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    signal = macd.ewm(span=9, adjust=False).mean()
    return float(macd.iloc[-1]), float(signal.iloc[-1])


def _calculate_atr(ohlcv: pd.DataFrame, period: int = 14) -> float:
    """Calculate 14-period Average True Range (ATR) percentage of current price."""
    try:
        if ohlcv is None or len(ohlcv) < period + 1:
            return 1.0  # Fallback default 1.0%
        df = ohlcv.copy()
        high = df['High'].astype(float)
        low = df['Low'].astype(float)
        close = df['Close'].astype(float)
        prev_close = close.shift(1)

        tr1 = high - low
        tr2 = (high - prev_close).abs()
        tr3 = (low - prev_close).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(period).mean().iloc[-1]
        current_close = close.iloc[-1]
        atr_pct = (atr / current_close) * 100 if current_close > 0 else 1.0
        return float(round(atr_pct, 2))
    except Exception as e:
        logger.warning(f"[ATR] Error calculating ATR: {e}")
        return 1.0



def _calculate_momentum_score(ohlcv: pd.DataFrame, macro_data: dict, tv_ta: dict = None) -> float:
    """
    Score momentum using TradingView TA integration (with fallback to pandas OHLCV).
    Priority is given to TradingView TA per AGENTS.md rules.
    Returns: float [0, 1]
    """
    try:
        score = 0.5
        rsi = 50.0
        macd = 0.0
        signal = 0.0
        tv_used = False

        if tv_ta and tv_ta.get("status") == "success" and "indicators" in tv_ta:
            indicators = tv_ta["indicators"]
            summary = tv_ta.get("summary", {})

            # RSI from TradingView
            if "RSI" in indicators and indicators["RSI"] is not None:
                rsi = float(indicators["RSI"])
                tv_used = True

            # MACD from TradingView
            if "MACD.macd" in indicators and "MACD.signal" in indicators:
                if indicators["MACD.macd"] is not None and indicators["MACD.signal"] is not None:
                    macd = float(indicators["MACD.macd"])
                    signal = float(indicators["MACD.signal"])
                    tv_used = True

            # Recommendation boost from TradingView summary
            rec = summary.get("RECOMMENDATION", "").upper()
            if "STRONG_BUY" in rec:
                score += 0.10
            elif "BUY" in rec:
                score += 0.05
            elif "STRONG_SELL" in rec:
                score -= 0.10
            elif "SELL" in rec:
                score -= 0.05

            # MA positioning from TradingView TA per AGENTS.md rules
            ma_buy_count = 0
            ma_total = 0
            for ma_key in ["SMA20", "SMA50", "SMA200", "EMA20", "EMA50", "EMA200"]:
                if ma_key in indicators and indicators[ma_key] is not None and ohlcv is not None and not ohlcv.empty:
                    current_price = float(ohlcv["Close"].iloc[-1])
                    if current_price > float(indicators[ma_key]):
                        ma_buy_count += 1
                    ma_total += 1
            if ma_total > 0:
                score += (ma_buy_count / ma_total - 0.5) * 0.15
                tv_used = True

        if not tv_used and ohlcv is not None and len(ohlcv) >= 20:
            close = ohlcv["Close"].astype(float)
            rsi = _calculate_rsi(close, 14)
            macd, signal = _calculate_macd(close)

            # Fallback MA positioning using pandas
            ma20 = close.rolling(20).mean().iloc[-1]
            ma50 = close.rolling(50).mean().iloc[-1] if len(close) >= 50 else ma20
            ma100 = close.rolling(100).mean().iloc[-1] if len(close) >= 100 else ma50
            current_price = close.iloc[-1]
            above_mas = sum([current_price > ma for ma in [ma20, ma50, ma100]])
            score += (above_mas / 3 - 0.5) * 0.15

        # RSI component (normalized 30-70 to 0-1)
        rsi_norm = (rsi - 30) / 40
        rsi_norm = max(0.0, min(1.0, rsi_norm))
        score += (rsi_norm - 0.5) * 0.25  # ±0.125 contribution

        # MACD component
        if macd > signal:
            score += 0.10 if macd > 0 else 0.05
        elif macd < signal:
            score -= 0.10 if macd < 0 else 0.05

        score = max(0.0, min(1.0, score))
        source_str = "TradingView TA" if tv_used else "Pandas Fallback"
        logger.info(f"[Momentum ({source_str})] RSI={rsi:.1f}, MACD={macd:.4f}, Score={score:.2f}")
        return score

    except Exception as e:
        logger.warning(f"[Momentum] Error: {e}")
        return 0.5


def _calculate_breadth_score(breadth: dict) -> float:
    """
    Score market breadth (A/D ratio, participation, volume trend).
    Returns: float [0, 1]
    """
    try:
        score = 0.5

        # A/D ratio component
        adr = breadth.get("advance_decline_ratio", 1.0)
        if adr > 1.5:
            score += 0.2  # Strong breadth
        elif adr < 0.7:
            score -= 0.2  # Weak breadth
        else:
            score += (adr - 1.0) * 0.2  # Gradual

        # Participation above MA20
        participation = breadth.get("participation_above_ma20", 50.0)
        part_score = (participation - 40) / 20  # 40%=neutral, 60%=bullish
        part_score = max(0, min(1, part_score))
        score += (part_score - 0.5) * 0.2  # ±0.1 contribution

        # Volume trend
        vol_trend = breadth.get("volume_trend", 0.0)
        if vol_trend > 5:
            score += 0.1  # Expanding volume
        elif vol_trend < -5:
            score -= 0.1  # Contracting volume

        score = max(0.0, min(1.0, score))
        logger.info(f"[Breadth] ADR={adr:.2f}, Particip={participation:.1f}%, Score={score:.2f}")
        return score

    except Exception as e:
        logger.warning(f"[Breadth] Error: {e}")
        return 0.5


def _calculate_macro_score(macro_data: dict) -> float:
    """
    Score macro environment (USD/IDR, IHSG trend, BI rate context).
    Returns: float [0, 1]
    """
    try:
        score = 0.5

        # USD/IDR pressure (lower IDR = bullish for equities)
        usdidr = macro_data.get("usdidr")
        if usdidr is None:
            usdidr = 15800.0
        else:
            usdidr = float(usdidr)

        # Adjust thresholds for current market conditions (2026: IDR ~18k)
        if usdidr < 16000:
            score += 0.15  # Strong IDR (rare, bullish)
        elif usdidr > 19000:
            score -= 0.15  # Very weak IDR (bearish)
        else:
            # Normalize within realistic 16000-19000 range
            usdidr_norm = (usdidr - 17500) / 1500  # 17500 = neutral (mid-point)
            score += max(-0.15, min(0.15, usdidr_norm * 0.15))

        # IHSG vs MA20 (trend strength)
        ihsg_vs_ma = macro_data.get("ihsg_vs_ma20")
        if ihsg_vs_ma is None:
            ihsg_vs_ma = 0.0
        else:
            ihsg_vs_ma = float(ihsg_vs_ma)

        if ihsg_vs_ma > 2.0:
            score += 0.15  # Strong uptrend
        elif ihsg_vs_ma < -2.0:
            score -= 0.15  # Strong downtrend
        else:
            score += (ihsg_vs_ma / 2.0) * 0.15  # Gradual

        # Volatility penalty
        is_volatile = macro_data.get("is_volatile", False)
        if is_volatile:
            score -= 0.1

        score = max(0.0, min(1.0, score))
        logger.info(f"[Macro] USD/IDR={usdidr:.0f}, IHSG_vs_MA20={ihsg_vs_ma:+.2f}%, Score={score:.2f}")
        return score

    except Exception as e:
        logger.warning(f"[Macro] Error: {e}")
        return 0.5


def _calculate_sector_score(sectors: dict) -> float:
    """
    Score sector rotation (divergence, leading sector strength, directional return).
    Returns: float [0, 1]
    """
    try:
        score = 0.5
        divergence = sectors.get("divergence", 0.0)
        leading_sector = sectors.get("leading_sector", "neutral")
        sec_dict = sectors.get("sectors", {})

        # Compute average 1D return of sampled sectors
        if sec_dict:
            all_rets = [v.get("1d_return", 0.0) for v in sec_dict.values()]
            avg_ret = sum(all_rets) / len(all_rets) if all_rets else 0.0

            # Adjust base score based on overall sector performance
            if avg_ret > 0.5:
                score += 0.10
            elif avg_ret < -0.5:
                score -= 0.10

        # Divergence indicates active sector rotation
        if divergence > 3.0:
            score += 0.10

        # Leading sector impact (bullish vs bearish)
        leading_data = sec_dict.get(leading_sector, {})
        leading_ret = leading_data.get("1d_return", 0.0)

        if leading_ret < 0:
            score -= 0.10  # Even the leading sector is declining
        else:
            if leading_sector in ["perbankan", "consumer"]:
                score += 0.05  # Defensive leads = moderate bullish
            elif leading_sector in ["mining", "infrastructure"]:
                score += 0.10  # Cyclical leads = strong bullish
            elif leading_sector == "property":
                score += 0.05  # Mixed signal

        score = max(0.0, min(1.0, score))
        logger.info(f"[Sectors] Divergence={divergence:.2f}%, Leading={leading_sector}, Score={score:.2f}")
        return score

    except Exception as e:
        logger.warning(f"[Sectors] Error: {e}")
        return 0.5


def _detect_market_regime(ohlcv: pd.DataFrame, macro_data: dict, tv_ta: dict = None) -> tuple[str, dict[str, float]]:
    """
    Detect market regime (VOLATILE, TRENDING, CONSOLIDATION) and return dynamic weights including news (15%).
    - VOLATILE: Macro 35%, Breadth 25%, Momentum 15%, Sector 10%, News 15%
    - TRENDING: Momentum 30%, Breadth 25%, Sector 15%, Macro 15%, News 15%
    - CONSOLIDATION: Breadth 35%, Sector 20%, Momentum 15%, Macro 15%, News 15%
    """
    is_volatile = macro_data.get("is_volatile", False)
    usdidr = float(macro_data.get("usdidr") or 15800.0)
    ihsg_vs_ma = float(macro_data.get("ihsg_vs_ma20") or 0.0)

    tv_summary = tv_ta.get("summary", {}).get("RECOMMENDATION", "") if tv_ta else ""

    # 1. Check Volatile regime
    if is_volatile or usdidr > 18500 or usdidr < 15500:
        regime = "VOLATILE"
        weights = {"macro": 0.35, "breadth": 0.25, "momentum": 0.15, "sectors": 0.10, "news": 0.15}

    # 2. Check Trending regime
    elif abs(ihsg_vs_ma) > 2.0 or "STRONG" in tv_summary:
        regime = "TRENDING"
        weights = {"momentum": 0.30, "breadth": 0.25, "sectors": 0.15, "macro": 0.15, "news": 0.15}

    # 3. Consolidation regime (default)
    else:
        regime = "CONSOLIDATION"
        weights = {"breadth": 0.35, "sectors": 0.20, "momentum": 0.15, "macro": 0.15, "news": 0.15}

    logger.info(f"[Regime Detector] Detected Regime: {regime}, Weights: {weights}")
    return regime, weights


def _project_predictions(current_price: float, daily_pct_move: float, atr_pct: float = 1.0) -> dict:
    """
    Project D1/D3/D5/D7 price targets with ATR-calibrated cumulative move.
    Formula: cum_pct = daily_move * days * damping_factor
    - D+1: 1 * 1.00 = 1.00x daily move
    - D+3: 3 * 0.75 = 2.25x daily move
    - D+5: 5 * 0.60 = 3.00x daily move
    - D+7: 7 * 0.45 = 3.15x daily move
    """
    predictions = {}
    horizons = [(1, 1.00), (3, 0.75), (5, 0.60), (7, 0.45)]

    for day, damp in horizons:
        cum_pct = daily_pct_move * day * damp
        # Cap realistic multi-day move range based on ATR (max 4x ATR)
        max_limit = max(3.0, atr_pct * 4.0)
        cum_pct = max(-max_limit, min(max_limit, cum_pct))
        projected_price = current_price * (1 + cum_pct / 100)
        predictions[f"day_{day}_price"] = float(round(float(projected_price), 0))
        predictions[f"day_{day}_pct"] = float(round(float(cum_pct), 2))

    predictions["atr_14_pct"] = atr_pct
    return predictions


def _calculate_5y_fibonacci(ohlcv: pd.DataFrame) -> dict:
    """Calculate 5-year Fibonacci Retracements & Expansions from OHLCV data."""
    try:
        if ohlcv is None or len(ohlcv) < 50:
            return {}
        df = ohlcv.copy()
        if not isinstance(df.index, pd.DatetimeIndex):
            df.index = pd.to_datetime(df.index)
        cutoff_5y = pd.Timestamp.now() - pd.Timedelta(days=5*365)
        df_5y = df[df.index >= cutoff_5y]
        if df_5y.empty:
            df_5y = df

        high_5y = float(df_5y["High"].max())
        low_5y = float(df_5y["Low"].min())
        diff = high_5y - low_5y

        return {
            "high_5y": round(high_5y, 0),
            "low_5y": round(low_5y, 0),
            "fib_236": round(high_5y - diff * 0.236, 0),
            "fib_382": round(high_5y - diff * 0.382, 0),
            "fib_500": round(high_5y - diff * 0.500, 0),
            "fib_618": round(high_5y - diff * 0.618, 0),
            "fib_786": round(high_5y - diff * 0.786, 0),
            "fib_exp_1272": round(low_5y + diff * 1.272, 0),
            "fib_exp_1618": round(low_5y + diff * 1.618, 0),
        }
    except Exception as e:
        logger.warning(f"[Fibonacci] Error calculating 5y Fib: {e}")
        return {}


def _calculate_ihsg_seasonality(ohlcv: pd.DataFrame) -> dict:
    """Extract historical monthly seasonality win rates & avg returns."""
    try:
        if ohlcv is None or len(ohlcv) < 200:
            return {}
        df = ohlcv.copy()
        if not isinstance(df.index, pd.DatetimeIndex):
            df.index = pd.to_datetime(df.index)
        df["Month"] = df.index.month
        df["Year"] = df.index.year
        monthly = df.groupby(["Year", "Month"])["Close"].agg(["first", "last"])
        monthly["ret"] = (monthly["last"] - monthly["first"]) / monthly["first"] * 100
        
        seasonality = {}
        month_names = {1:"Januari", 2:"Februari", 3:"Maret", 4:"April", 5:"Mei", 6:"Juni",
                       7:"Juli", 8:"Agustus", 9:"September", 10:"Oktober", 11:"November", 12:"Desember"}
        
        for m in range(1, 13):
            m_data = monthly[monthly.index.get_level_values("Month") == m]
            if not m_data.empty:
                avg_ret = float(m_data["ret"].mean())
                win_rate = float((m_data["ret"] > 0).mean() * 100)
                seasonality[m] = {
                    "month_name": month_names[m],
                    "avg_return_pct": round(avg_ret, 2),
                    "win_rate_pct": round(win_rate, 1)
                }
        return seasonality
    except Exception as e:
        logger.warning(f"[Seasonality] Error: {e}")
        return {}


def predict_ihsg_1year_outlook(ohlcv: pd.DataFrame, current_price: float, tv_ta_weekly: dict = None, tv_ta_monthly: dict = None) -> dict:
    """
    Generate 1-Year IHSG Technical Outlook, Bottom/Top Confluence Zones, Reversal Triggers, and Timing Window.
    """
    try:
        fib_levels = _calculate_5y_fibonacci(ohlcv)
        seasonality = _calculate_ihsg_seasonality(ohlcv)
        atr_pct = _calculate_atr(ohlcv, period=14)

        # Weekly & Monthly indicators from TradingView TA
        w_indicators = tv_ta_weekly.get("indicators", {}) if tv_ta_weekly else {}
        w_summary = tv_ta_weekly.get("summary", {}) if tv_ta_weekly else {}
        m_indicators = tv_ta_monthly.get("indicators", {}) if tv_ta_monthly else {}

        # MAs from weekly TA
        sma50_w = float(w_indicators.get("SMA50") or (ohlcv["Close"].astype(float).rolling(250).mean().iloc[-1] if ohlcv is not None else current_price))
        sma200_w = float(w_indicators.get("SMA200") or (ohlcv["Close"].astype(float).rolling(1000).mean().iloc[-1] if ohlcv is not None else current_price * 0.90))

        # Monthly Pivot Supports & Resistances
        p_s1 = float(m_indicators.get("Pivot.M.Fibonacci.S1") or m_indicators.get("Pivot.M.Classic.S1") or (current_price * 0.95))
        p_s2 = float(m_indicators.get("Pivot.M.Fibonacci.S2") or m_indicators.get("Pivot.M.Classic.S2") or (current_price * 0.90))
        ema100_m = float(m_indicators.get("EMA100") or (current_price * 0.95))

        p_r1 = float(m_indicators.get("Pivot.M.Fibonacci.R1") or m_indicators.get("Pivot.M.Classic.R1") or (current_price * 1.05))
        p_r2 = float(m_indicators.get("Pivot.M.Fibonacci.R2") or m_indicators.get("Pivot.M.Classic.R2") or (current_price * 1.10))
        ema20_m = float(m_indicators.get("EMA20") or (current_price * 1.05))

        # 1-Year Fibonacci Retracements & Expansions
        fib_382 = fib_levels.get("fib_382", current_price * 0.95)
        fib_500 = fib_levels.get("fib_500", current_price * 0.90)

        # Bottom Support Confluence (Find closest realistic support within 15% below current price)
        all_supports = [s for s in [p_s1, p_s2, ema100_m, sma200_w, fib_382, fib_500] if s < current_price]
        immediate_supports = [s for s in all_supports if s >= current_price * 0.85]
        if immediate_supports:
            bottom_level = round(float(np.max(immediate_supports)), 0)
        elif all_supports:
            bottom_level = round(float(np.max(all_supports)), 0)
        else:
            bottom_level = round(current_price * 0.92, 0)

        # Top Resistance Confluence (Find closest realistic resistance within 20% above current price)
        all_resistances = [r for r in [p_r1, p_r2, ema20_m, sma50_w] if r > current_price]
        immediate_resistances = [r for r in all_resistances if r <= current_price * 1.20]
        if immediate_resistances:
            top_level = round(float(np.min(immediate_resistances)), 0)
        elif all_resistances:
            top_level = round(float(np.min(all_resistances)), 0)
        else:
            top_level = round(current_price * 1.10, 0)

        # Downside Risk & Upside Potential
        downside_risk_pct = round(((bottom_level - current_price) / current_price) * 100, 2)
        upside_potential_pct = round(((top_level - current_price) / current_price) * 100, 2)

        # 1-Year Trend Direction
        w_rec = w_summary.get("RECOMMENDATION", "").upper()
        if "BUY" in w_rec or current_price > sma200_w:
            direction_1y = "BULLISH"
        else:
            direction_1y = "BEARISH"

        # Reversal Confirmation Triggers
        is_above_ma50_w = current_price > sma50_w
        bullish_reversal_confirmed = is_above_ma50_w
        bearish_reversal_confirmed = not is_above_ma50_w

        # Reversal Timing Estimation
        target_dist = abs(bottom_level - current_price) if direction_1y == "BEARISH" else abs(top_level - current_price)
        weekly_move_est = (atr_pct / 100) * current_price
        est_weeks = max(2, min(12, int(round(target_dist / max(1.0, weekly_move_est)))))

        # Target Month Calculation
        curr_month = datetime.now().month
        curr_year = datetime.now().year
        est_months_ahead = max(1, int(round(est_weeks / 4)))
        target_month_num = (curr_month + est_months_ahead - 1) % 12 + 1
        target_year_add = (curr_month + est_months_ahead - 1) // 12
        target_month_name = seasonality.get(target_month_num, {}).get("month_name", "N/A")
        target_month_window = f"{target_month_name} {curr_year + target_year_add} (±{est_weeks} Minggu)"

        # Best Historical Seasonality Reversal Month
        best_month_data = max(seasonality.values(), key=lambda x: x.get("win_rate_pct", 0)) if seasonality else {}
        worst_month_data = min(seasonality.values(), key=lambda x: x.get("win_rate_pct", 0)) if seasonality else {}

        return {
            "direction_1year": direction_1y,
            "bottom_confluence_level": bottom_level,
            "top_confluence_level": top_level,
            "downside_risk_pct": downside_risk_pct,
            "upside_potential_pct": upside_potential_pct,
            "ma50_weekly": round(sma50_w, 0),
            "ma200_weekly": round(sma200_w, 0),
            "is_above_ma50_weekly": is_above_ma50_w,
            "bullish_reversal_confirmed": bullish_reversal_confirmed,
            "bearish_reversal_confirmed": bearish_reversal_confirmed,
            "estimated_reversal_weeks": est_weeks,
            "estimated_reversal_window": target_month_window,
            "best_seasonal_month": best_month_data.get("month_name", "Juli"),
            "best_seasonal_win_rate": best_month_data.get("win_rate_pct", 100.0),
            "worst_seasonal_month": worst_month_data.get("month_name", "Maret"),
            "worst_seasonal_win_rate": worst_month_data.get("win_rate_pct", 12.5),
            "fib_levels": fib_levels,
            "monthly_pivots": {
                "S1": round(p_s1, 0), "S2": round(p_s2, 0), "EMA100_M": round(ema100_m, 0),
                "R1": round(p_r1, 0), "R2": round(p_r2, 0), "EMA20_M": round(ema20_m, 0)
            }
        }
    except Exception as e:
        logger.exception(f"[1-Year Outlook] Error: {e}")
        return {}



def _generate_narrative_with_llm(direction: str, confidence: str, combined_score: float, 
                               momentum: float, breadth: float, macro: float, sector: float, 
                               d1_pct: float, current_price: float, usdidr: float, 
                               recent_news: list) -> dict:
    """Call LLM to generate reasoning, drivers, and risks based on calculated scores."""
    if not LLM_ENABLED:
        return None
        
    try:
        # Build News String
        news_text = ""
        if recent_news:
            news_items = []
            for n in recent_news:
                title = n.get('summary', '').replace('\n', ' ')
                sent = n.get('sentiment', 'Neutral')
                news_items.append(f"- [{sent}] {title}")
            news_text = "Berita Terbaru:\n" + "\n".join(news_items)
            
        context = {
            "prediksi_arah": direction,
            "tingkat_keyakinan": confidence,
            "skor_gabungan": round(combined_score, 2),
            "target_besok": f"{d1_pct:+.2f}%",
            "metrik": {
                "market_breadth_score": round(breadth, 2),
                "momentum_score": round(momentum, 2),
                "macro_score": round(macro, 2),
                "sector_score": round(sector, 2)
            },
            "data_tambahan": {
                "ihsg_sekarang": current_price,
                "usd_idr": usdidr
            }
        }
        
        user_prompt = f"""Tugas: Buat analisis pergerakan IHSG untuk 1 minggu ke depan berdasarkan metrik matematis berikut.
Kamu harus menjelaskan MENGAPA algoritma memprediksi arah {direction} dengan meninjau skor komponennya (Breadth, Momentum, Makro, Sektor, dan News Sentiment).
Gunakan bahasa analis profesional dalam Bahasa Indonesia (Investment Manager).

Data Sistem:
{json.dumps(context, indent=2)}

{news_text}

Output dalam JSON format saja (tanpa markdown blok):
{{
    "reasoning": "Opini analis singkat (2-3 kalimat max) menjelaskan sentimen teknikal dan makro IHSG.",
    "key_drivers": ["poin katalis 1", "poin katalis 2"],
    "risks": ["poin risiko 1", "poin risiko 2"]
}}
"""
        
        raw = invoke_json_im(
            LLM_MODEL_INVESTMENT_MANAGER,
            IM_SYSTEM_PROMPT,
            user_prompt,
            fallback_model=LLM_MODEL_IM_FALLBACK
        )
        return raw
    except Exception as e:
        logger.warning(f"Failed to generate LLM narrative: {e}")
        return None

def predict_ihsg() -> dict:
    """
    Main IHSG prediction function.
    Returns complete prediction dict with direction, targets, confidence, components.
    """
    try:
        logger.info("[IHSG Predictor] Starting prediction...")

        # Fetch data
        ohlcv = get_ihsg_ohlcv(period="8y")
        breadth = get_market_breadth()
        sectors = get_sector_rotation()
        macro_data = macro_analyze()

        # Fetch News Agent (RAG Context)
        news_sentiment_score = 0.5
        try:
            from scripts.rag_retriever import search_by_ticker
            # IHSG usually affected by global or macro news without specific ticker
            # We search for empty ticker list to get general market news
            recent_news = search_by_ticker("COMPOSITE", limit=5)
            if not recent_news:
                # Fallback check empty ticker
                from scripts.rag_retriever import _execute_query
                recent_news = _execute_query("SELECT stream_id, content, summary, sentiment FROM news_signals WHERE jsonb_array_length(tickers) = 0 ORDER BY created_at DESC LIMIT 5", ())
            
            if recent_news:
                # Include Neutral but give it a slight positive skew if it contains macro keywords, or just count strictly
                bullish_count = sum(1 for n in recent_news if n.get("sentiment") == "Bullish")
                bearish_count = sum(1 for n in recent_news if n.get("sentiment") == "Bearish")
                
                # Treat some "Neutral" macro news as slightly bullish if it's actually good (like rating retained)
                for n in recent_news:
                    if n.get("sentiment") == "Neutral":
                        text = (n.get("summary", "") + " " + n.get("content", "")).lower()
                        if "pertahankan rating" in text or "stable" in text or "membaik" in text:
                            bullish_count += 0.5
                            
                total_scored = bullish_count + bearish_count
                if total_scored > 0:
                    news_sentiment_score = 0.5 + ((bullish_count - bearish_count) / total_scored) * 0.3
                    # Clamp between 0 and 1
                    news_sentiment_score = max(0.0, min(1.0, news_sentiment_score))
                
                logger.info(f"[IHSG Predictor] News Sentiment Score: {news_sentiment_score:.2f} (Bullish: {bullish_count}, Bearish: {bearish_count})")
        except Exception as e:
            logger.warning(f"[IHSG Predictor] Failed to fetch news context: {e}")

        if ohlcv is None or ohlcv.empty:
            logger.error("[IHSG] No OHLCV data available")
            return _empty_prediction()

        # Get current price from Stockbit realtime if available, fallback to ohlcv
        try:
            from data.fetcher_stockbit import get_ihsg_realtime_price_stockbit
            realtime = get_ihsg_realtime_price_stockbit()
            if realtime and realtime.get("price", 0) > 0:
                current_price = float(realtime["price"])
                logger.info(f"[IHSG Predictor] Using realtime price from Stockbit: {current_price}")
            else:
                current_price = float(ohlcv["Close"].iloc[-1])
                logger.info(f"[IHSG Predictor] Using last close price from OHLCV: {current_price}")
        except Exception as e:
            logger.warning(f"[IHSG Predictor] Failed to get realtime price, falling back to OHLCV: {e}")
            current_price = float(ohlcv["Close"].iloc[-1])

        # Fetch TradingView TA data for IHSG
        tv_ta = get_ihsg_technical_analysis()

        # Calculate component scores
        momentum_score = _calculate_momentum_score(ohlcv, macro_data, tv_ta)
        breadth_score = _calculate_breadth_score(breadth)
        macro_score = _calculate_macro_score(macro_data)
        sector_score = _calculate_sector_score(sectors)

        # Detect Market Regime & Dynamic Weighting
        market_regime, weights = _detect_market_regime(ohlcv, macro_data, tv_ta)

        # Weighted combination based on detected regime (including news_sentiment_score)
        combined_score = (
            momentum_score * weights["momentum"] +
            breadth_score * weights["breadth"] +
            macro_score * weights["macro"] +
            sector_score * weights["sectors"] +
            news_sentiment_score * weights["news"]
        )
        combined_score = float(combined_score)

        # Strict Binary Direction Determination (BULLISH vs BEARISH)
        direction = "BULLISH" if combined_score >= 0.50 else "BEARISH"

        # Confidence (based on score distance from 0.50 and component consensus)
        score_diff = abs(combined_score - 0.50)
        consensus = (
            (direction == "BULLISH" and momentum_score >= 0.52 and breadth_score >= 0.52) or
            (direction == "BEARISH" and momentum_score < 0.48 and breadth_score < 0.48)
        )
        if score_diff >= 0.08 or (score_diff >= 0.05 and consensus):
            confidence = "HIGH"
        elif score_diff >= 0.03:
            confidence = "MEDIUM"
        else:
            confidence = "LOW"

        # Calculate ATR and ATR-calibrated project predictions
        atr_pct = _calculate_atr(ohlcv, period=14)
        daily_move_pct = float((combined_score - 0.50) * 2.0 * atr_pct)
        predictions = _project_predictions(current_price, daily_move_pct, atr_pct)

        # 1-Year Outlook & Reversal Pivot Detector
        try:
            tv_ta_weekly = get_ihsg_technical_analysis(interval="1W")
            tv_ta_monthly = get_ihsg_technical_analysis(interval="1M")
            one_year_outlook = predict_ihsg_1year_outlook(ohlcv, current_price, tv_ta_weekly, tv_ta_monthly)
        except Exception as e:
            logger.warning(f"[IHSG Predictor] Failed to compute 1-year outlook: {e}")
            one_year_outlook = {}

        usdidr_for_display = macro_data.get("usdidr")
        if usdidr_for_display is None:
            usdidr_for_display = 15800.0

        # Build result
        # Call LLM
        llm_narrative = _generate_narrative_with_llm(
            direction, confidence, combined_score,
            momentum_score, breadth_score, macro_score, sector_score,
            float(daily_move_pct), float(current_price), float(usdidr_for_display),
            recent_news if 'recent_news' in locals() else []
        )
        
        reasoning_text = f"IHSG {direction} (Rezim {market_regime}): Combined score {combined_score:.2f} ({confidence} confidence)."
        drivers_list = _extract_drivers(momentum_score, breadth_score, macro_score, sector_score)
        risks_list = _extract_risks(momentum_score, breadth_score, macro_score)
        
        if llm_narrative:
            reasoning_text = llm_narrative.get("reasoning", reasoning_text)
            drivers_list = llm_narrative.get("key_drivers", drivers_list)
            risks_list = llm_narrative.get("risks", risks_list)
        
        result = {
            "current_price": round(current_price, 0),
            "confidence": confidence,
            "direction": direction,
            "volatility_level": "HIGH" if abs(daily_move_pct) > 1.5 else "MEDIUM" if abs(daily_move_pct) > 0.5 else "LOW",
            "market_regime": market_regime,
            "regime_weights": weights,
            "component_scores": {
                "momentum": round(momentum_score, 2),
                "breadth": round(breadth_score, 2),
                "macro": round(macro_score, 2),
                "sectors": round(sector_score, 2),
                "news": round(news_sentiment_score, 2),
                "combined": round(combined_score, 2),
            },
            "one_year_outlook": one_year_outlook,
            "reasoning": reasoning_text,
            "key_drivers": drivers_list,
            "risks": risks_list,
            "data_used": [
                f"IHSG: {current_price:,.0f}",
                f"Market Regime: {market_regime}",
                f"A/D Ratio: {breadth.get('advance_decline_ratio', 1.0):.2f}",
                f"Participation: {breadth.get('participation_above_ma20', 50):.1f}%",
                f"USD/IDR: {float(usdidr_for_display):.0f}",
                f"Sector Leading: {sectors.get('leading_sector', 'N/A')}",
                f"ATR (14d): {atr_pct:.2f}%",
            ],
            "ihsg_trend": macro_data.get("ihsg_trend", "UNKNOWN"),
            "macro_signal": "BULLISH" if macro_score > 0.6 else "BEARISH" if macro_score < 0.4 else "NEUTRAL",
            "timestamp": datetime.now().isoformat(),
        }

        # Add predictions
        result.update(predictions)

        logger.info(f"[IHSG] Prediction: {direction} ({confidence}), Score={combined_score:.2f}")
        return result

    except Exception as e:
        logger.exception(f"[IHSG Predictor] Fatal error: {e}")
        return _empty_prediction()


def _extract_drivers(momentum: float, breadth: float, macro: float, sector: float) -> list[str]:
    """Extract top 3 drivers."""
    drivers = []
    if momentum > 0.65:
        drivers.append("Momentum technical kuat (RSI/MACD bullish)")
    if breadth > 0.65:
        drivers.append("Breadth pasar positif (A/D ratio > 1.5)")
    if macro > 0.65:
        drivers.append("Sentimen makro supportif (IDR kuat, IHSG above MA20)")
    if sector > 0.65:
        drivers.append("Rotasi sektor ke cyclical/defensive positif")
    return drivers[:3] if drivers else ["Mixed signals"]


def _extract_risks(momentum: float, breadth: float, macro: float) -> list[str]:
    """Extract top risks."""
    risks = []
    if momentum < 0.35:
        risks.append("Momentum teknis lemah")
    if breadth < 0.35:
        risks.append("Breadth pasar negatif (losers > gainers)")
    if macro < 0.35:
        risks.append("Tekanan makro (IDR lemah, volatilitas tinggi)")
    return risks[:2] if risks else ["Limited downside"]


def _empty_prediction() -> dict:
    """Return empty/neutral prediction on error."""
    return {
        "current_price": 0,
        "confidence": "LOW",
        "direction": "BEARISH",
        "volatility_level": "MEDIUM",
        "component_scores": {
            "momentum": 0.5,
            "breadth": 0.5,
            "macro": 0.5,
            "sectors": 0.5,
            "combined": 0.5,
        },
        "reasoning": "Data not available",
        "key_drivers": ["N/A"],
        "risks": ["Data error"],
        "data_used": ["ERROR"],
        "day_1_price": 0,
        "day_1_pct": 0.0,
        "day_3_price": 0,
        "day_3_pct": 0.0,
        "day_5_price": 0,
        "day_5_pct": 0.0,
        "day_7_price": 0,
        "day_7_pct": 0.0,
    }
