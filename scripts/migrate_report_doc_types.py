"""
Script Migrasi DB — Classify Report Doc Types
Mengklasifikasikan kembali data histori `doc_type = 'report'` di database `news_signals`
menjadi:
- 'financial_report': Laporan Keuangan Kuartalan/Semesteran/Tahunan (Laba/Rugi, Revenue, Kinerja Finansial)
- 'corporate_action': Dividen, Rights Issue, Tender Offer, Pelunasan Obligasi, RUPS
- 'routine_report': Registrasi Pemegang Saham Bulanan, Perubahan Komite/Direksi, Keterbukaan Informasi Umum
"""

import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import logging
import psycopg2

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

DB_URI = os.getenv("VECTOR_DB_URI", "postgresql://vectoruser:vectorpassword@vector_postgres:5432/vectoragent")


def get_db_connection():
    try:
        return psycopg2.connect(DB_URI)
    except Exception as e:
        if "vector_postgres" in DB_URI:
            fallback_uri = DB_URI.replace("vector_postgres:5432", "localhost:5122")
            return psycopg2.connect(fallback_uri)
        raise e


def classify_report(text: str) -> str:
    """
    Mengklasifikasikan teks report menjadi 'financial_report', 'corporate_action', atau 'routine_report'.
    """
    if not text:
        return "routine_report"
    t = text.lower()

    # 1. Corporate Actions
    corp_action_terms = [
        "dividen", "dividend", "rights issue", "hmtd", "hmnetd", "tender offer",
        "pelunasan obligasi", "pelunasan sukuk", "rups", "rupslb", "pembagian dividen",
        "buyback", "pemecahan saham", "stock split"
    ]

    # 2. Routine Administrative Filings Exclusions
    routine_terms = [
        "registrasi pemegang", "pemegang efek", "pemegang saham", "laporan bulanan",
        "bukti publikasi", "rencana penyampaian", "jadwal penyampaian", "jadwal jatuh tempo",
        "perubahan komite", "perubahan susunan", "komisaris", "direksi", "wafat",
        "pencatatan saham baru", "konversi waran", "gerak hijau", "sertifikat saham",
        "kepala unit audit", "audit internal", "sekretaris perusahaan",
        "tanpa dampak material terhadap kinerja", "tanpa detail kinerja", "tanpa perubahan material"
    ]

    # 3. Financial Earnings Terms
    earnings_terms = [
        "laba bersih", "rugi bersih", "laba usaha", "laba operasional", "pendapatan",
        "revenue", "net profit", "penjualan", "ebitda"
    ]

    fs_terms = [
        "laporan keuangan interim", "laporan keuangan kuartal", "laporan keuangan semester",
        "laporan keuangan konsolidasian", "laporan keuangan tahunan"
    ]

    # Rule evaluation:
    if any(ex in t for ex in routine_terms):
        return "routine_report"

    if any(term in t for term in earnings_terms) or any(term in t for term in fs_terms):
        return "financial_report"

    if any(ca in t for ca in corp_action_terms):
        return "corporate_action"

    return "routine_report"


def run_migration():
    logger.info("=== STARTING REPORT DOC_TYPE MIGRATION ===")
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT stream_id, content, summary 
        FROM news_signals 
        WHERE doc_type = 'report' OR doc_type IS NULL
    """)
    rows = cur.fetchall()
    logger.info(f"Found {len(rows)} report records to process.")

    counts = {
        "financial_report": 0,
        "corporate_action": 0,
        "routine_report": 0,
    }

    for stream_id, content, summary in rows:
        text_to_eval = f"{summary or ''} {content or ''}"
        new_doc_type = classify_report(text_to_eval)
        
        cur.execute("""
            UPDATE news_signals 
            SET doc_type = %s 
            WHERE stream_id = %s
        """, (new_doc_type, stream_id))
        
        counts[new_doc_type] += 1

    conn.commit()
    cur.close()
    conn.close()

    logger.info("=== MIGRATION COMPLETED SUCCESSFULLY ===")
    logger.info(f"Summary distribution: {counts}")


if __name__ == "__main__":
    run_migration()
