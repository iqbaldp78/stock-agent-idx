"""
Data Module — Report Detector
Mendeteksi laporan keuangan kuartalan terbaru dari RAG DB (news_signals) dan menghitung time-decay factor.
"""

import re
import logging
from datetime import datetime, date
from typing import Dict, Optional
from scripts.rag_retriever import search_by_ticker

logger = logging.getLogger(__name__)

REPORT_DECAY_FULL_DAYS = 3
REPORT_DECAY_MAX_DAYS = 14


def extract_quarter_info(text: str) -> Optional[str]:
    """
    Ekstrak informasi kuartal (e.g. Q1 2026, Q2 2025, Semester I, dsb) dari teks report.
    """
    if not text:
        return None

    # Match patterns like Q1/Q2/Q3/Q4 202x or Kuartal 1/2/3/4 202x
    q_match = re.search(r'\b(Q[1-4]|Kuartal\s*[1-4]|Semester\s*[1-2])\s*(?:Tahun\s*)?(\d{4})?\b', text, re.IGNORECASE)
    if q_match:
        quarter_str = q_match.group(1).upper()
        year_str = q_match.group(2) if q_match.group(2) else ""
        return f"{quarter_str} {year_str}".strip()

    # Match patterns like Laporan Keuangan 202x
    lk_match = re.search(r'\bLaporan\s+Keuangan\s+(?:Kuartal\s*([1-4])\s+)?(\d{4})\b', text, re.IGNORECASE)
    if lk_match:
        q_num = lk_match.group(1)
        year_str = lk_match.group(2)
        if q_num:
            return f"Q{q_num} {year_str}"
        return f"FY {year_str}"

    return None


def calculate_decay_weight(created_at: datetime) -> tuple[float, int]:
    """
    Hitung decay weight berdasarkan tanggal publish report:
    - Hari 0..3: weight = 1.0 (full weight)
    - Hari 4..14: weight linear decay (1.0 -> 0.0)
    - Hari > 14: weight = 0.0
    
    Returns: (decay_weight, days_since_publish)
    """
    now = datetime.now()
    if isinstance(created_at, date) and not isinstance(created_at, datetime):
        created_at = datetime.combine(created_at, datetime.min.time())

    # Strip timezone if present to avoid tz aware/naive comparison issues
    if hasattr(created_at, 'tzinfo') and created_at.tzinfo is not None:
        created_at = created_at.replace(tzinfo=None)

    days_diff = max(0, (now - created_at).days)

    if days_diff <= REPORT_DECAY_FULL_DAYS:
        decay_weight = 1.0
    elif days_diff <= REPORT_DECAY_MAX_DAYS:
        # Linear decay from 1.0 to 0.0 over days 4..14 (11 days span)
        decay_weight = 1.0 - ((days_diff - REPORT_DECAY_FULL_DAYS) / (REPORT_DECAY_MAX_DAYS - REPORT_DECAY_FULL_DAYS))
        decay_weight = round(max(0.0, min(1.0, decay_weight)), 2)
    else:
        decay_weight = 0.0

    return decay_weight, days_diff


def is_financial_earnings_report(text: str) -> bool:
    """
    Mengecek apakah teks report merupakan laporan kinerja keuangan (kuartalan/semesteran/tahunan),
    bukan pengumuman rutin/administratif seperti laporan bulanan pemegang saham, perubahan komite, dsb.
    """
    if not text:
        return False
    t = text.lower()
    
    # 1. Direct Exclusions for routine administrative filings
    exclusions = [
        "registrasi pemegang", "pemegang efek", "pemegang saham", "laporan bulanan",
        "bukti publikasi", "rencana penyampaian", "jadwal penyampaian", "jadwal jatuh tempo",
        "perubahan komite", "perubahan susunan", "komisaris", "direksi", "wafat",
        "pencatatan saham baru", "konversi waran", "tender offer", "hmetd", "rups",
        "gerak hijau", "sertifikat saham", "kepala unit audit", "audit internal",
        "sekretaris perusahaan", "tanpa dampak material terhadap kinerja",
        "tanpa detail kinerja", "tanpa perubahan material"
    ]
    if any(ex in t for ex in exclusions):
        return False
        
    # 2. Must contain earnings/profit metrics or explicit financial performance mentions
    earnings_terms = [
        "laba bersih", "rugi bersih", "laba usaha", "laba operasional", "pendapatan",
        "revenue", "net profit", "penjualan", "ebitda"
    ]
    if any(term in t for term in earnings_terms):
        return True

    fs_terms = [
        "laporan keuangan interim", "laporan keuangan kuartal", "laporan keuangan semester",
        "laporan keuangan konsolidasian", "laporan keuangan tahunan"
    ]
    return any(term in t for term in fs_terms)



def detect_quarterly_report(ticker: str) -> Dict:
    """
    Mendeteksi apakah ticker memiliki laporan keuangan kuartalan terbaru dalam 14 hari terakhir di RAG DB.
    """
    try:
        # Search DB specifically for doc_type = 'financial_report'
        fin_reports = search_by_ticker(ticker, limit=5, doc_type="financial_report")
        
        # Fallback to search doc_type = 'report' with keyword filter if financial_report query yields nothing
        if not fin_reports:
            reports = search_by_ticker(ticker, limit=10, doc_type="report")
            fin_reports = [r for r in reports if is_financial_earnings_report(r.get("summary") or r.get("content", ""))]

        if not fin_reports:
            return {
                "has_recent_report": False,
                "is_financial_report": False,
                "report_category": None,
                "quarter": None,
                "sentiment": None,
                "sentiment_score": None,
                "published_at": None,
                "days_since_publish": None,
                "decay_weight": 0.0,
                "summary": None,
            }

        # Check latest financial earnings report
        latest_report = fin_reports[0]
        created_at = latest_report.get("created_at")

        if not created_at:
            return {
                "has_recent_report": False,
                "is_financial_report": False,
                "report_category": None,
                "quarter": None,
                "sentiment": None,
                "sentiment_score": None,
                "published_at": None,
                "days_since_publish": None,
                "decay_weight": 0.0,
                "summary": None,
            }

        decay_weight, days_diff = calculate_decay_weight(created_at)

        if decay_weight <= 0.0:
            return {
                "has_recent_report": False,
                "is_financial_report": True,
                "report_category": "FINANCIAL_REPORT",
                "quarter": None,
                "sentiment": latest_report.get("sentiment"),
                "sentiment_score": latest_report.get("sentiment_score", 5),
                "published_at": str(created_at),
                "days_since_publish": days_diff,
                "decay_weight": 0.0,
                "summary": latest_report.get("summary"),
            }

        summary_text = latest_report.get("summary") or latest_report.get("content", "")
        quarter_info = extract_quarter_info(summary_text)

        # Fallback quarter estimation if pattern match didn't find specific Q number
        if not quarter_info and hasattr(created_at, 'month'):
            month = created_at.month
            year = created_at.year
            if month in [1, 2, 3, 4]:
                q_est = "Q4"
                year_str = str(year - 1)
            elif month in [5, 6, 7]:
                q_est = "Q1"
                year_str = str(year)
            elif month in [8, 9, 10]:
                q_est = "Q2"
                year_str = str(year)
            else:
                q_est = "Q3"
                year_str = str(year)
            quarter_info = f"{q_est} {year_str}"

        return {
            "has_recent_report": True,
            "is_financial_report": True,
            "report_category": "FINANCIAL_REPORT",
            "quarter": quarter_info or "Quarterly Report",
            "sentiment": latest_report.get("sentiment", "Neutral"),
            "sentiment_score": latest_report.get("sentiment_score", 5),
            "published_at": str(created_at),
            "days_since_publish": days_diff,
            "decay_weight": decay_weight,
            "summary": summary_text,
        }

    except Exception as e:
        logger.warning(f"Error detecting quarterly report for {ticker}: {e}")
        return {
            "has_recent_report": False,
            "is_financial_report": False,
            "report_category": None,
            "quarter": None,
            "sentiment": None,
            "sentiment_score": None,
            "published_at": None,
            "days_since_publish": None,
            "decay_weight": 0.0,
            "summary": None,
        }


