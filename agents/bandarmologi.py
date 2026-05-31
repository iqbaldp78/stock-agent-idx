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


def _format_distribution_detail(broker_code: str, broker_data: dict,
                                window_days: int) -> dict:
    consistency = broker_data["active_days"] / window_days if window_days else 0
    if consistency >= 0.8:
        status = "⚠️ DISTRIBUSI KONSISTEN"
    elif consistency >= 0.6:
        status = "⚠️ DISTRIBUSI AKTIF"
    elif consistency >= 0.4:
        status = "⚠️ DISTRIBUSI RINGAN"
    else:
        status = "ℹ️ DISTRIBUSI SESUAI" if broker_data["active_days"] > 0 else "ℹ️ DISTRIBUSI TIDAK KONSISTEN"

    return {
        "broker": broker_code,
        "broker_name": broker_data["broker_name"],
        "total_sell_lot": broker_data["total_sell_lot"],
        "total_sell_value": broker_data["total_sell_value"],
        "avg_price": broker_data["avg_price"],
        "active_days": f"{broker_data['active_days']}/{window_days} hari",
        "status": status,
    }


def _assess_distribution(window_data: dict) -> tuple[float, str, list[str]]:
    detector = window_data.get("bandar_detector", {})
    accdist = (detector.get("broker_accdist") or "").strip().upper()

    score_adj = 0.0
    signals = []

    if accdist == "BIG DIST":
        score_adj -= 2.0
        signals.append("Big Dist")
    elif accdist == "DIST":
        score_adj -= 1.0
        signals.append("Dist")
    elif accdist == "BIG ACCUM":
        score_adj += 1.0
        signals.append("Big Accum")
    elif accdist == "ACCUM":
        score_adj += 0.5
        signals.append("Accum")

    top3_sell = window_data.get("distribution_top3_value", 0)
    total_value = (window_data.get("bandar_detector", {}) or {}).get("value", 0)
    if total_value:
        ratio = top3_sell / total_value
        if ratio >= 0.30:
            score_adj -= 1.0
            signals.append("Top3 sell >= 30% value")
        elif ratio >= 0.15:
            score_adj -= 0.5
            signals.append("Top3 sell >= 15% value")

    label = "DISTRIBUTION" if score_adj < 0 else "ACCUMULATION" if score_adj > 0 else "NEUTRAL"
    return score_adj, label, signals


def _assess_confidence(
    signal_7d: str,
    signal_30d: str,
    foreign_7d: float,
    foreign_30d: float,
    w7: dict,
    w30: dict,
    price_analysis: dict,
) -> str:
    score = 0.0

    # Signal alignment
    if signal_7d == signal_30d:
        score += 1.0

    # Foreign flow alignment
    if foreign_7d * foreign_30d > 0:
        score += 1.0

    # Active days consistency (top broker)
    if w7.get("top_accumulators"):
        top_7d = w7["top_accumulators"][0][1]
        if top_7d.get("active_days", 0) / max(w7.get("window_days", 1), 1) >= 0.6:
            score += 0.5
    if w30.get("top_accumulators"):
        top_30d = w30["top_accumulators"][0][1]
        if top_30d.get("active_days", 0) / max(w30.get("window_days", 1), 1) >= 0.6:
            score += 0.5

    # Distribution penalty
    dist_signal_7d = w7.get("distribution_signal")
    dist_signal_30d = w30.get("distribution_signal")
    if dist_signal_7d == "DISTRIBUTION" or dist_signal_30d == "DISTRIBUTION":
        score -= 1.0

    # Top3 sell penalty
    top3_sell_7d = w7.get("distribution_top3_value", 0)
    top3_sell_30d = w30.get("distribution_top3_value", 0)
    if top3_sell_7d >= 1_000_000_000_000 or top3_sell_30d >= 1_000_000_000_000:
        score -= 1.0
    elif top3_sell_7d >= 500_000_000_000 or top3_sell_30d >= 500_000_000_000:
        score -= 0.5

    # Price distance to avg bandar
    distance_1m = price_analysis.get("distance_from_1m")
    if distance_1m:
        try:
            dist_1m_pct = float(str(distance_1m).replace("%", ""))
            if dist_1m_pct <= 2.0:
                score += 0.5
            elif dist_1m_pct >= 5.0:
                score -= 0.5
        except ValueError:
            pass

    if score >= 2.0:
        return "HIGH"
    if score >= 0.5:
        return "MEDIUM"
    return "LOW"


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

    # === Distribution Signal ===
    dist_adj_7d, dist_signal_7d, dist_notes_7d = _assess_distribution(w7)
    dist_adj_30d, dist_signal_30d, dist_notes_30d = _assess_distribution(w30)
    score += dist_adj_7d + dist_adj_30d
    if dist_notes_7d:
        data_used.append("Distribution 7H: " + ", ".join(dist_notes_7d))
    if dist_notes_30d:
        data_used.append("Distribution 1M: " + ", ".join(dist_notes_30d))

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

    top_dist_7d = [_format_distribution_detail(code, data, BROKER_WATCH_SHORT)
                   for code, data in w7.get("top_distributors", [])[:5]]
    top_dist_30d = [_format_distribution_detail(code, data, BROKER_WATCH_LONG)
                    for code, data in w30.get("top_distributors", [])[:5]]

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
    confidence = _assess_confidence(
        signal_7d,
        signal_30d,
        foreign_7d,
        foreign_30d,
        w7,
        w30,
        price_analysis,
    )

    # Broker to watch
    broker_to_watch = []
    for code, data in w7["top_accumulators"][:2]:
        broker_to_watch.append(f"{code} ({data['broker_name']})")

    # === Retail Broker Penalty (XL, XC, YP) ===
    RETAIL_BROKERS = {"XL", "XC", "YP"}
    retail_penalty = 0.0
    # Cek top 3 broker akumulasi 7 hari
    if w7["top_accumulators"]:
        top_brokers = w7["top_accumulators"][:5]
        values = [data["total_buy_value"] for code, data in top_brokers]
        lots = [data["total_buy_lot"] for code, data in top_brokers]
        avg_value = sum(values) / len(values) if values else 0
        avg_lot = sum(lots) / len(lots) if lots else 0
        for rank, (code, data) in enumerate(top_brokers[:3], 1):
            if code in RETAIL_BROKERS:
                # Anomali jika value/lot 2x lebih besar dari rata2 top 5
                if (data["total_buy_value"] >= 2 * avg_value or data["total_buy_lot"] >= 2 * avg_lot):
                    data_used.append(f"Anomali: Broker retail {code} akumulasi besar di rank {rank} (anomali, no penalty)")
                else:
                    retail_penalty -= 1.0
                    data_used.append(f"Penalty: Broker retail {code} akumulasi di rank {rank} (score -1.0)")
    score += retail_penalty

    return {
        "ticker": ticker,
        "score": round(score, 1),
        "signal": signal,
        "weight": "40%",
        "window_7d": {
            "period": w7["period"],
            "assessment": signal_7d.replace("_", " ").title(),
            "top_accumulators": top_7d,
            "top_distributors": top_dist_7d,
            "distribution_signal": dist_signal_7d,
            "foreign_net_7d": foreign_7d,
        },
        "window_1m": {
            "period": w30["period"],
            "assessment": signal_30d.replace("_", " ").title(),
            "top_accumulators": top_30d,
            "top_distributors": top_dist_30d,
            "distribution_signal": dist_signal_30d,
            "foreign_net_1m": foreign_30d,
        },
        "price_analysis": price_analysis,
        "broker_to_watch": broker_to_watch,
        "data_used": data_used,
        "confidence": confidence,
    }


if __name__ == "__main__":
    import sys, json
    ticker = sys.argv[1] if len(sys.argv) > 1 else "ANTM"
    result = analyze(ticker)
    print(json.dumps(result, indent=2, ensure_ascii=False))
