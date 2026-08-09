"""
Graph — Scoring
Composite score dengan bobot dinamis berdasarkan kategori saham.
"""
from config import WEIGHTS, WEIGHTS_REPORT_BOOST, BIG_CAP_TICKERS, SMALL_CAP_MAX_MC


def get_weights(ticker: str, market_cap: float, is_volatile: bool, has_recent_report: bool = False) -> dict:
    """Tentukan bobot berdasarkan kondisi saham, pasar, dan ketersediaan laporan keuangan terbaru."""
    weights_dict = WEIGHTS_REPORT_BOOST if has_recent_report else WEIGHTS
    if is_volatile:
        return weights_dict["volatile"]
    elif ticker in BIG_CAP_TICKERS:
        return weights_dict["big_cap"]
    elif market_cap and market_cap < SMALL_CAP_MAX_MC:
        return weights_dict["small_cap"]
    return weights_dict["default"]


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
                         market_cap: float, is_volatile: bool,
                         macro_data: dict = None,
                         exclude_fundamental: bool = False,
                         has_recent_report: bool = False) -> dict:
    """
    Hitung composite score dari 5 agent (bandarm, technical, fundamental, macro, news).
    scores = {"bandarm": 8.5, "technical": 7.0, "fundamental": 8.0, "macro": 7.0, "news": 6.5}
    """
    w = get_weights(ticker, market_cap, is_volatile, has_recent_report=has_recent_report)
    
    total_w = w["bandarm"] + w["technical"] + w["macro"] + w.get("news", 0.12)
    
    if exclude_fundamental:
        composite = (
            scores["bandarm"] * (w["bandarm"] / total_w) +
            scores["technical"] * (w["technical"] / total_w) +
            scores["macro"] * (w["macro"] / total_w) +
            scores.get("news", 5) * (w.get("news", 0.12) / total_w)
        )
    else:
        composite = (
            scores["bandarm"] * w["bandarm"] +
            scores["technical"] * w["technical"] +
            scores.get("fundamental", 5.0) * w["fundamental"] +
            scores["macro"] * w["macro"] +
            scores.get("news", 5) * w.get("news", 0.12)
        )
    
    # USD/IDR Sector Adjustment
    sector = "Unknown"
    usdidr_adj = 0.0
    usdidr_narrative = ""
        
    ml_bonus_adj = 0.0
    ml_bonus_narrative = ""
        
    if macro_data:
        # Common idx sectors map
        COMMON_SECTORS = {
            "ADRO": "Energy", "PTBA": "Energy", "ITMG": "Energy", "HRUM": "Energy", "BUMI": "Energy", "MEDC": "Energy", "PGAS": "Energy", "AKRA": "Energy", "CUAN": "Energy", "DEWA": "Energy", "ESSA": "Energy",
            "BREN": "Utilities", "PGEO": "Utilities", "KEEN": "Utilities",
            "AMMN": "Basic Materials", "MDKA": "Basic Materials", "BRMS": "Basic Materials", "ANTM": "Basic Materials", "INCO": "Basic Materials", "TPIA": "Basic Materials", "BRPT": "Basic Materials", "SMGR": "Basic Materials", "INTP": "Basic Materials", "MBMA": "Basic Materials",
            "BBCA": "Financial Services", "BBRI": "Financial Services", "BMRI": "Financial Services", "BBNI": "Financial Services", "BRIS": "Financial Services", "ARTO": "Financial Services", "BBTN": "Financial Services",
            "ICBP": "Consumer Defensive", "INDF": "Consumer Defensive", "MYOR": "Consumer Defensive", "UNVR": "Consumer Defensive", "CMRY": "Consumer Defensive", "AMRT": "Consumer Defensive", "MIDI": "Consumer Defensive", "CPIN": "Consumer Defensive", "JPFA": "Consumer Defensive",
            "ASII": "Industrials", "UNTR": "Industrials", "JSMR": "Industrials",
            "TLKM": "Communication Services", "ISAT": "Communication Services", "EXCL": "Communication Services", "TOWR": "Communication Services",
            "GOTO": "Technology", "BUKA": "Technology", "EMTK": "Technology",
            "MAPI": "Consumer Cyclical", "ACES": "Consumer Cyclical", "ERAA": "Consumer Cyclical", "HRTA": "Consumer Cyclical", "MSIN": "Consumer Cyclical",
            "KLBF": "Healthcare", "MIKA": "Healthcare", "HEAL": "Healthcare",
            "CTRA": "Real Estate", "BSDE": "Real Estate", "PWON": "Real Estate", "SMRA": "Real Estate", "AADI": "Energy"
        }
        
        sector = COMMON_SECTORS.get(ticker.upper())
        if not sector:
            try:
                import yfinance as yf
                info = yf.Ticker(f"{ticker.upper()}.JK").info
                sector = info.get('sector', 'Unknown')
            except Exception:
                sector = 'Unknown'
                
        usdidr_1d_change = macro_data.get("usdidr_1d_change_pct", 0.0)
        
        # IDR melemah (USD/IDR naik hari ini) -> positif untuk eksportir, negatif untuk importir
        if usdidr_1d_change > 0.5:
            if sector in ["Energy", "Basic Materials"]:
                usdidr_adj = 0.5
                usdidr_narrative = f"Bonus eksportir (USD/IDR naik {usdidr_1d_change}%)"
            elif sector in ["Consumer Defensive", "Healthcare", "Real Estate", "Financial Services"]:
                usdidr_adj = -0.5
                usdidr_narrative = f"Penalti beban valas (USD/IDR naik {usdidr_1d_change}%)"
        # IDR menguat (USD/IDR turun hari ini) -> negatif untuk eksportir, positif untuk importir
        elif usdidr_1d_change < -0.5:
            if sector in ["Energy", "Basic Materials"]:
                usdidr_adj = -0.3
                usdidr_narrative = f"Penalti eksportir (Rupiah menguat {abs(usdidr_1d_change)}%)"
            elif sector in ["Consumer Defensive", "Healthcare", "Real Estate", "Financial Services"]:
                usdidr_adj = 0.5
                usdidr_narrative = f"Sinyal positif valas reda (Rupiah menguat {abs(usdidr_1d_change)}%)"
                
        # Tambahan ML Prediction Buy
        if macro_data.get("ml_signal") == "BUY":
            ml_bonus_adj = 2.0
            ml_bonus_narrative = "Bonus Sinyal ML Prediction Buy (+2.0)"
            
        composite += usdidr_adj + ml_bonus_adj
        composite = max(1.0, min(10.0, composite))
    
    mode = detect_mode(ticker, market_cap, is_volatile)

    return {
        "ticker": ticker,
        "composite_score": round(composite, 2),
        "weights_used": w,
        "weight_mode": mode,
        "sector": sector,
        "usdidr_adj": usdidr_adj,
        "usdidr_narrative": usdidr_narrative + (" | " + ml_bonus_narrative if ml_bonus_narrative else ""),
        "breakdown": {
            "bandarm": {"score": scores["bandarm"], "weight": w["bandarm"] if not exclude_fundamental else w["bandarm"] / total_w,
                        "contribution": round(scores["bandarm"] * (w["bandarm"] if not exclude_fundamental else w["bandarm"] / total_w), 2)},
            "technical": {"score": scores["technical"], "weight": w["technical"] if not exclude_fundamental else w["technical"] / total_w,
                          "contribution": round(scores["technical"] * (w["technical"] if not exclude_fundamental else w["technical"] / total_w), 2)},
            "fundamental": {"score": scores.get("fundamental", 5.0), "weight": w["fundamental"] if not exclude_fundamental else 0.0,
                            "contribution": round(scores.get("fundamental", 5.0) * (w["fundamental"] if not exclude_fundamental else 0.0), 2)},
            "macro": {"score": scores["macro"], "weight": w["macro"] if not exclude_fundamental else w["macro"] / total_w,
                      "contribution": round(scores["macro"] * (w["macro"] if not exclude_fundamental else w["macro"] / total_w), 2)},
            "news": {"score": scores.get("news", 5), "weight": w.get("news", 0.12) if not exclude_fundamental else w.get("news", 0.12) / total_w,
                     "contribution": round(scores.get("news", 5) * (w.get("news", 0.12) if not exclude_fundamental else w.get("news", 0.12) / total_w), 2)}
        }
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

    # Status difokuskan ke jarak dari avg 7 hari (jangka pendek) 
    # bukan 1 bulan (true cost yang kejauhan) untuk menyesuaikan ritme trading
    if dist_7d <= 0:
        status = "🟢 IDEAL"
        label = f"Harga {abs(dist_7d):.1f}% DI BAWAH avg cost bandar seminggu terakhir — ideal entry"
    elif dist_7d <= 3:
        status = "🟡 ACCEPTABLE"
        label = f"Harga {dist_7d:.1f}% di atas cost bandar mingguan — layak entry"
    elif dist_7d <= 7:
        status = "🟠 CAUTION"
        label = f"Harga {dist_7d:.1f}% di atas cost bandar mingguan — tunggu pullback"
    else:
        status = "🔴 AVOID"
        label = f"Harga {dist_7d:.1f}% terlalu jauh dari cost bandar (rawan guyur profit taking)"

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

def calculate_konglo_composite(scores: dict, ticker: str,
                               market_cap: float, is_volatile: bool,
                               macro_data: dict = None,
                               has_recent_report: bool = False) -> dict:
    """
    Hitung composite score khusus Konglo Play:
    Normal: Technical 45%, Bandarmologi 45%, News 5%, Fundamental 5%.
    With Recent Report: Technical 41%, Bandarmologi 42%, News 12%, Fundamental 5%.
    """
    if has_recent_report:
        w = {
            "technical": 0.41,
            "bandarm": 0.42,
            "fundamental": 0.05,
            "news": 0.12,
            "macro": 0.0
        }
    else:
        w = {
            "technical": 0.45,
            "bandarm": 0.45,
            "fundamental": 0.05,
            "news": 0.05,
            "macro": 0.0
        }
    
    composite = (
        scores["bandarm"] * w["bandarm"] +
        scores["technical"] * w["technical"] +
        scores.get("fundamental", 5.0) * w["fundamental"] +
        scores.get("news", 5.0) * w["news"]
    )
    
    ml_bonus_adj = 0.0
    ml_bonus_narrative = ""
    if macro_data:
        if macro_data.get("ml_signal") == "BUY":
            ml_bonus_adj = 2.0
            ml_bonus_narrative = "Bonus Sinyal ML Prediction Buy (+2.0)"
            
        composite += ml_bonus_adj
        composite = max(1.0, min(10.0, composite))
    
    sector = "Unknown"
    
    return {
        "ticker": ticker,
        "composite_score": round(composite, 2),
        "weights_used": w,
        "weight_mode": "konglo",
        "sector": sector,
        "usdidr_adj": 0.0,
        "usdidr_narrative": ml_bonus_narrative,
        "breakdown": {
            "bandarm": {"score": scores["bandarm"], "weight": w["bandarm"],
                        "contribution": round(scores["bandarm"] * w["bandarm"], 2)},
            "technical": {"score": scores["technical"], "weight": w["technical"],
                          "contribution": round(scores["technical"] * w["technical"], 2)},
            "fundamental": {"score": scores.get("fundamental", 5.0), "weight": w["fundamental"],
                            "contribution": round(scores.get("fundamental", 5.0) * w["fundamental"], 2)},
            "news": {"score": scores.get("news", 5.0), "weight": w["news"],
                     "contribution": round(scores.get("news", 5.0) * w["news"], 2)}
        }
    }

