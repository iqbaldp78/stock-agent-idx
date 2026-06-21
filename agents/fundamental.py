def calc_cagr(start, end, n_years):
    if start is None or end is None or n_years <= 0 or start <= 0 or end <= 0:
        return None
    try:
        val = (end / start) ** (1 / n_years) - 1
        if isinstance(val, complex):
            return None
        return val
    except Exception:
        return None
"""
Agent — Fundamental
Analisis fundamental saham: valuasi, profitabilitas, growth.
Rule-based scoring (tanpa LLM). Bisa ditambahkan LLM enhancement nanti.
"""
from data.fetcher_stockbit import get_stock_info
from agents.valuation import calculate_fair_value, valuation_score_adjustment


def analyze(ticker: str) -> dict:
    info = get_stock_info(ticker)
    history = info.get("history", {})
    key_points = []
    risks = []
    data_used = []
    score = 5.0  # base score

    # === CAGR Calculation ===
    cagr_results = {}
    cagr_dataused_lines = []
    for metric in ["revenue", "net_income", "eps"]:
        hist = history.get(metric, [])
        if len(hist) >= 2:
            hist_sorted = sorted(hist, key=lambda x: int(str(x['year'])))
            start_val = hist_sorted[0]['value']
            end_val = hist_sorted[-1]['value']
            n_years = int(str(hist_sorted[-1]['year'])) - int(str(hist_sorted[0]['year']))
            cagr = calc_cagr(start_val, end_val, n_years) if n_years > 0 else None
            if cagr is not None:
                cagr_results[metric] = cagr
                cagr_dataused_lines.append(f"CAGR {metric.replace('_',' ').title()}: {cagr*100:.2f}% ({hist_sorted[0]['year']}–{hist_sorted[-1]['year']})")
            else:
                cagr_dataused_lines.append(f"CAGR {metric.replace('_',' ').title()}: - ({hist_sorted[0]['year']}–{hist_sorted[-1]['year']})")
        else:
            cagr_dataused_lines.append(f"CAGR {metric.replace('_',' ').title()}: - (data kurang)")
    # === Scoring based on CAGR ===
    for metric, cagr in cagr_results.items():
        if cagr > 0.10:
            score += 1.0
            key_points.append(f"CAGR {metric.replace('_',' ').title()}: {cagr*100:.2f}% (tinggi)")
        elif cagr < 0:
            score -= 1.0
            risks.append(f"CAGR {metric.replace('_',' ').title()} negatif: {cagr*100:.2f}%")
        elif cagr > 0:
            key_points.append(f"CAGR {metric.replace('_',' ').title()}: {cagr*100:.2f}%")

    # Helper: get last 5 years' values for a metric
    def get_hist(metric):
        vals = history.get(metric, [])
        # Sort by year descending (assume year is int or str convertible)
        vals = sorted(vals, key=lambda x: str(x['year']), reverse=True)
        return vals[:5] if vals else []

    # Helper for trend (naik/turun)
    def get_trend(vals):
        if len(vals) < 2:
            return None
        diffs = [vals[i]['value'] - vals[i+1]['value'] for i in range(len(vals)-1)]
        if all(d > 0 for d in diffs):
            return 'up'
        elif all(d < 0 for d in diffs):
            return 'down'
        return 'mixed'

    # Net Income
    hist_net_income = get_hist("net_income")
    cagr_net_income = None
    if hist_net_income:
        vals = [x['value'] for x in hist_net_income[:3]]
        avg_net_income = sum(vals) / len(vals)
        data_used.append(f"Rata-rata Net Income 3 tahun: {avg_net_income:,.0f}")
        trend = get_trend(hist_net_income[:3])
        # Ambil CAGR net income (full period)
        hist_full = history.get("net_income", [])
        if len(hist_full) >= 2:
            hist_sorted = sorted(hist_full, key=lambda x: int(str(x['year'])))
            start_val = hist_sorted[0]['value']
            end_val = hist_sorted[-1]['value']
            n_years = int(str(hist_sorted[-1]['year'])) - int(str(hist_sorted[0]['year']))
            cagr_net_income = calc_cagr(start_val, end_val, n_years) if n_years > 0 else None
        if trend == 'up':
            if cagr_net_income is not None:
                key_points.append(f"Net income konsisten naik 3 tahun terakhir dengan CAGR {cagr_net_income*100:.2f}%")
            else:
                key_points.append("Net income konsisten naik 3 tahun terakhir")
        elif trend == 'down':
            risks.append("Net income konsisten turun 3 tahun terakhir")

    # EPS
    hist_eps = get_hist("eps")
    cagr_eps = None
    if hist_eps:
        vals = [x['value'] for x in hist_eps[:3]]
        avg_eps = sum(vals) / len(vals)
        data_used.append(f"Rata-rata EPS 3 tahun: {avg_eps:,.2f}")
        trend = get_trend(hist_eps[:3])
        # Ambil CAGR EPS (full period)
        hist_full = history.get("eps", [])
        if len(hist_full) >= 2:
            hist_sorted = sorted(hist_full, key=lambda x: int(str(x['year'])))
            start_val = hist_sorted[0]['value']
            end_val = hist_sorted[-1]['value']
            n_years = int(str(hist_sorted[-1]['year'])) - int(str(hist_sorted[0]['year']))
            cagr_eps = calc_cagr(start_val, end_val, n_years) if n_years > 0 else None
        if trend == 'up':
            if cagr_eps is not None:
                key_points.append(f"EPS konsisten naik 3 tahun terakhir dengan CAGR {cagr_eps*100:.2f}%")
            else:
                key_points.append("EPS konsisten naik 3 tahun terakhir")
        elif trend == 'down':
            risks.append("EPS konsisten turun 3 tahun terakhir")

    # Revenue
    hist_revenue = get_hist("revenue")
    cagr_revenue = None
    if hist_revenue:
        vals = [x['value'] for x in hist_revenue[:3]]
        avg_revenue = sum(vals) / len(vals)
        data_used.append(f"Rata-rata Revenue 3 tahun: {avg_revenue:,.0f}")
        trend = get_trend(hist_revenue[:3])
        # Ambil CAGR revenue (full period)
        hist_full = history.get("revenue", [])
        if len(hist_full) >= 2:
            hist_sorted = sorted(hist_full, key=lambda x: int(str(x['year'])))
            start_val = hist_sorted[0]['value']
            end_val = hist_sorted[-1]['value']
            n_years = int(str(hist_sorted[-1]['year'])) - int(str(hist_sorted[0]['year']))
            cagr_revenue = calc_cagr(start_val, end_val, n_years) if n_years > 0 else None
        if trend == 'up':
            if cagr_revenue is not None:
                key_points.append(f"Revenue konsisten naik 3 tahun terakhir dengan CAGR {cagr_revenue*100:.2f}%")
            else:
                key_points.append("Revenue konsisten naik 3 tahun terakhir")
        elif trend == 'down':
            risks.append("Revenue konsisten turun 3 tahun terakhir")
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
        # If value > 1, treat as percent already (e.g. 21.84 = 21.84%)
        if roe > 1:
            roe_pct = roe
        else:
            roe_pct = roe * 100
        data_used.append(f"ROE: {roe_pct:.2f}%")
        if roe_pct > 20:
            score += 1.5
            key_points.append(f"ROE {roe_pct:.2f}% — sangat baik")
        elif roe_pct > 15:
            score += 1.0
            key_points.append(f"ROE {roe_pct:.2f}% — di atas rata-rata")
        elif roe_pct > 10:
            score += 0.5
        elif roe_pct < 5:
            score -= 0.5
            risks.append(f"ROE {roe_pct:.2f}% — rendah")

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
        rev_pct = rev_growth
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
        earn_pct = earn_growth
        data_used.append(f"Earnings Growth: {earn_pct:.1f}%")
        if earn_pct > 20:
            score += 1.0
            key_points.append(f"Earnings growth {earn_pct:.1f}% — akseleratif")
        elif earn_pct < -10:
            score -= 0.5
            risks.append(f"Earnings turun {earn_pct:.1f}%")

    # === Dividend Analysis ===
    dividend_yield = info.get("dividend_yield")
    dividend_payout = info.get("dividend_payout_ratio")
    dividend_per_share = info.get("dividend_per_share")
    history = info.get("history", {})
    # Helper: get last 5 years' values for a metric
    def get_hist(metric):
        vals = history.get(metric, [])
        # Sort by year descending (assume year is int or str convertible)
        vals = sorted(vals, key=lambda x: str(x['year']), reverse=True)
        return vals[:5] if vals else []

    # === Net Income, EPS, Revenue Historical Comparison ===
    # Helper for trend (naik/turun)
    def get_trend(vals):
        if len(vals) < 2:
            return None
        diffs = [vals[i]['value'] - vals[i+1]['value'] for i in range(len(vals)-1)]
        if all(d > 0 for d in diffs):
            return 'up'
        elif all(d < 0 for d in diffs):
            return 'down'
        return 'mixed'

    # Net Income
    hist_net_income = get_hist("net_income")
    if hist_net_income:
        vals = [x['value'] for x in hist_net_income[:3]]
        avg_net_income = sum(vals) / len(vals)
        data_used.append(f"Rata-rata Net Income 3 tahun: {avg_net_income:,.0f}")
        trend = get_trend(hist_net_income[:3])
        if trend == 'up':
            key_points.append("Net income konsisten naik 3 tahun terakhir")
        elif trend == 'down':
            risks.append("Net income konsisten turun 3 tahun terakhir")

    # EPS
    hist_eps = get_hist("eps")
    if hist_eps:
        vals = [x['value'] for x in hist_eps[:3]]
        avg_eps = sum(vals) / len(vals)
        data_used.append(f"Rata-rata EPS 3 tahun: {avg_eps:,.2f}")
        trend = get_trend(hist_eps[:3])
        if trend == 'up':
            key_points.append("EPS konsisten naik 3 tahun terakhir")
        elif trend == 'down':
            risks.append("EPS konsisten turun 3 tahun terakhir")

    # Revenue
    hist_revenue = get_hist("revenue")
    if hist_revenue:
        vals = [x['value'] for x in hist_revenue[:3]]
        avg_revenue = sum(vals) / len(vals)
        data_used.append(f"Rata-rata Revenue 3 tahun: {avg_revenue:,.0f}")
        trend = get_trend(hist_revenue[:3])
        if trend == 'up':
            key_points.append("Revenue konsisten naik 3 tahun terakhir")
        elif trend == 'down':
            risks.append("Revenue konsisten turun 3 tahun terakhir")

    # === Historical Comparison for all metrics ===
    # PER
    hist_per = get_hist("per")
    if hist_per:
        avg_per = sum(x['value'] for x in hist_per) / len(hist_per)
        data_used.append(f"Rata-rata PER 5 tahun: {avg_per:.2f}x")
        if per is not None and per < avg_per - 1:
            key_points.append(f"PER saat ini di bawah rata-rata 5 tahun ({avg_per:.2f}x)")
        elif per is not None and per > avg_per + 1:
            risks.append(f"PER saat ini di atas rata-rata 5 tahun ({avg_per:.2f}x)")
    # PBV
    hist_pbv = get_hist("pbv")
    if hist_pbv:
        avg_pbv = sum(x['value'] for x in hist_pbv) / len(hist_pbv)
        data_used.append(f"Rata-rata PBV 5 tahun: {avg_pbv:.2f}x")
        if pbv is not None and pbv < avg_pbv - 0.5:
            key_points.append(f"PBV saat ini di bawah rata-rata 5 tahun ({avg_pbv:.2f}x)")
        elif pbv is not None and pbv > avg_pbv + 0.5:
            risks.append(f"PBV saat ini di atas rata-rata 5 tahun ({avg_pbv:.2f}x)")
    # ROE
    hist_roe = get_hist("roe")
    if hist_roe:
        avg_roe = sum(x['value'] for x in hist_roe) / len(hist_roe)
        data_used.append(f"Rata-rata ROE 5 tahun: {avg_roe:.2f}%")
        if roe is not None and roe*100 > avg_roe + 2:
            key_points.append(f"ROE saat ini di atas rata-rata 5 tahun ({avg_roe:.2f}%)")
        elif roe is not None and roe*100 < avg_roe - 2:
            risks.append(f"ROE saat ini di bawah rata-rata 5 tahun ({avg_roe:.2f}%)")
    # DER
    hist_der = get_hist("der")
    if hist_der:
        avg_der = sum(x['value'] for x in hist_der) / len(hist_der)
        data_used.append(f"Rata-rata DER 5 tahun: {avg_der:.2f}x")
        if der is not None and der < avg_der - 0.2:
            key_points.append(f"DER saat ini di bawah rata-rata 5 tahun ({avg_der:.2f}x)")
        elif der is not None and der > avg_der + 0.2:
            risks.append(f"DER saat ini di atas rata-rata 5 tahun ({avg_der:.2f}x)")
    # Revenue Growth
    hist_rev = get_hist("revenue_growth")
    if hist_rev:
        avg_rev = sum(x['value'] for x in hist_rev) / len(hist_rev)
        data_used.append(f"Rata-rata Revenue Growth 5 tahun: {avg_rev:.2f}%")
        if rev_growth is not None and rev_growth*100 > avg_rev + 2:
            key_points.append(f"Revenue growth saat ini di atas rata-rata 5 tahun ({avg_rev:.2f}%)")
        elif rev_growth is not None and rev_growth*100 < avg_rev - 2:
            risks.append(f"Revenue growth saat ini di bawah rata-rata 5 tahun ({avg_rev:.2f}%)")
    # Earnings Growth
    hist_earn = get_hist("earnings_growth")
    if hist_earn:
        avg_earn = sum(x['value'] for x in hist_earn) / len(hist_earn)
        data_used.append(f"Rata-rata Earnings Growth 5 tahun: {avg_earn:.2f}%")
        if earn_growth is not None and earn_growth*100 > avg_earn + 2:
            key_points.append(f"Earnings growth saat ini di atas rata-rata 5 tahun ({avg_earn:.2f}%)")
        elif earn_growth is not None and earn_growth*100 < avg_earn - 2:
            risks.append(f"Earnings growth saat ini di bawah rata-rata 5 tahun ({avg_earn:.2f}%)")
    # Dividend Yield
    hist_div = get_hist("dividend_yield")
    if hist_div:
        avg_div = sum(x['value'] for x in hist_div) / len(hist_div)
        data_used.append(f"Rata-rata Dividend Yield 5 tahun: {avg_div:.2f}%")
        if dividend_yield is not None:
            if dividend_yield > 1:
                yield_pct = dividend_yield
            else:
                yield_pct = dividend_yield * 100
            if yield_pct > avg_div + 1:
                key_points.append(f"Dividend yield saat ini di atas rata-rata 5 tahun ({avg_div:.2f}%)")
            elif yield_pct < avg_div - 1:
                risks.append(f"Dividend yield saat ini di bawah rata-rata 5 tahun ({avg_div:.2f}%)")
    # (Dividend yield analysis now handled above with history/hist_div logic)
    if dividend_payout is not None:
        data_used.append(f"Dividend Payout Ratio: {dividend_payout*100:.1f}%")
        if dividend_payout > 0.8:
            risks.append(f"Payout ratio sangat tinggi: {dividend_payout*100:.1f}%")
        elif dividend_payout > 0.6:
            risks.append(f"Payout ratio tinggi: {dividend_payout*100:.1f}%")
    if dividend_per_share is not None:
        data_used.append(f"Dividend per Share: {dividend_per_share}")

    # === Fair Value / Valuation Analysis ===
    fair_value = calculate_fair_value(info)
    valuation_label = fair_value.get("valuation_label", "UNKNOWN")
    valuation_adj = valuation_score_adjustment(valuation_label)
    score += valuation_adj

    fv_base = fair_value.get("fair_value_base")
    upside = fair_value.get("upside_pct")
    if fv_base:
        data_used.append(f"Fair Value: {fv_base:,.0f} ({valuation_label})")
        if upside is not None:
            data_used.append(f"Upside to fair value: {upside:+.2f}%")
    if valuation_label in ("DEEP_UNDERVALUED", "UNDERVALUED"):
        key_points.append(f"Valuasi menarik: {valuation_label} (upside {upside:+.1f}%)")
    elif valuation_label in ("OVERVALUED", "EXPENSIVE"):
        risks.append(f"Valuasi mahal: {valuation_label} (upside {upside:+.1f}%)")

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

    # Tambahkan baris CAGR di akhir data_used
    data_used.extend(cagr_dataused_lines)
    return {
        "ticker": ticker,
        "score": round(score, 1),
        "signal": signal,
        "key_points": key_points,
        "risks": risks,
        "data_used": data_used,
        "fair_value": fair_value,
        "confidence": confidence,
    }


if __name__ == "__main__":
    import argparse, json
    parser = argparse.ArgumentParser()
    parser.add_argument("--ticker", required=True)
    args = parser.parse_args()
    result = analyze(args.ticker)
    print(json.dumps(result, indent=2, ensure_ascii=False))
