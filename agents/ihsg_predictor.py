"""
IHSG Predictor Agent
Prediksi direction IHSG (BULLISH/BEARISH/SIDEWAYS) dengan D1/D3/D5/D7 price targets.
Rule-based scoring (4 components) + optional LLM narrative.
"""
import logging
from datetime import datetime
import pandas as pd

from data.fetcher_ihsg import get_ihsg_ohlcv, get_market_breadth, get_sector_rotation
from agents.macro import analyze as macro_analyze
from config import LLM_ENABLED

logger = logging.getLogger(__name__)


def _calculate_rsi(prices: pd.Series, period: int = 14) -> float:
    """Calculate RSI."""
    if len(prices) < period + 1:
        return 50.0
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss.replace(0, 1e-10)
    rsi = 100 - (100 / (1 + rs))
    return float(rsi.iloc[-1]) if not pd.isna(rsi.iloc[-1]) else 50.0


def _calculate_macd(prices: pd.Series) -> tuple[float, float]:
    """Calculate MACD and signal line. Returns (macd, signal)."""
    if len(prices) < 26:
        return 0.0, 0.0
    ema12 = prices.ewm(span=12, adjust=False).mean()
    ema26 = prices.ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    signal = macd.ewm(span=9, adjust=False).mean()
    return float(macd.iloc[-1]), float(signal.iloc[-1])


def _calculate_momentum_score(ohlcv: pd.DataFrame, macro_data: dict) -> float:
    """
    Score momentum (RSI, MACD, MA positioning).
    Returns: float [0, 1]
    """
    if ohlcv is None or len(ohlcv) < 20:
        return 0.5

    try:
        close = ohlcv["Close"]
        rsi = _calculate_rsi(close, 14)
        macd, signal = _calculate_macd(close)

        score = 0.5

        # RSI component (normalized 0-100 to 0-1, sigmoid-like)
        rsi_norm = (rsi - 30) / 40  # 30 = neutral, 70 = overbought
        rsi_norm = max(0, min(1, rsi_norm))
        score += (rsi_norm - 0.5) * 0.2  # Max ±0.1 contribution

        # MACD component
        if macd > signal and signal > 0:
            score += 0.15  # Bullish
        elif macd < signal and signal < 0:
            score -= 0.15  # Bearish

        # MA positioning (price vs MA20/50/100)
        ma20 = close.rolling(20).mean().iloc[-1]
        ma50 = close.rolling(50).mean().iloc[-1] if len(close) >= 50 else ma20
        ma100 = close.rolling(100).mean().iloc[-1] if len(close) >= 100 else ma50

        current_price = close.iloc[-1]
        above_mas = sum([current_price > ma for ma in [ma20, ma50, ma100]])
        score += (above_mas / 3 - 0.5) * 0.2  # ±0.1 contribution

        score = max(0.0, min(1.0, score))
        logger.info(f"[Momentum] RSI={rsi:.1f}, MACD={macd:.4f}, Score={score:.2f}")
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

        if usdidr < 15500:
            score += 0.15  # Strong IDR
        elif usdidr > 16500:
            score -= 0.15  # Weak IDR
        else:
            usdidr_norm = (usdidr - 16000) / 1000  # 16000 = neutral
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
    Score sector rotation (divergence, leading sector strength).
    Returns: float [0, 1]
    """
    try:
        score = 0.5
        divergence = sectors.get("divergence", 0.0)
        leading_sector = sectors.get("leading_sector", "neutral")

        # Divergence indicates rotation
        if divergence > 3.0:
            score += 0.15  # Strong rotation

        # Leading sector type
        if leading_sector in ["perbankan", "consumer"]:
            score += 0.1  # Defensive = moderate bullish
        elif leading_sector in ["mining", "infrastructure"]:
            score += 0.15  # Cyclical = strong bullish
        elif leading_sector == "property":
            score += 0.05  # Mixed signal

        score = max(0.0, min(1.0, score))
        logger.info(f"[Sectors] Divergence={divergence:.2f}%, Leading={leading_sector}, Score={score:.2f}")
        return score

    except Exception as e:
        logger.warning(f"[Sectors] Error: {e}")
        return 0.5


def _project_predictions(current_price: float, daily_pct_move: float, volatility: float) -> dict:
    """
    Project D1/D3/D5/D7 price targets with volatility damping.
    Volatility decreases as days increase.
    """
    predictions = {}
    volatility_damping = [1.0, 0.9, 0.7, 0.5]  # D1, D3, D5, D7

    for i, (day, damp) in enumerate(zip([1, 3, 5, 7], volatility_damping)):
        damped_move = daily_pct_move * damp
        projected_price = current_price * (1 + damped_move / 100)
        predictions[f"day_{day}_price"] = float(round(float(projected_price), 0))
        predictions[f"day_{day}_pct"] = float(round(float(damped_move), 2))

    return predictions


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

        if ohlcv is None or ohlcv.empty:
            logger.error("[IHSG] No OHLCV data available")
            return _empty_prediction()

        current_price = float(ohlcv["Close"].iloc[-1])

        # Calculate component scores
        momentum_score = _calculate_momentum_score(ohlcv, macro_data)
        breadth_score = _calculate_breadth_score(breadth)
        macro_score = _calculate_macro_score(macro_data)
        sector_score = _calculate_sector_score(sectors)

        # Weighted combination
        combined_score = (
            momentum_score * 0.35 +
            breadth_score * 0.30 +
            macro_score * 0.20 +
            sector_score * 0.15
        )
        combined_score = float(combined_score)

        # Direction determination
        if combined_score > 0.6:
            direction = "BULLISH"
        elif combined_score < 0.4:
            direction = "BEARISH"
        else:
            direction = "SIDEWAYS"

        # Confidence (based on score agreement)
        if (momentum_score > 0.6 and breadth_score > 0.6 and macro_score > 0.6) or \
           (momentum_score < 0.4 and breadth_score < 0.4 and macro_score < 0.4):
            confidence = "HIGH"
        elif abs(combined_score - 0.5) > 0.15:
            confidence = "MEDIUM"
        else:
            confidence = "LOW"

        # Project predictions
        daily_move_pct = float((combined_score - 0.5) * 2 * 2.5)  # ±2.5% range
        predictions = _project_predictions(current_price, daily_move_pct, 0.0)

        usdidr_for_display = macro_data.get("usdidr")
        if usdidr_for_display is None:
            usdidr_for_display = 15800.0

        # Build result
        result = {
            "current_price": round(current_price, 0),
            "confidence": confidence,
            "direction": direction,
            "volatility_level": "HIGH" if abs(daily_move_pct) > 1.5 else "MEDIUM" if abs(daily_move_pct) > 0.5 else "LOW",
            "component_scores": {
                "momentum": round(momentum_score, 2),
                "breadth": round(breadth_score, 2),
                "macro": round(macro_score, 2),
                "sectors": round(sector_score, 2),
                "combined": round(combined_score, 2),
            },
            "reasoning": f"IHSG {direction}: Combined score {combined_score:.2f} ({confidence} confidence). "
                        f"Momentum={momentum_score:.2f}, Breadth={breadth_score:.2f}, "
                        f"Macro={macro_score:.2f}, Sectors={sector_score:.2f}",
            "key_drivers": _extract_drivers(momentum_score, breadth_score, macro_score, sector_score),
            "risks": _extract_risks(momentum_score, breadth_score, macro_score),
            "data_used": [
                f"IHSG: {current_price:,.0f}",
                f"A/D Ratio: {breadth.get('advance_decline_ratio', 1.0):.2f}",
                f"Participation: {breadth.get('participation_above_ma20', 50):.1f}%",
                f"USD/IDR: {float(usdidr_for_display):.0f}",
                f"Sector Leading: {sectors.get('leading_sector', 'N/A')}",
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
        "direction": "SIDEWAYS",
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
