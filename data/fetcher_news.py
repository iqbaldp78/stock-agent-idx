"""
Data Fetcher — News & Report (Local RAG Vector Database)
Mengambil berita dan laporan saham terkait ticker dari database RAG lokal (news_signals).
"""
import logging
from typing import List, Dict, Optional
from scripts.rag_retriever import search_by_ticker

logger = logging.getLogger(__name__)


def fetch_news(ticker: str, limit: int = 10, doc_type: Optional[str] = None) -> List[Dict]:
    """
    Mengambil berita dan laporan terkait ticker saham dari RAG Vector Database lokal.
    
    Args:
        ticker (str): Ticker saham (contoh: "BBCA").
        limit (int): Jumlah maksimum berita/laporan yang diambil.
        doc_type (str, optional): 'news' atau 'report'. Jika None, mengambil keduanya.
    
    Returns:
        List[Dict]: Daftar artikel/laporan dengan judul, deskripsi, tanggal, dan sentimen.
    """
    try:
        rag_results = search_by_ticker(ticker, limit=limit, doc_type=doc_type)
        articles = []
        for item in rag_results:
            kind = (item.get("doc_type") or "news").upper()
            articles.append({
                "title": f"[{kind}] " + (item.get("summary") or item.get("content", "")[:100]),
                "description": item.get("content", ""),
                "published_at": str(item.get("created_at", "")),
                "source": f"Stockbit RAG {kind.capitalize()}",
                "url": "",
                "sentiment": item.get("sentiment", "NEUTRAL"),
                "doc_type": item.get("doc_type", "news"),
                "impact_scope": item.get("impact_scope", "Micro"),
            })
        return articles
    except Exception as e:
        logger.warning(f"Error fetching RAG news/reports for {ticker}: {e}")
        return []


if __name__ == "__main__":
    ticker = "BBCA"
    news = fetch_news(ticker, limit=5)
    print(f"RAG News/Reports for {ticker}: {len(news)} items")
    for article in news:
        print(f"- {article['title']} ({article['published_at']})")
