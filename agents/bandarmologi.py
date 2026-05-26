"""
Agent — Bandarmologi (Bobot 40%)
Analisis akumulasi/distribusi bandar berdasarkan broker summary.
Core agent — penentu utama scoring di IDX market.
"""
from data.fetcher_stockbit import get_full_bandarm_data
from data.fetcher_stockbit import get_stock_info
from graph.scoring import assess_entry_vs_bandar
from config import BROKER_WATCH_SHORT, BROKER_WATCH_LONG


def _assess_accumulation(top_accumulators: list, window_days: int) -> tuple[float, str]:
    """
    Evaluasi kekuatan akumulasi dari top broker.
    Returns: (score_adjustment, signal)
    """
    if not top_accumulators:
        return 0.0, "NO_DATA"

    top_broker = top_accumulators[0][1]
    active_days = top_broker["active_days"]
    consistency = active_days / window_days

    # Consistency scoring
    if consistency >= 0.8:
        return 2.0, "STRONG_ACCUMULATION"
    elif consistency >= 0.6:
        return 1.0, "MODERATE_ACCUMULATION"
    elif consistency >= 0.4:
        return 0.0, "LIGHT_ACCUMULATION"
    else:
        return -1.0, "DISTRIBUTION"


def _format_broker_detail(broker_code: str, broker_data: dict,
                          window_days: int) -> dict:
    """Format detail broker untuk output."""
    consistency = broker_data["active_days"] / window_days
    if consistency >= 0.8:
        status = "⚡ KONSISTEN — PANTAU KETAT"
    elif consistency >= 0.6:
        status = "📈 AKTIF AKUMULASI"
    elif consistency >= 0.4:
        status = "📊 AKUMULASI RINGAN"
    else:
        status = "⚠️ TIDAK KONSISTEN"

    return {
        "broker": broker_code,
        "broker_name": broker_data["broker_name"],
        "total_buy_lot": broker_data["total_buy_lot"],
        "total_buy_value": broker_data["total_buy_value"],
        "avg_price": broker_data["avg_price"],
        "active_days": f"{broker_data['active_days']}/{window_days} hari",
        "status": status,
    }


def analyze(ticker: str) -> dict:
    """
    Analisis bandarmologi lengkap:
    - Window 7 hari (timing signal)
    - Window 30 hari (true cost bandar)
    - Entry assessment vs avg cost bandar
    """
    bandarm_data = get_full_bandarm_data(ticker)
    info = get_stock_info(ticker)
    current_price = info.get("current_price") or 0

    w7 = bandarm_data["w7"]
    w30 = bandarm_data["w30"]

    score = 5.0
    data_used = ["Stockbit broker summary 7H & 1M"]

    # === W7 Assessment ===
    adj_7d, signal_7d = _assess_accumulation(w7["top_accumulators"], BROKER_WATCH_SHORT)
    score += adj_7d

    # === W30 Assessment ===
    adj_30d, signal_30d = _assess_accumulation(w30["top_accumulators"], BROKER_WATCH_LONG)
    score += adj_30d

    # === Foreign Flow ===
    foreign_7d = w7["foreign_net"]
    foreign_30d = w30["foreign_net"]

    if foreign_7d > 0 and foreign_30d > 0:
        score += 1.0
        data_used.append(f"Foreign net buy 7H & 1M")
    elif foreign_7d > 0:
        score += 0.5
        data_used.append(f"Foreign net buy 7H")
    elif foreign_7d < 0 and foreign_30d < 0:
        score -= 1.0
        data_used.append(f"Foreign net sell 7H & 1M")

    # === Consistency Bonus ===
    if signal_7d == "STRONG_ACCUMULATION" and signal_30d in ("STRONG_ACCUMULATION", "MODERATE_ACCUMULATION"):
        score += 1.0  # Double confirmation

    # Clamp score
    score = max(1.0, min(10.0, score))

    # Overall signal
    if score >= 7.5:
        signal = "STRONG_ACCUMULATION"
    elif score >= 6.0:
        signal = "ACCUMULATION"
    elif score >= 4.0:
        signal = "NEUTRAL"
    else:
        signal = "DISTRIBUTION"

    # === Format top accumulators ===
    top_7d = [_format_broker_detail(code, data, BROKER_WATCH_SHORT)
              for code, data in w7["top_accumulators"][:5]]
    top_30d = [_format_broker_detail(code, data, BROKER_WATCH_LONG)
               for code, data in w30["top_accumulators"][:5]]

    # === Entry Analysis ===
    bandar_avg_7d = w7["top_accumulators"][0][1]["avg_price"] if w7["top_accumulators"] else 0
    bandar_avg_1m = w30["top_accumulators"][0][1]["avg_price"] if w30["top_accumulators"] else 0

    price_analysis = {}
    if current_price > 0 and bandar_avg_7d > 0 and bandar_avg_1m > 0:
        entry_assessment = assess_entry_vs_bandar(current_price, bandar_avg_7d, bandar_avg_1m)
        price_analysis = {
            "current_price": current_price,
            "bandar_avg_7d": bandar_avg_7d,
            "bandar_avg_1m": bandar_avg_1m,
            "distance_from_7d": f"{entry_assessment['distance_7d_pct']:+.2f}%",
            "distance_from_1m": f"{entry_assessment['distance_1m_pct']:+.2f}%",
            "ideal_entry_zone": entry_assessment["ideal_entry_zone"],
            "max_entry": entry_assessment["max_entry"],
            "entry_status": entry_assessment["status"],
            "entry_label": entry_assessment["label"],
        }

    # Confidence
    if signal_7d == signal_30d and foreign_7d * foreign_30d > 0:
        confidence = "HIGH"
    elif w7["top_accumulators"] and w30["top_accumulators"]:
        confidence = "MEDIUM"
    else:
        confidence = "LOW"

    # Broker to watch
    broker_to_watch = []
    for code, data in w7["top_accumulators"][:2]:
        broker_to_watch.append(f"{code} ({data['broker_name']})")

    return {
        "ticker": ticker,
        "score": round(score, 1),
        "signal": signal,
        "weight": "40%",
        "window_7d": {
            "period": w7["period"],
            "assessment": signal_7d.replace("_", " ").title(),
            "top_accumulators": top_7d,
            "foreign_net_7d": foreign_7d,
        },
        "window_1m": {
            "period": w30["period"],
            "assessment": signal_30d.replace("_", " ").title(),
            "top_accumulators": top_30d,
            "foreign_net_1m": foreign_30d,
        },
        "price_analysis": price_analysis,
        "broker_to_watch": broker_to_watch,
        "data_used": data_used,
        "confidence": confidence,
    }
