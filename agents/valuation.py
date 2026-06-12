"""
Valuation utilities for Fundamental Agent.

Menghitung fair value saham dengan pendekatan sederhana dan robust:
- PE based: EPS * target PE
- PBV/ROE based: BVPS * fair PBV
- EPS growth based: EPS * growth-adjusted PE

Catatan: ini bukan rekomendasi investasi, melainkan estimasi kuantitatif untuk
membantu scoring fundamental dan margin of safety.
"""
from __future__ import annotations

from statistics import median


def _to_float(value, default: float | None = None) -> float | None:
    if value is None:
        return default
    try:
        return float(str(value).replace(",", "").replace("%", "").strip())
    except (TypeError, ValueError):
        return default


def _normalize_pct(value, default: float = 0.0) -> float:
    """Return percentage units, e.g. 18.5 means 18.5%."""
    val = _to_float(value, default)
    if val is None:
        return default
    return val * 100 if abs(val) <= 1 else val


def _history_values(history: dict, key: str) -> list[float]:
    values = []
    for item in history.get(key, []) or []:
        val = _to_float(item.get("value"))
        if val is not None:
            values.append(val)
    return values


def _derive_eps(info: dict) -> tuple[float | None, str | None]:
    current_price = _to_float(info.get("current_price"))
    per = _to_float(info.get("per"))
    if current_price and per and per > 0:
        return current_price / per, "derived_from_current_price_per"

    eps_history = _history_values(info.get("history", {}), "eps")
    if eps_history:
        return eps_history[-1], "latest_eps_history"
    return None, None


def _derive_bvps(info: dict) -> tuple[float | None, str | None]:
    current_price = _to_float(info.get("current_price"))
    pbv = _to_float(info.get("pbv"))
    if current_price and pbv and pbv > 0:
        return current_price / pbv, "derived_from_current_price_pbv"
    return None, None


def _target_pe(info: dict, history: dict) -> tuple[float, list[str]]:
    notes = []
    roe_pct = _normalize_pct(info.get("roe"), 0.0)
    earnings_growth = _normalize_pct(info.get("earnings_growth"), 0.0)
    der = _to_float(info.get("der"), 0.0) or 0.0
    der_ratio = der / 100 if der > 10 else der

    hist_pe = [v for v in _history_values(history, "per") if 0 < v < 80]
    if hist_pe:
        target = median(hist_pe)
        notes.append(f"Target PE dari median historis: {target:.1f}x")
    else:
        target = 15.0
        notes.append("Target PE fallback base: 15.0x")

    if roe_pct > 20:
        target += 4
    elif roe_pct > 15:
        target += 2
    elif roe_pct < 8:
        target -= 3

    if earnings_growth > 20:
        target += 4
    elif earnings_growth > 10:
        target += 2
    elif earnings_growth < 0:
        target -= 4

    if der_ratio > 2:
        target -= 2

    target = max(5.0, min(target, 35.0))
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
    roe_pct = _normalize_pct(info.get("roe"), 0.0)
    if not bvps or bvps <= 0 or roe_pct <= 0:
        return {"available": False, "reason": "BVPS or ROE unavailable"}

    required_return_pct = 12.0
    fair_pbv = roe_pct / required_return_pct
    fair_pbv = max(0.5, min(fair_pbv, 5.0))
    return {
        "available": True,
        "bvps": round(bvps, 2),
        "roe_pct": round(roe_pct, 2),
        "required_return_pct": required_return_pct,
        "fair_pbv": round(fair_pbv, 2),
        "fair_value": round(bvps * fair_pbv, 0),
    }


def _growth_based(info: dict, eps: float | None) -> dict:
    if not eps or eps <= 0:
        return {"available": False, "reason": "EPS unavailable or non-positive"}

    growth_pct = _normalize_pct(info.get("earnings_growth"), 0.0)
    roe_pct = _normalize_pct(info.get("roe"), 0.0)
    target_pe = growth_pct
    if roe_pct > 20:
        target_pe += 5
    elif roe_pct > 15:
        target_pe += 3
    target_pe = max(7.0, min(target_pe, 30.0))

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
    history = info.get("history", {}) or {}
    current_price = _to_float(info.get("current_price"), 0.0) or 0.0
    notes: list[str] = []

    eps, eps_source = _derive_eps(info)
    if eps_source:
        notes.append(f"EPS source: {eps_source}")

    bvps, bvps_source = _derive_bvps(info)
    if bvps_source:
        notes.append(f"BVPS source: {bvps_source}")

    target_pe, pe_notes = _target_pe(info, history)
    notes.extend(pe_notes)

    methods = {
        "pe_based": _pe_based(info, eps, target_pe),
        "pbv_roe_based": _pbv_roe_based(info, bvps),
        "eps_growth_based": _growth_based(info, eps),
    }

    weights = {
        "pe_based": 0.45,
        "pbv_roe_based": 0.35,
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
        fair_low = min(values) * 0.95
        fair_high = max(values) * 1.05
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
