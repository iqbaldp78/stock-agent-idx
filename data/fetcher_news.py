"""
Data Fetcher — News
Mengambil berita terkait ticker saham dari API berita eksternal.

Fungsi yang disediakan:
- fetch_news(ticker: str, limit: int = 10) -> list[dict]
"""

import os
import httpx
from datetime import datetime

NEWS_API_URL = "https://newsapi.org/v2/everything"
NEWS_API_KEY = os.getenv("NEWS_API_KEY")

def fetch_news(ticker: str, limit: int = 10) -> list[dict]:
    """
    Mengambil berita terkait ticker saham dari API berita eksternal.
    
    Args:
        ticker (str): Ticker saham (contoh: "BBCA").
        limit (int): Jumlah maksimum berita yang diambil.
    
    Returns:
        list[dict]: Daftar berita dengan informasi seperti judul, deskripsi, dan tanggal publikasi.
    """
    if not NEWS_API_KEY:
        raise ValueError("NEWS_API_KEY tidak diset di environment variables.")
    
    params = {
        "q": ticker,
        "apiKey": NEWS_API_KEY,
        "pageSize": limit,
        "sortBy": "publishedAt",
        "language": "id",
    }
    
    try:
        response = httpx.get(NEWS_API_URL, params=params, timeout=10.0)
        response.raise_for_status()
        articles = response.json().get("articles", [])
        return [
            {
                "title": article.get("title"),
                "description": article.get("description"),
                "published_at": article.get("publishedAt"),
                "source": article.get("source", {}).get("name"),
                "url": article.get("url"),
            }
            for article in articles
        ]
    except httpx.RequestError as e:
        raise RuntimeError(f"Error saat mengambil berita: {e}")
    except httpx.HTTPStatusError as e:
        raise RuntimeError(f"HTTP error saat mengambil berita: {e.response.status_code}")

if __name__ == "__main__":
    # Contoh penggunaan
    ticker = "BBCA"
    news = fetch_news(ticker, limit=5)
    for article in news:
        print(f"- {article['title']} ({article['published_at']})")
