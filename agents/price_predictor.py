"""
Agent — Price Predictor
Prediksi pergerakan harga harian (day 1, 3, 5, 7) menggunakan hybrid approach:
- Rule-based: momentum, volume, bandarm strength, macro
- LLM enhancement: reasoning dan adjustment
"""
from __future__ import annotations
import logging
from typing import Any

from agents.llm_client import invoke_json_im
from config import LLM_ENABLED, LLM_MODEL_INVESTMENT_MANAGER, LLM_MODEL_IM_FALLBACK

logger = logging.getLogger(__name__)

# Konstanta untuk rule-based calculation
MAX_DAILY_MOVE_PCT = 3.0  # Maksimal 3% per hari
COMPOUND_FACTORS = {
    1: 1.0,
    3: 1.5,
    5: 2.2,
    7: 3.0,
}


def _calculate_momentum_score(tech_data: dict) -> float:
    """
    Calculate technical momentum score (0-1).
    Higher = more bullish momentum.
    """
    score = 0.5  # neutral baseline
    
    # RSI contribution
    macd = tech_data.get("macd") or {}
    macd_cross = macd.get("cross", "")
    if macd_cross == "golden_cross":
        score += 0.3
    elif macd_cross == "bullish":
        score += 0.15
    elif macd_cross == "death_cross":
        score -= 0.3
    elif macd_cross == "bearish":
        score -= 0.15
    
    # Divergence signals
    divergence = tech_data.get("divergence", {})
    if divergence.get("rsi") == "bullish" or divergence.get("macd") == "bullish":
        score += 0.2
    elif divergence.get("rsi") == "bearish" or divergence.get("macd") == "bearish":
        score -= 0.2
    
    # Trend
    trend = (tech_data.get("trend") or "").lower()
    if trend == "bullish":
        score += 0.15
    elif trend == "bearish":
        score -= 0.15
    
    return max(0.0, min(1.0, score))


def _calculate_volume_score(tech_data: dict) -> float:
    """
    Calculate volume trend score (0-1).
    Based on volume ratio from technical analysis.
    """
    score = 0.5  # neutral baseline
    
    # Parse volume info from data_used
    data_used = tech_data.get("data_used", [])
    vol_ratio = None
    for item in data_used:
        if "Vol ratio" in item and ":" in item:
            try:
                vol_ratio = float(item.split(":")[-1].strip())
                break
            except (ValueError, IndexError):
                pass
    
    if vol_ratio is not None:
        if vol_ratio > 1.5:
            score = 0.9
        elif vol_ratio > 1.2:
            score = 0.7
        elif vol_ratio < 0.5:
            score = 0.2
        elif vol_ratio < 0.8:
            score = 0.4
    
    return score


def _calculate_bandarm_strength(bandarm_data: dict) -> float:
    """
    Calculate bandarmologi accumulation strength (0-1).
    Higher = stronger accumulation.
    """
    score = 0.5  # neutral baseline
    
    signal = (bandarm_data.get("signal") or "").upper()
    
    if signal == "STRONG_ACCUMULATION":
        score = 0.95
    elif signal == "ACCUMULATION":
        score = 0.75
    elif signal == "NEUTRAL":
        score = 0.5
    elif signal == "DISTRIBUTION":
        score = 0.2
    
    # Adjust based on confidence
    confidence = bandarm_data.get("confidence", "MEDIUM")
    if confidence == "HIGH":
        pass  # no adjustment
    elif confidence == "MEDIUM":
        score = score * 0.9 + 0.5 * 0.1  # pull slightly toward neutral
    elif confidence == "LOW":
        score = score * 0.7 + 0.5 * 0.3  # pull more toward neutral
    
    return score


def _calculate_macro_score(macro_data: dict) -> float:
    """
    Calculate macro sentiment score (0-1).
    """
    macro_score = macro_data.get("score", 5.0)
    # Normalize from 1-10 scale to 0-1
    return (macro_score - 1.0) / 9.0


def calculate_base_prediction(
    ticker: str,
    scores: dict,
    composites: dict,
    macro_data: dict,
    ml_prediction: dict = None,
) -> dict:
    """
    Calculate rule-based price movement prediction.
    Returns base prediction before LLM enhancement.
    """
    ticker_scores = scores.get(ticker, {})
    tech_data = ticker_scores.get("technical", {})
    bandarm_data = ticker_scores.get("bandarm", {})
    
    # Calculate component scores
    momentum_score = _calculate_momentum_score(tech_data)
    volume_score = _calculate_volume_score(tech_data)
    bandarm_score = _calculate_bandarm_strength(bandarm_data)
    macro_score = _calculate_macro_score(macro_data)
    
    # Weighted combination
    combined_score = (
        momentum_score * 0.30 +
        volume_score * 0.25 +
        bandarm_score * 0.30 +
        macro_score * 0.15
    )
    
    # Calculate base daily % (scale by MAX_DAILY_MOVE_PCT)
    # combined_score range is 0-1, we map it to -MAX to +MAX
    # 0.5 = neutral (0% move), 1.0 = +MAX, 0.0 = -MAX
    base_daily_pct = (combined_score - 0.5) * 2 * MAX_DAILY_MOVE_PCT
    
    # Get current price from bandarm price_analysis
    price_analysis = bandarm_data.get("price_analysis", {})
    current_price = price_analysis.get("current_price", 0)
    
    if current_price == 0:
        # Fallback: try to get from technical or composite
        logger.warning(f"[PREDICTOR] No current price for {ticker}")
        return None
    
    # Generate predictions for each day
    predictions = {}

    # If we have real Multi-Day ML predictions from workflow, use them instead of linear fallback!
    multiday_pcts = {}
    if ml_prediction and "predictions_multiday" in ml_prediction:
        multiday_pcts = ml_prediction["predictions_multiday"]

    for day, factor in COMPOUND_FACTORS.items():
        if f"{day}d" in multiday_pcts:
            # Real ML Prediction
            day_pct = multiday_pcts[f"{day}d"]
        else:
            # Fallback to legacy linear rule-based if ML not provided
            day_pct = base_daily_pct * factor

        predicted_price = current_price * (1 + day_pct / 100)

        # Ranges get wider as horizon increases
        range_padding = 0.02 + (0.01 * float(day))
        price_range_low = predicted_price * (1 - range_padding)
        price_range_high = predicted_price * (1 + range_padding)

        predictions[f"day_{day}"] = {
            "price": round(predicted_price, 0),
            "pct_change": f"{day_pct:+.2f}%",
            "price_range": [round(price_range_low, 0), round(price_range_high, 0)],
        }
    
    return {
        "current_price": current_price,
        "predictions": predictions,
        "base_daily_pct": round(base_daily_pct, 2),
        "component_scores": {
            "momentum": round(momentum_score, 2),
            "volume": round(volume_score, 2),
            "bandarm": round(bandarm_score, 2),
            "macro": round(macro_score, 2),
            "combined": round(combined_score, 2),
        },
    }


def _build_llm_context(
    ticker: str,
    base_prediction: dict,
    scores: dict,
    composites: dict,
    macro_data: dict,
) -> dict:
    """Build context for LLM enhancement."""
    ticker_scores = scores.get(ticker, {})
    
    return {
        "ticker": ticker,
        "base_prediction": base_prediction,
        "technical_summary": {
            "score": ticker_scores.get("technical", {}).get("score"),
            "signal": ticker_scores.get("technical", {}).get("signal"),
            "trend": ticker_scores.get("technical", {}).get("trend"),
            "setup": ticker_scores.get("technical", {}).get("setup"),
        },
        "bandarmologi_summary": {
            "score": ticker_scores.get("bandarm", {}).get("score"),
            "signal": ticker_scores.get("bandarm", {}).get("signal"),
            "broker_to_watch": ticker_scores.get("bandarm", {}).get("broker_to_watch", []),
            "price_analysis": ticker_scores.get("bandarm", {}).get("price_analysis", {}),
        },
        "fundamental_summary": {
            "score": ticker_scores.get("fundamental", {}).get("score"),
            "key_points": ticker_scores.get("fundamental", {}).get("key_points", []),
        },
        "macro_context": {
            "ihsg_trend": macro_data.get("ihsg_trend"),
            "is_volatile": macro_data.get("is_volatile"),
        },
        "composite_score": composites.get(ticker, {}).get("composite_score"),
    }


PRICE_PREDICTION_SYSTEM_PROMPT = """You are a stock market analyst specializing in Indonesian stocks (IDX).

**CRITICAL: Write all output in Indonesian language.**

Your task is to enhance a rule-based price prediction with:
1. Detailed reasoning (3-5 sentences minimum)
2. Key drivers (3-5 bullet points)
3. Risk factors (2-3 bullet points)
4. Confidence assessment (HIGH/MEDIUM/LOW)
5. Optional: adjust predicted % if rule-based seems off

Base your analysis on:
- Technical indicators (momentum, MACD, RSI, MA trends)
- Volume patterns
- Bandarmologi signals (institutional accumulation/distribution)
- Macro market conditions

Output valid JSON with this structure:
{
  "adjusted_predictions": {
    "day_1": {"pct_change": "+2.0"},
    "day_3": {"pct_change": "+5.0"},
    "day_5": {"pct_change": "+8.0"},
    "day_7": {"pct_change": "+11.0"}
  },
  "reasoning": "Detailed explanation in Indonesian (3-5 sentences minimum)...",
  "key_drivers": [
    "Driver 1",
    "Driver 2",
    "Driver 3"
  ],
  "risks": [
    "Risk 1",
    "Risk 2"
  ],
  "confidence": "HIGH"
}

Important: All text including reasoning, key drivers, and risks must be in Bahasa Indonesia. Only use English for ticker symbols, technical terms like RSI/MACD, and financial metrics (e.g., PER, ROE, DER)."""


def enhance_with_llm(
    ticker: str,
    base_prediction: dict,
    scores: dict,
    composites: dict,
    macro_data: dict,
) -> dict | None:
    """
    Enhance base prediction with LLM reasoning and optional adjustments.
    Returns enhanced prediction or None if LLM fails.
    """
    if not LLM_ENABLED:
        return None
    
    try:
        context = _build_llm_context(ticker, base_prediction, scores, composites, macro_data)
        
        user_prompt = f"""Ticker: {ticker}

Base Rule-Based Prediction:
- Current Price: {base_prediction['current_price']:,.0f}
- Day 1: {base_prediction['predictions']['day_1']['pct_change']}
- Day 3: {base_prediction['predictions']['day_3']['pct_change']}
- Day 5: {base_prediction['predictions']['day_5']['pct_change']}
- Day 7: {base_prediction['predictions']['day_7']['pct_change']}

Component Scores:
- Momentum: {base_prediction['component_scores']['momentum']}
- Volume: {base_prediction['component_scores']['volume']}
- Bandarmologi: {base_prediction['component_scores']['bandarm']}
- Macro: {base_prediction['component_scores']['macro']}

Context:
{context}

Provide enhanced analysis with detailed reasoning, key drivers, risks, and confidence level. Optionally adjust % if rule-based prediction seems off."""
        
        llm_result = invoke_json_im(
            LLM_MODEL_INVESTMENT_MANAGER,
            PRICE_PREDICTION_SYSTEM_PROMPT,
            user_prompt,
            fallback_model=LLM_MODEL_IM_FALLBACK,
        )
        
        return llm_result
    
    except Exception as e:
        logger.warning(f"[PREDICTOR] LLM enhancement failed for {ticker}: {e}")
        return None


def predict_movement(
    ticker: str,
    scores: dict,
    composites: dict,
    macro_data: dict,
) -> dict:
    """
    Main entry point: predict daily price movement for a ticker.
    Returns complete prediction with LLM enhancement if available.
    """
    # Get ML prediction if available in composites
    ml_pred = composites.get(ticker, {}).get("ml_prediction", {})

    # Calculate base prediction (now powered by multi-day ML)
    base_pred = calculate_base_prediction(
        ticker, scores, composites, macro_data, ml_pred
    )
    
    if not base_pred:
        return {
            "error": "Unable to calculate base prediction (missing price data)",
            "current_price": None,
            "predictions": {},
        }
    
    # Try LLM enhancement
    llm_enhanced = None
    if LLM_ENABLED:
        llm_enhanced = enhance_with_llm(ticker, base_pred, scores, composites, macro_data)
    
    # Merge predictions
    final_predictions = base_pred["predictions"].copy()
    
    if llm_enhanced and llm_enhanced.get("adjusted_predictions"):
        # Apply LLM adjustments
        for day_key, adjustment in llm_enhanced["adjusted_predictions"].items():
            if day_key in final_predictions and "pct_change" in adjustment:
                try:
                    adj_pct = float(adjustment["pct_change"].replace("%", "").replace("+", ""))
                    new_price = base_pred["current_price"] * (1 + adj_pct / 100)
                    final_predictions[day_key]["price"] = round(new_price, 0)
                    final_predictions[day_key]["pct_change"] = f"{adj_pct:+.1f}%"
                    # Adjust range
                    final_predictions[day_key]["price_range"] = [
                        round(new_price * 0.97, 0),
                        round(new_price * 1.03, 0),
                    ]
                except (ValueError, KeyError):
                    pass  # Keep base prediction
    
    # Build final output
    result = {
        "current_price": base_pred["current_price"],
        "predictions": final_predictions,
        "confidence": "MEDIUM",  # default
        "reasoning": "Prediction based on technical momentum, volume trend, bandarmologi accumulation strength, and macro sentiment.",
        "key_drivers": [],
        "risks": [],
    }
    
    # Add LLM enhancements if available
    if llm_enhanced:
        if llm_enhanced.get("reasoning"):
            result["reasoning"] = llm_enhanced["reasoning"]
        if llm_enhanced.get("key_drivers"):
            result["key_drivers"] = llm_enhanced["key_drivers"]
        if llm_enhanced.get("risks"):
            result["risks"] = llm_enhanced["risks"]
        if llm_enhanced.get("confidence") in ("HIGH", "MEDIUM", "LOW"):
            result["confidence"] = llm_enhanced["confidence"]
    
    return result


if __name__ == "__main__":
    # Simple test
    import json
    from agents.bandarmologi import analyze as analyze_bandarmologi
    from agents.technical import analyze as analyze_technical
    from agents.fundamental import analyze as analyze_fundamental
    from agents.macro import analyze as analyze_macro
    
    ticker = "ANTM"
    bandarm = analyze_bandarmologi(ticker)
    tech = analyze_technical(ticker)
    fund = analyze_fundamental(ticker)
    macro_data = analyze_macro()
    
    scores = {
        ticker: {
            "bandarm": bandarm,
            "technical": tech,
            "fundamental": fund,
        }
    }
    composites = {
        ticker: {
            "composite_score": 7.5,
            "weights_used": {"bandarm": 0.4, "technical": 0.25, "fundamental": 0.2, "macro": 0.15},
        }
    }
    
    prediction = predict_movement(ticker, scores, composites, macro_data)
    print(json.dumps(prediction, indent=2, ensure_ascii=False))