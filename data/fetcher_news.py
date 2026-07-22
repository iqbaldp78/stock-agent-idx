"""
Data Fetcher — News (Local RAG Vector Database)
Mengambil berita terkait ticker saham dari database RAG lokal (news_signals).
Tidak melakukan HTTP request eksternal ke NewsAPI.
"""
import logging
from typing import List, Dict
from scripts.rag_retriever import search_by_ticker

logger = logging.getLogger(__name__)


def fetch_news(ticker: str, limit: int = 10) -> List[Dict]:
    """
    Mengambil berita terkait ticker saham dari RAG Vector Database lokal.
    
    Args:
        ticker (str): Ticker saham (contoh: "BBCA").
        limit (int): Jumlah maksimum berita yang diambil.
    
    Returns:
        List[Dict]: Daftar berita dengan judul, deskripsi, dan tanggal publikasi.
    """
    try:
        rag_results = search_by_ticker(ticker, limit=limit)
        articles = []
        for item in rag_results:
            articles.append({
                "title": item.get("summary") or item.get("content", "")[:100],
                "description": item.get("content", ""),
                "published_at": str(item.get("created_at", "")),
                "source": "Stockbit RAG News",
                "url": "",
                "sentiment": item.get("sentiment", "NEUTRAL"),
            })
        return articles
    except Exception as e:
        logger.warning(f"Error fetching RAG news for {ticker}: {e}")
        return []


if __name__ == "__main__":
    ticker = "BBCA"
    news = fetch_news(ticker, limit=5)
    print(f"RAG News for {ticker}: {len(news)} items")
    for article in news:
        print(f"- {article['title']} ({article['published_at']})")
