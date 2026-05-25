"""
Agent — Fundamental
Analisis fundamental saham: valuasi, profitabilitas, growth.
Rule-based scoring (tanpa LLM). Bisa ditambahkan LLM enhancement nanti.
"""
from data.fetcher_yfinance import get_stock_info


def analyze(ticker: str) -> dict:
    """
    Scoring fundamental berdasarkan:
    - PER (valuasi)
    - PBV (valuasi)
    - ROE (profitabilitas)
    - DER (leverage)
    - Revenue & earnings growth
    """
    info = get_stock_info(ticker)

    score = 5.0  # base score
    key_points = []
    risks = []
    data_used = []

    # === PER Analysis ===
    per = info.get("per")
    if per is not None:
        data_used.append(f"PER: {per:.1f}x")
        if per < 0:
            score -= 1.0
            risks.append("Laba negatif (PER < 0)")
        elif per < 10:
            score += 1.5
            key_points.append(f"PER {per:.1f}x — undervalued")
        elif per < 15:
            score += 1.0
            key_points.append(f"PER {per:.1f}x — valuasi wajar")
        elif per < 25:
            score += 0.5
            key_points.append(f"PER {per:.1f}x — premium tapi masih oke")
        else:
            score -= 0.5
            risks.append(f"PER {per:.1f}x — mahal")

    # === PBV Analysis ===
    pbv = info.get("pbv")
    if pbv is not None:
        data_used.append(f"PBV: {pbv:.2f}x")
        if pbv < 1.0:
            score += 1.0
            key_points.append(f"PBV {pbv:.2f}x — di bawah book value")
        elif pbv < 2.5:
            score += 0.5
            key_points.append(f"PBV {pbv:.2f}x — wajar")
        elif pbv > 5.0:
            score -= 0.5
            risks.append(f"PBV {pbv:.2f}x — valuasi tinggi")

    # === ROE Analysis ===
    roe = info.get("roe")
    if roe is not None:
        roe_pct = roe * 100
        data_used.append(f"ROE: {roe_pct:.1f}%")
        if roe_pct > 20:
            score += 1.5
            key_points.append(f"ROE {roe_pct:.1f}% — sangat baik")
        elif roe_pct > 15:
            score += 1.0
            key_points.append(f"ROE {roe_pct:.1f}% — di atas rata-rata")
        elif roe_pct > 10:
            score += 0.5
        elif roe_pct < 5:
            score -= 0.5
            risks.append(f"ROE {roe_pct:.1f}% — rendah")

    # === DER Analysis ===
    der = info.get("der")
    if der is not None:
        der_ratio = der / 100 if der > 10 else der  # normalize
        data_used.append(f"DER: {der_ratio:.2f}x")
        if der_ratio < 0.5:
            score += 0.5
            key_points.append(f"DER {der_ratio:.2f}x — leverage rendah")
        elif der_ratio > 2.0:
            score -= 1.0
            risks.append(f"DER {der_ratio:.2f}x — leverage tinggi")

    # === Growth Analysis ===
    rev_growth = info.get("revenue_growth")
    if rev_growth is not None:
        rev_pct = rev_growth * 100
        data_used.append(f"Revenue Growth: {rev_pct:.1f}%")
        if rev_pct > 15:
            score += 1.0
            key_points.append(f"Revenue growth {rev_pct:.1f}% — strong")
        elif rev_pct > 5:
            score += 0.5
        elif rev_pct < -5:
            score -= 0.5
            risks.append(f"Revenue turun {rev_pct:.1f}%")

    earn_growth = info.get("earnings_growth")
    if earn_growth is not None:
        earn_pct = earn_growth * 100
        data_used.append(f"Earnings Growth: {earn_pct:.1f}%")
        if earn_pct > 20:
            score += 1.0
            key_points.append(f"Earnings growth {earn_pct:.1f}% — akseleratif")
        elif earn_pct < -10:
            score -= 0.5
            risks.append(f"Earnings turun {earn_pct:.1f}%")

    # Clamp score 1-10
    score = max(1.0, min(10.0, score))

    # Determine signal
    if score >= 7.5:
        signal = "BUY"
    elif score >= 5.5:
        signal = "HOLD"
    else:
        signal = "SELL"

    # Confidence
    data_count = len(data_used)
    if data_count >= 5:
        confidence = "HIGH"
    elif data_count >= 3:
        confidence = "MEDIUM"
    else:
        confidence = "LOW"

    return {
        "ticker": ticker,
        "score": round(score, 1),
        "signal": signal,
        "key_points": key_points,
        "risks": risks,
        "data_used": data_used,
        "confidence": confidence,
    }
