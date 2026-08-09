"""
Valuation utilities for Fundamental Agent.

Menghitung fair value saham dengan pendekatan blended (PE, PBV/ROE Justified Model, Growth/PEG Model)
yang dirancang secara realistis sesuai karakteristik saham di Bursa Efek Indonesia (IDX).
"""
from __future__ import annotations

FINANCIAL_TICKERS = {
    "BBCA", "BBRI", "BMRI", "BBNI", "BRIS", "ARTO", "BBTN", "BDMN", "BNGA", "BNLI",
    "PNBN", "MEGA", "BTPS", "BSDE", "NISP"
}

COMMODITY_TICKERS = {
    "ADRO", "PTBA", "ITMG", "HRUM", "BUMI", "MEDC", "PGAS", "AKRA", "CUAN", "DEWA",
    "ESSA", "AMMN", "MDKA", "BRMS", "ANTM", "INCO", "TPIA", "BRPT", "SMGR", "INTP",
    "MBMA", "TINS", "AADI"
}

CONSUMER_TICKERS = {
    "ICBP", "INDF", "MYOR", "UNVR", "CMRY", "AMRT", "MIDI", "CPIN", "JPFA", "KLBF",
    "MIKA", "HEAL", "SIDO", "ACES", "MAPI", "ERAA"
}


def _to_float(value, default: float | None = None) -> float | None:
    if value is None:
        return default
    try:
        return float(str(value).replace(",", "").replace("%", "").strip())
    except (TypeError, ValueError):
        return default


def _derive_eps(info: dict) -> tuple[float | None, str | None]:
    eps = _to_float(info.get("eps"))
    if eps and eps > 0:
        return eps, "info_eps"

    current_price = _to_float(info.get("current_price"))
    per = _to_float(info.get("per"))
    if current_price and per and per > 0:
        return current_price / per, "derived_from_current_price_per"

    eps_history = info.get("history", {}).get("eps", [])
    if eps_history:
        eps_sorted = sorted(eps_history, key=lambda x: str(x.get("year", "")), reverse=True)
        latest_val = _to_float(eps_sorted[0].get("value"))
        if latest_val and latest_val > 0:
            return latest_val, "latest_eps_history"
    return None, None


def _derive_bvps(info: dict) -> tuple[float | None, str | None]:
    bvps = _to_float(info.get("bvps"))
    if bvps and bvps > 0:
        return bvps, "info_bvps"

    current_price = _to_float(info.get("current_price"))
    pbv = _to_float(info.get("pbv"))
    if current_price and pbv and pbv > 0:
        return current_price / pbv, "derived_from_current_price_pbv"
    return None, None


def _target_pe(info: dict, ticker: str) -> tuple[float, list[str]]:
    notes = []
    roe_pct = _to_float(info.get("roe"), 0.0) or 0.0
    earnings_growth = _to_float(info.get("earnings_growth"), 0.0) or 0.0
    der = _to_float(info.get("der"), 0.0) or 0.0
    der_ratio = der / 100 if der > 10 else der

    ticker_upper = ticker.upper()
    if ticker_upper in FINANCIAL_TICKERS:
        target = 12.5
        notes.append("Target PE baseline sektor Keuangan/Bank: 12.5x")
    elif ticker_upper in COMMODITY_TICKERS:
        target = 8.5
        notes.append("Target PE baseline sektor Komoditas/Energi: 8.5x")
    elif ticker_upper in CONSUMER_TICKERS:
        target = 15.0
        notes.append("Target PE baseline sektor Consumer/Healthcare: 15.0x")
    else:
        target = 13.5
        notes.append("Target PE baseline universal: 13.5x")

    if roe_pct > 20:
        target += 2.5
    elif roe_pct > 15:
        target += 1.0
    elif roe_pct < 8:
        target -= 2.0

    if earnings_growth > 15:
        target += 1.5
    elif earnings_growth > 5:
        target += 0.5
    elif earnings_growth < 0:
        target -= 1.5

    if der_ratio > 2.0:
        target -= 1.5

    target = max(6.0, min(target, 22.0))
    return round(target, 2), notes


def _pe_based(info: dict, eps: float | None, target_pe: float) -> dict:
    if not eps or eps <= 0:
        return {"available": False, "reason": "EPS unavailable or non-positive"}
    return {
        "available": True,
        "eps": round(eps, 2),
        "target_pe": round(target_pe, 2),
        "fair_value": round(eps * target_pe, 0),
    }


def _pbv_roe_based(info: dict, bvps: float | None) -> dict:
    """
    Justified PBV / Gordon Growth Model:
    Fair PBV = (ROE - g) / (r - g)
    """
    roe_pct = _to_float(info.get("roe"), 0.0) or 0.0
    if not bvps or bvps <= 0 or roe_pct <= 0:
        return {"available": False, "reason": "BVPS or ROE unavailable"}

    ticker = str(info.get("ticker", "")).upper()

    # Required Return / Cost of Equity (r)
    if ticker in FINANCIAL_TICKERS or roe_pct > 18:
        required_return_pct = 13.5
    else:
        required_return_pct = 14.5

    der = _to_float(info.get("der"), 0.0) or 0.0
    der_ratio = der / 100 if der > 10 else der
    if der_ratio > 1.5:
        required_return_pct += 1.5

    payout_raw = _to_float(info.get("dividend_payout_ratio"), 50.0) or 50.0
    payout_ratio = payout_raw / 100.0 if payout_raw > 1.0 else payout_raw
    payout_ratio = max(0.20, min(payout_ratio, 0.80))
    retention_rate = 1.0 - payout_ratio

    # Sustainable growth g = ROE * retention
    g_pct = min(roe_pct * retention_rate, required_return_pct - 3.0)
    g_pct = max(0.0, g_pct)

    denom = required_return_pct - g_pct
    if denom <= 1.0:
        denom = 1.0

    fair_pbv = (roe_pct - g_pct) / denom
    if fair_pbv <= 0:
        fair_pbv = roe_pct / required_return_pct

    fair_pbv = max(0.6, min(fair_pbv, 4.0))

    return {
        "available": True,
        "bvps": round(bvps, 2),
        "roe_pct": round(roe_pct, 2),
        "sustainable_growth_pct": round(g_pct, 2),
        "required_return_pct": required_return_pct,
        "fair_pbv": round(fair_pbv, 2),
        "fair_value": round(bvps * fair_pbv, 0),
    }


def _growth_based(info: dict, eps: float | None, target_pe_base: float) -> dict:
    """
    PEG-adjusted Valuation Method:
    Target PE = Base PE + PEG_factor * Growth
    """
    if not eps or eps <= 0:
        return {"available": False, "reason": "EPS unavailable or non-positive"}

    growth_pct = _to_float(info.get("earnings_growth"), 0.0) or 0.0
    roe_pct = _to_float(info.get("roe"), 0.0) or 0.0

    g_clamped = max(-10.0, min(growth_pct, 15.0))

    if g_clamped > 0:
        target_pe = target_pe_base + (0.15 * g_clamped)
    else:
        target_pe = target_pe_base + (0.25 * g_clamped)

    if roe_pct > 18:
        target_pe += 1.0

    target_pe = max(6.0, min(target_pe, 20.0))

    return {
        "available": True,
        "eps": round(eps, 2),
        "growth_pct": round(growth_pct, 2),
        "target_pe": round(target_pe, 2),
        "fair_value": round(eps * target_pe, 0),
    }


def _valuation_label(upside_pct: float | None) -> str:
    if upside_pct is None:
        return "UNKNOWN"
    if upside_pct >= 25:
        return "DEEP_UNDERVALUED"
    if upside_pct >= 10:
        return "UNDERVALUED"
    if upside_pct <= -25:
        return "EXPENSIVE"
    if upside_pct <= -10:
        return "OVERVALUED"
    return "FAIRLY_VALUED"


def _confidence(methods: dict, notes: list[str]) -> str:
    available = sum(1 for m in methods.values() if m.get("available"))
    if available >= 3:
        return "HIGH"
    if available >= 2:
        return "MEDIUM"
    return "LOW"


def calculate_fair_value(info: dict) -> dict:
    """Calculate fair value range and valuation label from stock info."""
    ticker = str(info.get("ticker", "")).upper()
    current_price = _to_float(info.get("current_price"), 0.0) or 0.0
    notes: list[str] = []

    eps, eps_source = _derive_eps(info)
    if eps_source:
        notes.append(f"EPS source: {eps_source}")

    bvps, bvps_source = _derive_bvps(info)
    if bvps_source:
        notes.append(f"BVPS source: {bvps_source}")

    target_pe, pe_notes = _target_pe(info, ticker)
    notes.extend(pe_notes)

    methods = {
        "pe_based": _pe_based(info, eps, target_pe),
        "pbv_roe_based": _pbv_roe_based(info, bvps),
        "eps_growth_based": _growth_based(info, eps, target_pe),
    }

    if ticker in FINANCIAL_TICKERS:
        weights = {
            "pbv_roe_based": 0.45,
            "pe_based": 0.40,
            "eps_growth_based": 0.15,
        }
    else:
        weights = {
            "pe_based": 0.50,
            "pbv_roe_based": 0.30,
            "eps_growth_based": 0.20,
        }

    weighted_sum = 0.0
    used_weight = 0.0
    values = []
    for name, result in methods.items():
        if result.get("available"):
            fv = _to_float(result.get("fair_value"))
            if fv and fv > 0:
                weighted_sum += fv * weights[name]
                used_weight += weights[name]
                values.append(fv)

    if used_weight == 0 or not values:
        fair_base = None
        fair_low = None
        fair_high = None
        upside_pct = None
        mos_pct = None
    else:
        fair_base = weighted_sum / used_weight
        fair_low = min(values) * 0.93
        fair_high = max(values) * 1.07
        upside_pct = ((fair_base - current_price) / current_price * 100) if current_price else None
        mos_pct = ((fair_base - current_price) / fair_base * 100) if fair_base else None

    label = _valuation_label(upside_pct)

    return {
        "current_price": round(current_price, 0) if current_price else None,
        "method": "blended",
        "fair_value_low": round(fair_low, 0) if fair_low else None,
        "fair_value_base": round(fair_base, 0) if fair_base else None,
        "fair_value_high": round(fair_high, 0) if fair_high else None,
        "upside_pct": round(upside_pct, 2) if upside_pct is not None else None,
        "margin_of_safety_pct": round(mos_pct, 2) if mos_pct is not None else None,
        "valuation_label": label,
        "methods": methods,
        "notes": notes,
        "confidence": _confidence(methods, notes),
    }


def valuation_score_adjustment(label: str) -> float:
    return {
        "DEEP_UNDERVALUED": 1.5,
        "UNDERVALUED": 1.0,
        "FAIRLY_VALUED": 0.0,
        "OVERVALUED": -0.7,
        "EXPENSIVE": -1.2,
    }.get(label, 0.0)
