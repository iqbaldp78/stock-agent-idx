"""
Graph — Scoring
Composite score dengan bobot dinamis berdasarkan kategori saham.
"""
from config import WEIGHTS, BIG_CAP_TICKERS, SMALL_CAP_MAX_MC


def get_weights(ticker: str, market_cap: float, is_volatile: bool) -> dict:
    """Tentukan bobot berdasarkan kondisi saham dan pasar."""
    if is_volatile:
        return WEIGHTS["volatile"]
    elif ticker in BIG_CAP_TICKERS:
        return WEIGHTS["big_cap"]
    elif market_cap and market_cap < SMALL_CAP_MAX_MC:
        return WEIGHTS["small_cap"]
    return WEIGHTS["default"]


def detect_mode(ticker: str, market_cap: float, is_volatile: bool) -> str:
    """Deteksi mode bobot yang digunakan."""
    if is_volatile:
        return "volatile"
    elif ticker in BIG_CAP_TICKERS:
        return "big_cap"
    elif market_cap and market_cap < SMALL_CAP_MAX_MC:
        return "small_cap"
    return "default"


def calculate_composite(scores: dict, ticker: str,
                         market_cap: float, is_volatile: bool) -> dict:
    """
    Hitung composite score dari 5 agent (bandarm, technical, fundamental, macro, news).
    scores = {"bandarm": 8.5, "technical": 7.0, "fundamental": 8.0, "macro": 7.0, "news": 6.5}
    """
    w = get_weights(ticker, market_cap, is_volatile)
    composite = (
        scores["bandarm"] * w["bandarm"] +
        scores["technical"] * w["technical"] +
        scores["fundamental"] * w["fundamental"] +
        scores["macro"] * w["macro"] +
        scores.get("news", 5) * w.get("news", 0.12)
    )
    mode = detect_mode(ticker, market_cap, is_volatile)

    return {
        "ticker": ticker,
        "composite_score": round(composite, 2),
        "weights_used": w,
        "weight_mode": mode,
        "breakdown": {
            "bandarm": {"score": scores["bandarm"], "weight": w["bandarm"],
                        "contribution": round(scores["bandarm"] * w["bandarm"], 2)},
            "technical": {"score": scores["technical"], "weight": w["technical"],
                          "contribution": round(scores["technical"] * w["technical"], 2)},
            "fundamental": {"score": scores["fundamental"], "weight": w["fundamental"],
                            "contribution": round(scores["fundamental"] * w["fundamental"], 2)},
            "macro": {"score": scores["macro"], "weight": w["macro"],
                      "contribution": round(scores["macro"] * w["macro"], 2)},
            "news": {"score": scores.get("news", 5), "weight": w.get("news", 0.12),
                     "contribution": round(scores.get("news", 5) * w.get("news", 0.12), 2)},
        },
    }


def assess_entry_vs_bandar(current_price: float,
                           avg_7d: float,
                           avg_1m: float) -> dict:
    """
    Evaluasi posisi harga saat ini vs avg cost bandar.
    Menentukan apakah layak entry atau tunggu pullback.
    """
    dist_7d = (current_price - avg_7d) / avg_7d * 100
    dist_1m = (current_price - avg_1m) / avg_1m * 100

    # Status berdasarkan jarak dari avg 1 bulan (true cost)
    if dist_1m <= 0:
        status = "🟢 IDEAL"
        label = f"Harga {abs(dist_1m):.1f}% DI BAWAH true cost bandar — entry sangat menarik"
    elif dist_1m <= 2:
        status = "🟡 ACCEPTABLE"
        label = f"Harga {dist_1m:.1f}% di atas true cost bandar — layak entry"
    elif dist_1m <= 5:
        status = "🟠 CAUTION"
        label = f"Harga {dist_1m:.1f}% di atas true cost bandar — tunggu pullback"
    else:
        status = "🔴 AVOID"
        label = f"Harga {dist_1m:.1f}% di atas true cost bandar — terlalu jauh"

    ideal_entry = round(avg_1m * 1.005, 0)
    max_entry = round(avg_7d * 1.02, 0)

    return {
        "status": status,
        "label": label,
        "distance_7d_pct": round(dist_7d, 2),
        "distance_1m_pct": round(dist_1m, 2),
        "ideal_entry_zone": f"{round(avg_1m * 0.995, 0):.0f}–{ideal_entry:.0f}",
        "max_entry": f"{max_entry:.0f}",
    }
