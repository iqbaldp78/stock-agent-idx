"""
Agent — Bandarmologi (Bobot 40%)
Analisis akumulasi/distribusi bandar berdasarkan broker summary.
Core agent — penentu utama scoring di IDX market.
"""
from typing import Optional
from data.fetcher_stockbit import get_current_price_stockbit
from data.fetcher_stockbit import get_full_bandarm_data
from data.fetcher_stockbit import get_stock_info
from graph.scoring import assess_entry_vs_bandar
from config import BROKER_WATCH_SHORT, BROKER_WATCH_LONG


def _assess_accumulation(top_accumulators: list, window_days: int) -> dict:
    """
    Evaluasi kekuatan akumulasi dari top broker.
    Returns: dict with status and metrics
    """
    if not top_accumulators:
        return {"status": "NO_DATA", "consistency": 0.0, "top_broker": None}

    top_broker = top_accumulators[0][1]
    active_days = top_broker["active_days"]
    consistency = active_days / window_days

    # Raw status assignment
    if consistency >= 0.8:
        status = "STRONG_ACCUMULATION"
    elif consistency >= 0.6:
        status = "MODERATE_ACCUMULATION"
    elif consistency >= 0.4:
        status = "LIGHT_ACCUMULATION"
    else:
        status = "DISTRIBUTION"
        
    return {
        "status": status,
        "consistency": consistency,
        "top_broker": top_accumulators[0][0],
        "top_broker_data": top_broker
    }

def _evaluate_bandar_phase(w7_eval: dict, w30_eval: dict, dist_7d_status: str, dist_30d_status: str) -> tuple[float, str, str]:
    """
    Matriks Fase Bandar.
    Returns: (base_score, phase_name, narrative)
    """
    w7_status = w7_eval["status"]
    w30_status = w30_eval["status"]
    
    # 1. THE ACCUMULATION (Fase Akumulasi Masif)
    if w30_status in ["STRONG_ACCUMULATION", "MODERATE_ACCUMULATION"] and w7_status in ["STRONG_ACCUMULATION", "MODERATE_ACCUMULATION"]:
        if dist_7d_status == "DISTRIBUTION":
            return 6.5, "ACCUMULATION_WITH_MINOR_DISTRIBUTION", "Akumulasi konsisten 1M tapi mulai ada distribusi kecil minggu ini"
        return 8.5, "STRONG_ACCUMULATION", "Fase Akumulasi Masif: Bandar konsisten akumulasi dari 1 bulan lalu hingga minggu ini"
        
    # 2. THE BREAKOUT / ESTAFET (Fase Pergantian Bandar / Re-Akumulasi)
    elif w30_status in ["DISTRIBUTION", "LIGHT_ACCUMULATION", "NO_DATA"] and w7_status in ["STRONG_ACCUMULATION", "MODERATE_ACCUMULATION"]:
        return 7.5, "RE_ACCUMULATION", "Fase Re-Akumulasi (Estafet): Bandar lama mungkin taking profit, tapi ada bandar baru yang nampung agresif minggu ini"
        
    # 3. THE MARK-UP TRAP (Fase Distribusi Terselubung)
    elif w30_status in ["STRONG_ACCUMULATION", "MODERATE_ACCUMULATION"] and w7_status in ["DISTRIBUTION", "LIGHT_ACCUMULATION", "NO_DATA"]:
        return 4.5, "MARK_UP_TRAP", "Fase Mark-up Trap: Bandar punya banyak barang dari bulan lalu, tapi ekornya mulai buang barang (distribusi) minggu ini"
        
    # 4. THE MARK-DOWN (Fase Buang Barang)
    else: # w30 dist/light, w7 dist/light
        return 2.5, "DISTRIBUTION", "Fase Mark-Down: Murni distribusi dari bulan lalu hingga hari ini (Rawan guyur)"

def _detect_broker_estafet(w30_distributors: list, w7_accumulators: list) -> tuple[float, str]:
    """
    Cek apakah barang dari Top Seller 1M ditampung oleh Top Buyer 7D.
    """
    if not w30_distributors or not w7_accumulators:
        return 0.0, ""
        
    top_sellers = [code for code, data in w30_distributors[:3]]
    top_buyers = [code for code, data in w7_accumulators[:3]]
    
    # Broker institusi & asing kuat (Asing + Institusi Lokal/Dana Pensiun/Big Player)
    STRONG_BROKERS = {"BK", "ZP", "AK", "CS", "RX", "KZ", "YU", "CG", "DX", "BB", "IF", "OD", "TP", "NI", "CC", "GW", "AI", "AG", "DB", "DP", "LG", "LS", "HD", "MS", "GR", "ML", "UB"}
    # Broker Ritel Murni (FOMO Army)
    RETAIL_BROKERS = {"YP", "XC", "XL", "PD", "SQ"}
    
    # Estafet dari ritel ke asing/big broker
    for seller in top_sellers:
        if seller in RETAIL_BROKERS:
            for buyer in top_buyers:
                if buyer in STRONG_BROKERS:
                    return 1.5, f"Estafet dari ritel ({seller}) ke institusi kuat ({buyer})"
                    
    return 0.0, ""
    
def _assess_concentration(w7_accumulators: list, w7_distributors: list, w7_data: dict) -> tuple[float, str, str, str]:
    """
    Hitung Rasio Konsentrasi Beli vs Jual (1 vs Many).
    Returns: (score_adjustment, type (driver/risk/neutral), narrative, internal_log)
    """
    if not w7_accumulators or not w7_distributors:
        return 0.0, "neutral", "", ""
        
    # Dapatkan total volume/value seluruh market dari w7_data
    # Asumsi: total_buy_value_all == total_sell_value_all (match)
    # Karena data yang kita punya adalah top broker, kita jumlahkan top 10 sebagai proksi,
    # ATAU jika tersedia total real market, gunakan itu. 
    # Di sini kita gunakan total dari semua broker di array accumulators & distributors
    total_buy_val = sum(data["total_buy_value"] for code, data in w7_accumulators)
    total_sell_val = sum(data["total_sell_value"] for code, data in w7_distributors)
    
    if total_buy_val == 0 or total_sell_val == 0:
        return 0.0, "neutral", "", ""
        
    # Hitung konsentrasi Top 3
    top3_buyers = w7_accumulators[:3]
    top3_sellers = w7_distributors[:3]
    
    top3_buy_val = sum(data["total_buy_value"] for code, data in top3_buyers)
    top3_sell_val = sum(data["total_sell_value"] for code, data in top3_sellers)
    
    buy_concentration = (top3_buy_val / total_buy_val) * 100
    sell_concentration = (top3_sell_val / total_sell_val) * 100
    
    # Ambil nama kode broker
    buyer_codes = ", ".join([code for code, data in top3_buyers])
    seller_codes = ", ".join([code for code, data in top3_sellers])
    
    # Skenario 1: Akumulasi Terkonsentrasi (Piramida)
    if buy_concentration > 50.0 and sell_concentration < 45.0:
        nar = f"Akumulasi Terkonsentrasi: Top 3 broker ({buyer_codes}) menyapu {buy_concentration:.0f}% suplai pasar dari tangan ritel tersebar."
        return 1.0, "driver", nar, f"Konsentrasi Beli ({buy_concentration:.0f}%) > Jual ({sell_concentration:.0f}%) -> Bonus +1.0"
        
    # Skenario 2: Distribusi Terkonsentrasi (Ritel Exit Liquidity)
    elif sell_concentration > 50.0 and buy_concentration < 45.0:
        nar = f"Distribusi Terkonsentrasi: {sell_concentration:.0f}% buangan bandar besar ({seller_codes}) sedang ditadah oleh broker eceran."
        return -1.0, "risk", nar, f"Konsentrasi Jual ({sell_concentration:.0f}%) > Beli ({buy_concentration:.0f}%) -> Penalti -1.0"
        
    # Skenario 3: Big vs Big / Retail vs Retail
    else:
        return 0.0, "neutral", "", f"Konsentrasi Beli ({buy_concentration:.0f}%) vs Jual ({sell_concentration:.0f}%) -> Imbang (Netral)"

def _assess_aggressiveness(w7_accumulators: list, current_price: float, is_accumulating: bool) -> tuple[float, str, str, str]:
    """
    Hitung Agresivitas Bandar (HAKA/HAKI) berdasarkan jarak Avg Cost Top 3 Buyer dengan Current Price.
    Hanya dihitung jika saham sedang dalam fase akumulasi secara keseluruhan.
    Returns: (score_adjustment, type (driver/risk/neutral), narrative, internal_log)
    """
    if not is_accumulating or not w7_accumulators or current_price <= 0:
        return 0.0, "neutral", "", ""
        
    # Hitung volume-weighted average price (VWAP) khusus Top 3 Buyer
    top3 = w7_accumulators[:3]
    total_val = sum(data["total_buy_value"] for code, data in top3)
    total_lot = sum(data["total_buy_lot"] for code, data in top3)
    
    if total_lot == 0:
        return 0.0, "neutral", "", ""
        
    # Harga rata-rata per lembar saham = Total Value / (Total Lot * 100)
    avg_cost_top3 = total_val / (total_lot * 100)
    
    # Hitung selisih: positif artinya Bandar nyangkut/beli di atas harga closing (HAKA kuat)
    diff_pct = ((avg_cost_top3 - current_price) / current_price) * 100
    
    # Skenario 1: Hyper-Aggressive (Sangat HAKA)
    if diff_pct > 3.0:
        nar = f"Agresivitas Ekstrem (HAKA): Bandar rela akumulasi dengan rata-rata modal ({avg_cost_top3:.0f}) yang {diff_pct:.1f}% LEBIH TINGGI dari harga penutupan saat ini. Sinyal kuat antisipasi pergerakan naik."
        return 1.0, "driver", nar, f"HAKA Ekstrem: Cost {avg_cost_top3:.0f} > Price {current_price} (+{diff_pct:.1f}%) -> Bonus +1.0"
        
    # Skenario 2: Aggressive (HAKA Wajar)
    elif 0.0 <= diff_pct <= 3.0:
        nar = f"Agresivitas Wajar: Bandar proaktif menyerap barang di harga pasar saat ini (Avg: {avg_cost_top3:.0f})."
        return 0.5, "driver", nar, f"HAKA Wajar: Cost {avg_cost_top3:.0f} >= Price {current_price} (+{diff_pct:.1f}%) -> Bonus +0.5"
        
    # Skenario 3: False Accumulation / Harga Ketinggian
    elif diff_pct < -7.0:
        nar = f"Akumulasi Tertinggal: Harga pasar (+{-diff_pct:.1f}%) terlampau jauh meninggalkan modal bandar ({avg_cost_top3:.0f}). Rawan guyuran profit taking."
        return -1.0, "risk", nar, f"Trap: Price {current_price} jauh di atas Cost {avg_cost_top3:.0f} ({diff_pct:.1f}%) -> Penalti -1.0"
        
    # Skenario 4: Passive Accumulation
    else:
        return 0.0, "neutral", "", f"Akumulasi Pasif: Cost {avg_cost_top3:.0f} di bawah Price {current_price} ({diff_pct:.1f}%) -> Imbang (Netral)"

def _detect_fomo_trap(w7_accumulators: list, w7_distributors: list, current_price: float, bandar_avg_cost_7d: float) -> tuple[float, str, str, str]:
    """
    Mendeteksi jebakan pucuk (Exit Liquidity): 
    Harga dipompa meroket, namun Institusi justru membuang barang ke Ritel (YP, XC, PD dkk).
    Returns: (score_adjustment, type (driver/risk/neutral), narrative, internal_log)
    """
    if not w7_accumulators or not w7_distributors or current_price <= 0 or bandar_avg_cost_7d <= 0:
        return 0.0, "neutral", "", ""
        
    # 1. Syarat Harga: Harga harus sedang "terbang" atau jauh di atas modal bandar (minimal > 4% dari modal bandar)
    diff_price = ((current_price - bandar_avg_cost_7d) / bandar_avg_cost_7d) * 100
    if diff_price < 4.0:
        return 0.0, "neutral", "", "" # Bukan trap pucuk kalau harga lagi turun/sideways
        
    # Broker institusi & asing kuat (Asing + Lokal)
    INST_BROKERS = {"BK", "ZP", "AK", "CS", "RX", "KZ", "YU", "CG", "DX", "BB", "IF", "OD", "TP", "NI", "CC", "GW", "AI", "AG", "DB", "DP", "LG", "LS", "HD", "MS", "GR", "ML", "UB"}
    # Broker Ritel Murni (FOMO Army)
    RETAIL_BROKERS = {"YP", "XC", "XL", "PD", "SQ"}
    
    # 2. Cek apakah Ritel dominan di Top 3 Buyer
    top_buyers_code = [code for code, data in w7_accumulators[:3]]
    retail_buyers = [b for b in top_buyers_code if b in RETAIL_BROKERS]
    
    # 3. Cek apakah Institusi / Asing dominan di Top 3 Seller (Berdasarkan Kode ATAU Tipe Broker 'Asing')
    inst_sellers = [
        code for code, data in w7_distributors[:3] 
        if code in INST_BROKERS or data.get("type") in ["Asing", "FOREIGN", "F", "Foreign"]
    ]
    
    # 4. TRAP TERKONFIRMASI: Jika minimal 2 ritel ada di top buyer, DAN minimal 1-2 institusi di top seller membuang barang
    if len(retail_buyers) >= 1 and len(inst_sellers) >= 1:
        # Hitung dominasinya untuk narasi
        ret_str = ", ".join(retail_buyers)
        inst_str = ", ".join(inst_sellers)
        nar = f"🚨 Retail FOMO Trap: Harga dipompa naik (+{diff_price:.1f}% dari modal bandar), namun Institusi ({inst_str}) membuang barang yang ditampung Ritel ({ret_str}). Sangat rawan jebol (Exit Liquidity)."
        log = f"FOMO Trap Detected! Price +{diff_price:.1f}% -> Inst Seller ({inst_str}) vs Retail Buyer ({ret_str}) -> Penalti -1.5"
        return -1.5, "risk", nar, log
        
    return 0.0, "neutral", "", ""

def _format_broker_detail(broker_code: str, broker_data: dict,
                          window_days: int, current_price: float = 0) -> dict:
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

    avg_price = broker_data["avg_price"]
    distance_pct = None
    if current_price > 0 and avg_price > 0:
        distance_pct = ((current_price - avg_price) / avg_price) * 100

    return {
        "broker": broker_code,
        "broker_name": broker_data["broker_name"],
        "total_buy_lot": broker_data["total_buy_lot"],
        "total_buy_value": broker_data["total_buy_value"],
        "avg_price": avg_price,
        "active_days": f"{broker_data['active_days']}/{window_days} hari",
        "status": status,
        "distance_pct": distance_pct,
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


def analyze(
    ticker: str,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
) -> dict:
    """
    Analisis bandarmologi lengkap:
    - Window 7 hari (timing signal)
    - Window 30 hari (true cost bandar)
    - Entry assessment vs avg cost bandar
    """
    bandarm_data = get_full_bandarm_data(ticker, date_from=date_from, date_to=date_to)
    info = get_stock_info(ticker)
    try:
        current_price = get_current_price_stockbit(ticker) or 0
    except Exception:
        current_price = info.get("current_price") or 0

    w7 = bandarm_data["w7"]
    w30 = bandarm_data["w30"]

    data_used = ["Stockbit broker summary 7H & 1M"]

    # === Base Evaluations ===
    eval_7d = _assess_accumulation(w7["top_accumulators"], BROKER_WATCH_SHORT)
    eval_30d = _assess_accumulation(w30["top_accumulators"], BROKER_WATCH_LONG)
    
    signal_7d = eval_7d["status"]
    signal_30d = eval_30d["status"]

    # === Distribution Signal ===
    dist_adj_7d, dist_signal_7d, dist_notes_7d = _assess_distribution(w7)
    dist_adj_30d, dist_signal_30d, dist_notes_30d = _assess_distribution(w30)
    
    # === PHASE MATRIX BASE SCORE ===
    score, phase_signal, phase_narrative = _evaluate_bandar_phase(eval_7d, eval_30d, dist_signal_7d, dist_signal_30d)
    data_used.append(phase_narrative)
    
    # Apply Distribution Penalties on top of base score
    score += dist_adj_7d + dist_adj_30d
    if dist_notes_7d:
        data_used.append("Distribution 7H: " + ", ".join(dist_notes_7d))
    if dist_notes_30d:
        data_used.append("Distribution 1M: " + ", ".join(dist_notes_30d))

    # === Deteksi Estafet (Ritel -> Asing) ===
    estafet_bonus, estafet_narrative = _detect_broker_estafet(w30.get("top_distributors", []), w7.get("top_accumulators", []))
    if estafet_bonus > 0:
        score += estafet_bonus
        data_used.append(estafet_narrative)
        
    # === Rasio Konsentrasi (The Pyramid) ===
    conc_score, conc_type, conc_narrative, conc_log = _assess_concentration(
        w7.get("top_accumulators", []), 
        w7.get("top_distributors", []), 
        w7
    )
    score += conc_score
    data_used.append(conc_log)

    # === Agresivitas Bandar (HAKA Indicator) ===
    # HAKA hanya dinilai jika fase 7 harinya beneran Akumulasi
    is_accum = (signal_7d in ["STRONG_ACCUM", "MODERATE_ACCUM", "LIGHT_ACCUM"])
    haka_score, haka_type, haka_narrative, haka_log = _assess_aggressiveness(
        w7.get("top_accumulators", []), 
        current_price,
        is_accum
    )
    score += haka_score
    if haka_log:
        data_used.append(haka_log)

    # === Foreign Flow (Net Asing) ===
    foreign_7d = w7["foreign_net"]
    foreign_30d = w30["foreign_net"]

    if foreign_7d > 0 and foreign_30d > 0:
        score += 1.0
        data_used.append(f"Foreign net buy akumulasi 7H & 1M")
    elif foreign_7d > 0:
        score += 0.5
        data_used.append(f"Foreign net buy jangka pendek 7H")
    elif foreign_7d < 0 and foreign_30d < 0:
        score -= 1.0
        data_used.append(f"Foreign buang barang (net sell) 7H & 1M")

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
    top_7d = [_format_broker_detail(code, data, BROKER_WATCH_SHORT, current_price)
              for code, data in w7["top_accumulators"][:10]]
    top_30d = [_format_broker_detail(code, data, BROKER_WATCH_LONG, current_price)
               for code, data in w30["top_accumulators"][:10]]

    top_dist_7d = [_format_distribution_detail(code, data, BROKER_WATCH_SHORT)
                   for code, data in w7.get("top_distributors", [])[:10]]
    top_dist_30d = [_format_distribution_detail(code, data, BROKER_WATCH_LONG)
                    for code, data in w30.get("top_distributors", [])[:10]]

    # === Entry Analysis ===
    bandar_avg_7d = w7["top_accumulators"][0][1]["avg_price"] if w7["top_accumulators"] else 0
    bandar_avg_1m = w30["top_accumulators"][0][1]["avg_price"] if w30["top_accumulators"] else 0

    price_analysis = {}
    anom_akum_7d = None
    anom_akum_1m = None
    anom_dist_7d = None
    anom_dist_1m = None
    if current_price > 0 and bandar_avg_7d > 0 and bandar_avg_1m > 0:
        entry_assessment = assess_entry_vs_bandar(current_price, bandar_avg_7d, bandar_avg_1m)
        # Net foreign status
        def net_status(val):
            if val > 0:
                return f"net buy ({val:,.0f})"
            elif val < 0:
                return f"net sell ({val:,.0f})"
            else:
                return "netral"

        # Anomali akumulasi/distribusi besar (top 5 broker)
        def detect_anomali(top_brokers, key_value, key_lot):
            if not top_brokers:
                return None
            values = [b[1][key_value] for b in top_brokers]
            lots = [b[1][key_lot] for b in top_brokers]
            avg_value = sum(values) / len(values) if values else 0
            avg_lot = sum(lots) / len(lots) if lots else 0
            for code, data in top_brokers:
                if avg_value > 0 and data[key_value] >= 3 * avg_value:
                    return f"{code} ({data['broker_name']}) value {data[key_value]:,.0f} (≥3x rata2 top 5)"
                if avg_lot > 0 and data[key_lot] >= 3 * avg_lot:
                    return f"{code} ({data['broker_name']}) lot {data[key_lot]:,.0f} (≥3x rata2 top 5)"
            return None

        anom_akum_7d = detect_anomali(w7["top_accumulators"][:5], "total_buy_value", "total_buy_lot")
        anom_akum_1m = detect_anomali(w30["top_accumulators"][:5], "total_buy_value", "total_buy_lot")
        anom_dist_7d = detect_anomali(w7.get("top_distributors", [])[:5], "total_sell_value", "total_sell_lot")
        anom_dist_1m = detect_anomali(w30.get("top_distributors", [])[:5], "total_sell_value", "total_sell_lot")

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
            "net_foreign_7d": net_status(foreign_7d),
            "net_foreign_1m": net_status(foreign_30d),
            "anomali_akumulasi_7d": anom_akum_7d,
            "anomali_akumulasi_1m": anom_akum_1m,
            "anomali_distribusi_7d": anom_dist_7d,
            "anomali_distribusi_1m": anom_dist_1m,
        }

    # Pengaruh score dari anomali akumulasi/distribusi
    anomali_score = 0.0
    broker_to_watch = []
    # Akumulasi 7d
    if anom_akum_7d:
        anomali_score += 1.0
        # Ekstrak kode broker dari string anomali
        code = anom_akum_7d.split()[0]
        name = anom_akum_7d.split('(',1)[1].split(')',1)[0] if '(' in anom_akum_7d else code
        broker_to_watch.append(f"{code} ({name}) [ANOMALI AKUMULASI]")
    # Akumulasi 1m
    if anom_akum_1m:
        anomali_score += 1.0
        code = anom_akum_1m.split()[0]
        name = anom_akum_1m.split('(',1)[1].split(')',1)[0] if '(' in anom_akum_1m else code
        broker_to_watch.append(f"{code} ({name}) [ANOMALI AKUMULASI]")
    # Distribusi 7d
    if anom_dist_7d:
        anomali_score -= 1.0
        code = anom_dist_7d.split()[0]
        name = anom_dist_7d.split('(',1)[1].split(')',1)[0] if '(' in anom_dist_7d else code
        broker_to_watch.append(f"{code} ({name}) [ANOMALI DISTRIBUSI]")
    # Distribusi 1m
    if anom_dist_1m:
        anomali_score -= 1.0
        code = anom_dist_1m.split()[0]
        name = anom_dist_1m.split('(',1)[1].split(')',1)[0] if '(' in anom_dist_1m else code
        broker_to_watch.append(f"{code} ({name}) [ANOMALI DISTRIBUSI]")

    # Tambahkan broker top 2 akumulasi 7d (jika belum ada)
    for code, data in w7["top_accumulators"][:2]:
        label = f"{code} ({data['broker_name']})"
        if label not in broker_to_watch:
            broker_to_watch.append(label)

    # Tambahkan score anomali ke score utama
    score += anomali_score

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
    
    # === Deteksi FOMO Trap (Exit Liquidity) ===
    fomo_score, fomo_type, fomo_narrative, fomo_log = _detect_fomo_trap(
        w7.get("top_accumulators", []),
        w7.get("top_distributors", []),
        current_price,
        price_analysis.get("bandar_avg_7d", 0)
    )
    score += fomo_score
    if fomo_log:
        data_used.append(fomo_log)

    # === Retail Broker Penalty (XL, XC, YP, PD) ===
    RETAIL_BROKERS_PENALTY = {"YP", "XC", "XL", "PD"}
    retail_penalty = 0.0
    # Cek top 3 broker akumulasi 7 hari
    if w7["top_accumulators"]:
        top_brokers = w7["top_accumulators"][:5]
        values = [data["total_buy_value"] for code, data in top_brokers]
        lots = [data["total_buy_lot"] for code, data in top_brokers]
        avg_value = sum(values) / len(values) if values else 0
        avg_lot = sum(lots) / len(lots) if lots else 0
        for rank, (code, data) in enumerate(top_brokers[:3], 1):
            if code in RETAIL_BROKERS_PENALTY:
                # Anomali jika value/lot 2x lebih besar dari rata2 top 5
                if (data["total_buy_value"] >= 2 * avg_value or data["total_buy_lot"] >= 2 * avg_lot):
                    data_used.append(f"Anomali: Broker retail {code} akumulasi besar di rank {rank} (anomali, no penalty)")
                else:
                    retail_penalty -= 1.0
                    data_used.append(f"Penalty: Broker retail {code} akumulasi di rank {rank} (score -1.0)")
    score += retail_penalty

    # === Calculate aggregated metrics for UI ===
    # Window 7 days
    w7_net_lot = sum(b[1]["total_buy_lot"] for b in w7.get("top_accumulators", [])) - \
                 sum(d[1]["total_sell_lot"] for d in w7.get("top_distributors", []))
    w7_net_value = sum(b[1]["total_buy_value"] for b in w7.get("top_accumulators", [])) - \
                   sum(d[1]["total_sell_value"] for d in w7.get("top_distributors", []))
    w7_total_buyer = len(w7.get("top_accumulators", []))
    w7_total_seller = len(w7.get("top_distributors", []))

    # Window 30 days
    w30_net_lot = sum(b[1]["total_buy_lot"] for b in w30.get("top_accumulators", [])) - \
                  sum(d[1]["total_sell_lot"] for d in w30.get("top_distributors", []))
    w30_net_value = sum(b[1]["total_buy_value"] for b in w30.get("top_accumulators", [])) - \
                    sum(d[1]["total_sell_value"] for d in w30.get("top_distributors", []))
    w30_total_buyer = len(w30.get("top_accumulators", []))
    w30_total_seller = len(w30.get("top_distributors", []))

    res = {
        "ticker": ticker,
        "score": round(score, 1),
        "signal": signal,
        "weight": "40%",
        "window_7d": {
            "period": w7["period"],
            "bandar_signal": signal_7d.replace("_", " ").title(),
            "assessment": signal_7d.replace("_", " ").title(),
            "net_lot": w7_net_lot,
            "net_value": w7_net_value,
            "total_buyer": w7_total_buyer,
            "total_seller": w7_total_seller,
            "top_accumulators": top_7d,
            "top_distributors": top_dist_7d,
            "distribution_signal": dist_signal_7d,
            "foreign_net_7d": foreign_7d,
        },
        "window_1m": {
            "period": w30["period"],
            "bandar_signal": signal_30d.replace("_", " ").title(),
            "assessment": signal_30d.replace("_", " ").title(),
            "net_lot": w30_net_lot,
            "net_value": w30_net_value,
            "total_buyer": w30_total_buyer,
            "total_seller": w30_total_seller,
            "top_accumulators": top_30d,
            "top_distributors": top_dist_30d,
            "distribution_signal": dist_signal_30d,
            "foreign_net_1m": foreign_30d,
        },
        "price_analysis": price_analysis,
        "broker_to_watch": broker_to_watch,
        "data_used": data_used,
        "confidence": confidence,
        "insight_concentration": {
            "type": conc_type,
            "narrative": conc_narrative
        },
        "insight_aggressiveness": {
            "type": haka_type,
            "narrative": haka_narrative
        },
        "insight_fomo_trap": {
            "type": fomo_type,
            "narrative": fomo_narrative
        }
    }

    if "custom_window" in bandarm_data:
        cw = bandarm_data["custom_window"]
        cw_days = cw.get("window_days", 1)
        top_accum_cw = [_format_broker_detail(code, data, cw_days, current_price)
                        for code, data in cw.get("top_accumulators", [])[:10]]
        top_dist_cw = [_format_distribution_detail(code, data, cw_days)
                       for code, data in cw.get("top_distributors", [])[:10]]
        res["custom_window"] = {
            "period": cw.get("period", ""),
            "window_days": cw_days,
            "top_accumulators": top_accum_cw,
            "top_distributors": top_dist_cw,
            "distribution_top3_value": cw.get("distribution_top3_value", 0),
            "foreign_net": cw.get("foreign_net", 0),
        }

    return res


if __name__ == "__main__":
    import sys, json
    ticker = sys.argv[1] if len(sys.argv) > 1 else "ANTM"
    result = analyze(ticker)
    print(json.dumps(result, indent=2, ensure_ascii=False))
