"""
Agent — Investment Manager
Mensintesis semua input → TOP 3 PICK dengan entry presisi berdasarkan avg cost bandar.
Phase 4: Rule-based synthesis (dapat ditingkatkan dengan Claude Sonnet).
"""
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def synthesize(state: dict) -> dict:
    """
    Investment Manager: Pilih TOP 3 dari finalists.
    Entry zone = dekat avg cost bandar (true cost 1M).
    
    Input: state dari workflow (finalists, scores, composites, macro_data)
    Output: top_picks + final_report
    """
    finalists = state.get("finalists", [])
    scores = state.get("scores", {})
    composites = state.get("composites", {})
    macro_data = state.get("macro_data", {})

    if not finalists:
        return {"top_picks": [], "final_report": _empty_report()}

    logger.info(f"[INVESTMENT_MANAGER] Analyzing {len(finalists)} finalists")

    top_picks = []
    for i, finalist in enumerate(finalists[:3]):
        ticker = finalist["ticker"]
        ticker_scores = scores.get(ticker, {})
        bandarm = ticker_scores.get("bandarm", {})
        tech = ticker_scores.get("technical", {})
        fund = ticker_scores.get("fundamental", {})
        composite = composites.get(ticker, {})

        # Bandar context
        window_7d = bandarm.get("window_7d", {})
        window_1m = bandarm.get("window_1m", {})
        price_analysis = bandarm.get("price_analysis", {})

        # Extract avg costs
        avg_cost_7d = price_analysis.get("bandar_avg_7d")
        avg_cost_1m = price_analysis.get("bandar_avg_1m")
        current_price = price_analysis.get("current_price")

        # Entry zone based on bandar avg cost
        entry_low = price_analysis.get("ideal_entry_zone", "N/A")
        max_entry = price_analysis.get("max_entry", "N/A")

        # Target & SL from technical
        target_1 = tech.get("target")
        stop_loss = tech.get("stop_loss")

        # Calculate risk/reward
        risk_reward = _calc_risk_reward(current_price, target_1, stop_loss)

        # Distance from bandar cost
        distance = ""
        if avg_cost_1m and current_price:
            dist_pct = (current_price - avg_cost_1m) / avg_cost_1m * 100
            distance = f"+{dist_pct:.1f}%" if dist_pct > 0 else f"{dist_pct:.1f}%"

        # Build thesis
        thesis = _build_thesis(ticker, bandarm, tech, fund, price_analysis)

        # Entry reasoning
        entry_reasoning = _build_entry_reasoning(
            ticker, avg_cost_7d, avg_cost_1m, current_price, stop_loss
        )

        # Conviction
        final_score = finalist.get("final_score", 0)
        if final_score >= 8.0:
            conviction = "HIGH"
        elif final_score >= 6.5:
            conviction = "MEDIUM"
        else:
            conviction = "LOW"

        # Agent score breakdown
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

        # Broker to watch
        broker_to_watch = bandarm.get("broker_to_watch", [])
        broker_utama = broker_to_watch[0] if broker_to_watch else "N/A"

        pick = {
            "rank": i + 1,
            "ticker": ticker,
            "thesis": thesis,
            "time_horizon": "Positional (4-6 minggu)",
            "bandar_context": {
                "broker_utama": broker_utama,
                "avg_cost_7d": avg_cost_7d,
                "avg_cost_1m": avg_cost_1m,
                "active_days_1m": window_1m.get("active_days", "N/A"),
                "distance_current": distance,
            },
            "entry_zone": entry_low,
            "max_entry": max_entry,
            "target_1": target_1,
            "target_2": _calc_target_2(target_1),
            "stop_loss": stop_loss,
            "risk_reward": risk_reward,
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
        top_picks.append(pick)

        logger.info(
            f"  #{i+1} {ticker}: conviction={conviction}, "
            f"entry={entry_low}, score={final_score}"
        )

    # Watchlist (finalists 4-5)
    watchlist = [f["ticker"] for f in finalists[3:5]]

    # Avoid list (from debate — tickers with strong sell signals)
    avoid = _build_avoid_list(state)

    # Market condition
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
    }

    return {
        "top_picks": top_picks,
        "final_report": final_report,
    }


def _build_thesis(ticker: str, bandarm: dict, tech: dict, fund: dict,
                  price_analysis: dict) -> str:
    """Generate investment thesis."""
    parts = []

    # Bandar context
    signal = bandarm.get("signal", "")
    broker_list = bandarm.get("broker_to_watch", [])
    if broker_list:
        broker_main = broker_list[0]
    else:
        broker_main = "institutional"

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

    # Technical
    setup = tech.get("setup", "")
    if setup:
        parts.append(setup)

    # Fundamental
    key_pts = fund.get("key_points", [])
    if key_pts:
        parts.append(key_pts[0])

    return f"{ticker} — " + ". ".join(parts) + "." if parts else f"{ticker} — layak dipertimbangkan"


def _build_entry_reasoning(ticker: str, avg_7d, avg_1m, current, stop_loss) -> str:
    """Explain why entry zone is set at that level."""
    parts = []

    if avg_1m:
        parts.append(
            f"Entry ideal dekat true cost bandar ({avg_1m:,.0f})"
        )
        parts.append(
            "Bandar tidak akan biarkan harga turun jauh dari cost mereka"
        )

    if stop_loss and avg_1m:
        sl_dist = abs(stop_loss - avg_1m) / avg_1m * 100 if avg_1m else 0
        parts.append(
            f"SL di {stop_loss:,.0f} = {sl_dist:.1f}% di bawah avg bandar, risiko kecil"
        )

    return ". ".join(parts) if parts else "Entry berdasarkan analisis multi-agent"


def _calc_risk_reward(current, target, stop_loss) -> str:
    """Calculate risk/reward ratio."""
    if not all([current, target, stop_loss]):
        return "N/A"
    try:
        risk = abs(current - stop_loss)
        reward = abs(target - current)
        if risk == 0:
            return "N/A"
        rr = reward / risk
        return f"1:{rr:.1f}"
    except (TypeError, ZeroDivisionError):
        return "N/A"


def _calc_target_2(target_1) -> float | None:
    """Target 2 = target 1 + 5%."""
    if target_1 is None:
        return None
    try:
        return round(float(target_1) * 1.05)
    except (TypeError, ValueError):
        return None


def _position_size(conviction: str) -> str:
    """Position size based on conviction."""
    sizes = {
        "HIGH": "30% portofolio",
        "MEDIUM": "20% portofolio",
        "LOW": "10% portofolio",
    }
    return sizes.get(conviction, "15% portofolio")


def _build_avoid_list(state: dict) -> list:
    """Identify tickers to avoid based on debate signals."""
    scores = state.get("scores", {})
    composites = state.get("composites", {})
    avoid = []

    for ticker, ticker_scores in scores.items():
        bandarm = ticker_scores.get("bandarm", {})
        if bandarm.get("score", 5) <= 3:
            signal = bandarm.get("signal", "distribusi")
            avoid.append(f"{ticker} — {signal}, hindari dulu")

    return avoid[:3]  # Max 3 avoid


def _empty_report() -> dict:
    """Empty report when no finalists."""
    return {
        "generated_at": datetime.now().isoformat(),
        "market_condition": "UNKNOWN",
        "top_picks": [],
        "watchlist": [],
        "avoid": [],
        "total_analyzed": 0,
        "total_finalists": 0,
    }
