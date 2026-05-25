"""
Agent — Macro
Analisis kondisi makro pasar: IHSG trend, USD/IDR, volatilitas, sektor.
"""
from data.fetcher_macro import get_macro_data, get_sector_outlook


def analyze() -> dict:
    """
    Scoring makro pasar Indonesia.
    Output digunakan sebagai konteks untuk semua saham (bukan per-saham).
    """
    macro = get_macro_data()
    sectors = get_sector_outlook()

    score = 5.0
    data_used = []

    # === IHSG Trend ===
    ihsg_price = macro.get("ihsg_price")
    ihsg_change = macro.get("ihsg_change_pct", 0)
    ihsg_vs_ma20 = macro.get("ihsg_vs_ma20")

    if ihsg_price:
        data_used.append(f"IHSG: {ihsg_price:.0f}")

    if ihsg_vs_ma20 is not None:
        data_used.append(f"IHSG vs MA20: {ihsg_vs_ma20:+.2f}%")
        if ihsg_vs_ma20 > 2:
            score += 1.5
            ihsg_trend = "BULLISH"
        elif ihsg_vs_ma20 > 0:
            score += 0.5
            ihsg_trend = "SLIGHTLY_BULLISH"
        elif ihsg_vs_ma20 > -2:
            score -= 0.5
            ihsg_trend = "SLIGHTLY_BEARISH"
        else:
            score -= 1.5
            ihsg_trend = "BEARISH"
    else:
        ihsg_trend = "UNKNOWN"

    # === USD/IDR ===
    usdidr = macro.get("usdidr")
    if usdidr:
        data_used.append(f"USD/IDR: {usdidr:.0f}")
        if usdidr < 15500:
            score += 1.0
            usdidr_trend = "STRONG_IDR"
        elif usdidr < 16000:
            score += 0.5
            usdidr_trend = "STABLE"
        elif usdidr < 16500:
            usdidr_trend = "WEAKENING"
        else:
            score -= 1.0
            usdidr_trend = "WEAK_IDR"
    else:
        usdidr_trend = "UNKNOWN"

    # === Volatility ===
    is_volatile = macro.get("is_volatile", False)
    data_used.append(f"Volatile: {is_volatile}")
    if is_volatile:
        score -= 1.0

    # === Market Risk ===
    if score >= 7:
        market_risk = "LOW"
    elif score >= 5:
        market_risk = "MEDIUM"
    else:
        market_risk = "HIGH"

    # Clamp
    score = max(1.0, min(10.0, score))

    return {
        "score": round(score, 1),
        "ihsg_trend": ihsg_trend,
        "ihsg_price": ihsg_price,
        "ihsg_change_pct": ihsg_change,
        "usdidr": usdidr,
        "usdidr_trend": usdidr_trend,
        "is_volatile": is_volatile,
        "sector_outlook": sectors,
        "market_risk": market_risk,
        "data_used": data_used,
    }
