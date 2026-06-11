"""
Agent — Investment Manager
Mensintesis semua input → TOP 3 PICK dengan entry presisi berdasarkan avg cost bandar.
Phase 4: LLM via 9Router + rule-based numeric merge + fallback.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime

from agents.debate.personas import IM_SYSTEM_PROMPT
from agents.llm_client import health_check, invoke_json_im
from agents.price_predictor import predict_movement
from config import (
    LLM_ENABLED,
    LLM_MODEL_IM_FALLBACK,
    LLM_MODEL_INVESTMENT_MANAGER,
)

logger = logging.getLogger(__name__)


def synthesize(state: dict) -> dict:
    """
    Investment Manager: Pilih TOP 3 dari finalists.
    Tries LLM synthesis first, falls back to rule-based.
    """
    finalists = state.get("finalists", [])
    if not finalists:
        return {"top_picks": [], "final_report": _empty_report()}

    if LLM_ENABLED and health_check():
        try:
            result = synthesize_with_llm(state)
            if result and result.get("top_picks"):
                return result
        except Exception as e:
            logger.warning("[INVESTMENT_MANAGER] LLM failed, rule-based fallback: %s", e)

    return synthesize_rule_based(state)


def synthesize_with_llm(state: dict) -> dict | None:
    """Single LLM call for TOP 3 narrative; numbers from rule-based picks."""
    finalists = state.get("finalists", [])
    scores = state.get("scores", {})
    composites = state.get("composites", {})
    macro_data = state.get("macro_data", {})
    debate_log = state.get("debate_log", [])

    finalist_tickers = [f["ticker"] for f in finalists[:7]]
    debate_summary = [
        e for e in debate_log
        if e.get("ticker") in finalist_tickers or e.get("ticker") == "MARKET"
    ][-80:]

    context = {
        "finalists": finalists[:7],
        "scores": {t: scores.get(t) for t in finalist_tickers if t in scores},
        "composites": {t: composites.get(t) for t in finalist_tickers if t in composites},
        "macro_data": macro_data,
        "debate_log": debate_summary,
    }
    user = (
        "Pilih TOP 3 dari finalis berikut. Rank 1 = conviction tertinggi.\n\n"
        f"{json.dumps(context, ensure_ascii=False, default=str)}"
    )

    raw = invoke_json_im(
        LLM_MODEL_INVESTMENT_MANAGER,
        IM_SYSTEM_PROMPT,
        user,
        fallback_model=LLM_MODEL_IM_FALLBACK,
    )
    if not raw:
        return None

    return _merge_llm_decision(state, raw)


def _merge_llm_decision(state: dict, llm_raw: dict) -> dict:
    """Merge LLM narratives with rule-based numeric fields."""
    finalists = state.get("finalists", [])
    scores = state.get("scores", {})
    composites = state.get("composites", {})
    macro_data = state.get("macro_data", {})
    ml_predictions = state.get("ml_predictions", {})

    ranked = llm_raw.get("ranked_tickers") or []
    if not isinstance(ranked, list):
        ranked = []

    finalist_by_ticker = {f["ticker"]: f for f in finalists}
    ordered_tickers: list[str] = []
    llm_meta: dict[str, dict] = {}

    for item in ranked[:3]:
        if not isinstance(item, dict):
            continue
        t = item.get("ticker")
        if t and t in finalist_by_ticker and t not in ordered_tickers:
            ordered_tickers.append(t)
            llm_meta[t] = item

    if len(ordered_tickers) < 3:
        for f in finalists:
            t = f["ticker"]
            if t not in ordered_tickers:
                ordered_tickers.append(t)
            if len(ordered_tickers) >= 3:
                break

    top_picks = []
    for i, ticker in enumerate(ordered_tickers[:3]):
        finalist = finalist_by_ticker.get(ticker, {"ticker": ticker})
        pick = _build_pick_rule_based(
            rank=i + 1,
            ticker=ticker,
            finalist=finalist,
            scores=scores,
            composites=composites,
            macro_data=macro_data,
            ml_predictions=ml_predictions,
        )
        meta = llm_meta.get(ticker, {})
        if meta.get("thesis"):
            pick["thesis"] = str(meta["thesis"])
        if meta.get("entry_reasoning"):
            pick["entry_reasoning"] = str(meta["entry_reasoning"])
        if meta.get("conviction") in ("HIGH", "MEDIUM", "LOW"):
            pick["conviction"] = meta["conviction"]
            pick["position_size"] = _position_size(meta["conviction"])
        if meta.get("time_horizon"):
            pick["time_horizon"] = str(meta["time_horizon"])
        top_picks.append(pick)

    watchlist = llm_raw.get("watchlist")
    if not isinstance(watchlist, list):
        watchlist = [f["ticker"] for f in finalists[3:5]]
    watchlist = [str(x) for x in watchlist[:5]]

    avoid = llm_raw.get("avoid")
    if not isinstance(avoid, list):
        avoid = _build_avoid_list(state)
    avoid = [str(x) for x in avoid[:5]]

    market_summary = llm_raw.get("market_condition_summary")
    ihsg_trend = macro_data.get("ihsg_trend", "UNKNOWN")
    ihsg_price = macro_data.get("ihsg_price", "N/A")
    if market_summary:
        market_condition = str(market_summary)
    else:
        foreign = "foreign net buy" if macro_data.get("score", 5) >= 6 else "foreign cautious"
        market_condition = f"{ihsg_trend} — IHSG {ihsg_price}, {foreign}"

    final_report = {
        "generated_at": datetime.now().isoformat(),
        "market_condition": market_condition,
        "top_picks": top_picks,
        "watchlist": watchlist,
        "avoid": avoid,
        "llm_synthesis": llm_raw,
        "total_analyzed": len(composites),
        "total_finalists": len(finalists),
        "synthesis_mode": "llm",
    }

    logger.info("[INVESTMENT_MANAGER] LLM TOP 3: %s", [p["ticker"] for p in top_picks])
    return {"top_picks": top_picks, "final_report": final_report}


def synthesize_rule_based(state: dict) -> dict:
    """Rule-based TOP 3 (original logic)."""
    finalists = state.get("finalists", [])
    scores = state.get("scores", {})
    composites = state.get("composites", {})
    macro_data = state.get("macro_data", {})
    ml_predictions = state.get("ml_predictions", {})

    if not finalists:
        return {"top_picks": [], "final_report": _empty_report()}

    logger.info(f"[INVESTMENT_MANAGER] Rule-based: {len(finalists)} finalists")

    top_picks = []
    for i, finalist in enumerate(finalists[:3]):
        ticker = finalist["ticker"]
        pick = _build_pick_rule_based(
            rank=i + 1,
            ticker=ticker,
            finalist=finalist,
            scores=scores,
            composites=composites,
            macro_data=macro_data,
            ml_predictions=ml_predictions,
        )
        top_picks.append(pick)
        logger.info(
            f"  #{i+1} {ticker}: conviction={pick['conviction']}, "
            f"entry={pick['entry_zone']}, score={pick['final_score']}"
        )

    watchlist = [f["ticker"] for f in finalists[3:5]]
    avoid = _build_avoid_list(state)

    ihsg_trend = macro_data.get("ihsg_trend", "UNKNOWN")
    ihsg_price = macro_data.get("ihsg_price", "N/A")
    foreign = "foreign net buy" if macro_data.get("score", 5) >= 6 else "foreign cautious"
    market_condition = f"{ihsg_trend} — IHSG {ihsg_price}, {foreign}"

    final_report = {
        "generated_at": datetime.now().isoformat(),
        "market_condition": market_condition,
        "top_picks": top_picks,
        "watchlist": watchlist,
        "avoid": avoid,
        "total_analyzed": len(composites),
        "total_finalists": len(finalists),
        "synthesis_mode": "rule_based",
    }

    return {"top_picks": top_picks, "final_report": final_report}


def _build_pick_rule_based(
    *,
    rank: int,
    ticker: str,
    finalist: dict,
    scores: dict,
    composites: dict,
    macro_data: dict,
    ml_predictions: dict = None,
) -> dict:
    ticker_scores = scores.get(ticker, {})
    bandarm = ticker_scores.get("bandarm", {})
    tech = ticker_scores.get("technical", {})
    fund = ticker_scores.get("fundamental", {})
    composite = composites.get(ticker, {})

    window_1m = bandarm.get("window_1m", {})
    price_analysis = bandarm.get("price_analysis", {})
    avg_cost_7d = price_analysis.get("bandar_avg_7d")
    avg_cost_1m = price_analysis.get("bandar_avg_1m")
    current_price = price_analysis.get("current_price")
    entry_low = price_analysis.get("ideal_entry_zone", "N/A")
    max_entry = price_analysis.get("max_entry", "N/A")

    # Extract TP1, TP2, TP3 with R/R metrics
    tp1 = tech.get("tp1")
    tp2 = tech.get("tp2")
    tp3 = tech.get("tp3")
    tp1_size = tech.get("tp1_size", 0.30)
    tp2_size = tech.get("tp2_size", 0.40)
    tp3_size = tech.get("tp3_size", 0.30)
    risk_reward_tp1 = tech.get("risk_reward_tp1", "N/A")
    risk_reward_tp2 = tech.get("risk_reward_tp2", "N/A")
    risk_reward_tp3 = tech.get("risk_reward_tp3", "N/A")

    # Parse TP values as float
    try:
        tp1 = float(tp1) if tp1 else None
    except (ValueError, TypeError):
        tp1 = None
    try:
        tp2 = float(tp2) if tp2 else None
    except (ValueError, TypeError):
        tp2 = None
    try:
        tp3 = float(tp3) if tp3 else None
    except (ValueError, TypeError):
        tp3 = None

    stop_loss = tech.get("stop_loss")
    try:
        stop_loss = float(stop_loss) if stop_loss else None
    except (ValueError, TypeError):
        stop_loss = None

    distance = ""
    if avg_cost_1m and current_price:
        dist_pct = (current_price - avg_cost_1m) / avg_cost_1m * 100
        distance = f"+{dist_pct:.1f}%" if dist_pct > 0 else f"{dist_pct:.1f}%"

    thesis = _build_thesis(ticker, bandarm, tech, fund, price_analysis)
    entry_reasoning = _build_entry_reasoning(
        ticker, avg_cost_7d, avg_cost_1m, current_price, stop_loss
    )
    final_score = finalist.get("final_score", 0)
    if final_score >= 8.0:
        conviction = "HIGH"
    elif final_score >= 6.5:
        conviction = "MEDIUM"
    else:
        conviction = "LOW"

    agent_scores = {
        "bandarm": {
            "score": bandarm.get("score", 0),
            "weight": f"{composite.get('weights_used', {}).get('bandarm', 0.4) * 100:.0f}%",
            "contribution": round(
                bandarm.get("score", 0) * composite.get("weights_used", {}).get("bandarm", 0.4), 2
            ),
        },
        "technical": {
            "score": tech.get("score", 0),
            "weight": f"{composite.get('weights_used', {}).get('technical', 0.25) * 100:.0f}%",
            "contribution": round(
                tech.get("score", 0) * composite.get("weights_used", {}).get("technical", 0.25), 2
            ),
        },
        "fundamental": {
            "score": fund.get("score", 0),
            "weight": f"{composite.get('weights_used', {}).get('fundamental', 0.2) * 100:.0f}%",
            "contribution": round(
                fund.get("score", 0) * composite.get("weights_used", {}).get("fundamental", 0.2), 2
            ),
        },
        "macro": {
            "score": macro_data.get("score", 0),
            "weight": f"{composite.get('weights_used', {}).get('macro', 0.15) * 100:.0f}%",
            "contribution": round(
                macro_data.get("score", 0) * composite.get("weights_used", {}).get("macro", 0.15), 2
            ),
        },
        "composite": composite.get("composite_score", 0),
    }
    broker_to_watch = bandarm.get("broker_to_watch", [])
    broker_utama = broker_to_watch[0] if broker_to_watch else "N/A"

    # Generate price prediction for TOP 3
    price_prediction = predict_movement(
        ticker=ticker,
        scores=scores,
        composites=composites,
        macro_data=macro_data,
    )

    # Extract ML prediction if available
    ml_prediction = None
    if ml_predictions:
        ml_prediction = ml_predictions.get(ticker)

    pred_return = float(ml_prediction.get("pred_return", 0.0)) if ml_prediction else 0.0
    decision_label = _decision_label(pred_return, tech, bandarm)
    target_1 = tp1
    target_2 = _calc_target_2(tp1)
    risk_reward = _calc_risk_reward(current_price, target_1, stop_loss, decision_label)

    return {
        "rank": rank,
        "ticker": ticker,
        "thesis": thesis,
        "time_horizon": "Positional (4-6 minggu)",
        "price_prediction": price_prediction,
        "ml_prediction": ml_prediction,
        "pred_return": pred_return,
        "decision_label": decision_label,
        "bandar_context": {
            "broker_utama": broker_utama,
            "avg_cost_7d": avg_cost_7d,
            "avg_cost_1m": avg_cost_1m,
            "active_days_1m": window_1m.get("active_days", "N/A"),
            "distance_current": distance,
        },
        "entry_zone": entry_low,
        "max_entry": max_entry,
        "tp1": tp1,
        "tp2": tp2,
        "tp3": tp3,
        "target_1": target_1,
        "target_2": target_2,
        "tp1_size": tp1_size,
        "tp2_size": tp2_size,
        "tp3_size": tp3_size,
        "risk_reward_tp1": risk_reward_tp1,
        "risk_reward_tp2": risk_reward_tp2,
        "risk_reward_tp3": risk_reward_tp3,
        "stop_loss": stop_loss,
        "risk_reward": risk_reward,
        "position_strategy": f"Exit {tp1_size*100:.0f}% at TP1, {tp2_size*100:.0f}% at TP2, {tp3_size*100:.0f}% at TP3",
        "position_size": _position_size(conviction),
        "conviction": conviction,
        "entry_reasoning": entry_reasoning,
        "agent_scores": agent_scores,
        "bandarm_signal": bandarm.get("signal", "N/A"),
        "broker_to_watch": broker_to_watch,
        "weight_mode": finalist.get("weight_mode", "default"),
        "composite_score": composite.get("composite_score", 0),
        "final_score": final_score,
    }


def _decision_label(pred_return_pct: float, tech: dict, bandarm: dict) -> str:
    """
    Map predicted return to decision label with special bandar-vs-technical conflict handling.
    pred_return_pct is expected in percentage points (e.g., 0.8 for +0.8%).
    """
    tech_bearish = str(tech.get("trend", "")).lower() == "bearish"
    bandar_accum_strong = (
        bandarm.get("score", 0) >= 7.0
        and "ACCUMULATION" in str(bandarm.get("signal", "")).upper()
    )

    if tech_bearish and bandar_accum_strong and pred_return_pct >= 0.3:
        return "SPEC BUY"

    if pred_return_pct > 1.0:
        return "STRONG BUY"
    if pred_return_pct >= 0.3:
        return "BUY"
    if pred_return_pct < -0.5:
        return "AVOID"
    return "HOLD"


def _build_thesis(ticker: str, bandarm: dict, tech: dict, fund: dict,
                  price_analysis: dict) -> str:
    parts = []
    signal = bandarm.get("signal", "")
    broker_list = bandarm.get("broker_to_watch", [])
    broker_main = broker_list[0] if broker_list else "institutional"
    avg_1m = price_analysis.get("bandar_avg_1m")
    current = price_analysis.get("current_price")

    if "ACCUMULATION" in signal.upper():
        parts.append(f"{broker_main} akumulasi aktif")
        if avg_1m:
            parts.append(f"true cost bandar di {avg_1m:,.0f}")
        if current and avg_1m:
            dist = (current - avg_1m) / avg_1m * 100
            if dist <= 3:
                parts.append("harga masih dekat cost bandar")
            else:
                parts.append(f"harga {dist:.1f}% di atas cost bandar")

    setup = tech.get("setup", "")
    if setup:
        parts.append(setup)

    key_pts = fund.get("key_points", [])
    if key_pts:
        parts.append(key_pts[0])

    return f"{ticker} — " + ". ".join(parts) + "." if parts else f"{ticker} — layak dipertimbangkan"


def _build_entry_reasoning(ticker: str, avg_7d, avg_1m, current, stop_loss) -> str:
    parts = []
    if avg_1m:
        parts.append(f"Entry ideal dekat true cost bandar ({avg_1m:,.0f})")
        parts.append("Bandar tidak akan biarkan harga turun jauh dari cost mereka")
    if stop_loss and avg_1m:
        sl_dist = abs(stop_loss - avg_1m) / avg_1m * 100 if avg_1m else 0
        parts.append(f"SL di {stop_loss:,.0f} = {sl_dist:.1f}% di bawah avg bandar, risiko kecil")
    return ". ".join(parts) if parts else "Entry berdasarkan analisis multi-agent"


def _calc_risk_reward(current, target, stop_loss, decision_label: str | None = None) -> str:
    if not all([current, target, stop_loss]):
        return "N/A"
    try:
        label = str(decision_label or "").upper()

        # Direction-aware R/R: BUY-family uses long math, AVOID uses short math.
        if label in ("STRONG BUY", "BUY", "SPEC BUY"):
            risk = current - stop_loss
            reward = target - current
        elif label == "AVOID":
            risk = stop_loss - current
            reward = current - target
        else:
            risk = abs(current - stop_loss)
            reward = abs(target - current)

        if risk <= 0 or reward <= 0:
            return "N/A"
        rr = reward / risk
        return f"1:{rr:.1f}"
    except (TypeError, ZeroDivisionError):
        return "N/A"


def _calc_target_2(target_1) -> float | None:
    if target_1 is None:
        return None
    try:
        return round(float(target_1) * 1.05)
    except (TypeError, ValueError):
        return None


def _position_size(conviction: str) -> str:
    sizes = {
        "HIGH": "30% portofolio",
        "MEDIUM": "20% portofolio",
        "LOW": "10% portofolio",
    }
    return sizes.get(conviction, "15% portofolio")


def _build_avoid_list(state: dict) -> list:
    scores = state.get("scores", {})
    avoid = []
    for ticker, ticker_scores in scores.items():
        bandarm = ticker_scores.get("bandarm", {})
        if bandarm.get("score", 5) <= 3:
            signal = bandarm.get("signal", "distribusi")
            avoid.append(f"{ticker} — {signal}, hindari dulu")
    return avoid[:3]


def _empty_report() -> dict:
    return {
        "generated_at": datetime.now().isoformat(),
        "market_condition": "UNKNOWN",
        "top_picks": [],
        "watchlist": [],
        "avoid": [],
        "total_analyzed": 0,
        "total_finalists": 0,
        "synthesis_mode": "none",
    }


if __name__ == "__main__":
    import json
    from agents.bandarmologi import analyze as analyze_bandarmologi
    from agents.fundamental import analyze as analyze_fundamental
    from agents.macro import analyze as analyze_macro
    from agents.technical import analyze as analyze_technical

    ticker = "ANTM"
    bandarm = analyze_bandarmologi(ticker)
    tech = analyze_technical(ticker)
    fund = analyze_fundamental(ticker)
    macro_data = analyze_macro()
    composite_score = (
        bandarm.get("score", 0) * 0.4
        + tech.get("score", 0) * 0.25
        + fund.get("score", 0) * 0.2
        + macro_data.get("score", 0) * 0.15
    )
    scores = {ticker: {"bandarm": bandarm, "technical": tech, "fundamental": fund}}
    composites = {
        ticker: {
            "weights_used": {"bandarm": 0.4, "technical": 0.25, "fundamental": 0.2, "macro": 0.15},
            "composite_score": composite_score,
        }
    }
    finalists = [{"ticker": ticker, "final_score": composite_score, "weight_mode": "default"}]
    state = {
        "finalists": finalists,
        "scores": scores,
        "composites": composites,
        "macro_data": macro_data,
        "debate_log": [],
    }
    result = synthesize(state)
    print(json.dumps(result, indent=2, ensure_ascii=False))
