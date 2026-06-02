"""
Agent — News
Menganalisis berita terkait ticker saham untuk sentimen dan relevansi.

Fungsi yang disediakan:
- analyze(ticker: str) -> dict
"""

from data.fetcher_news import fetch_news

def analyze(ticker: str) -> dict:
    """
    Menganalisis berita untuk ticker saham dan menghasilkan skor berdasarkan sentimen.
    
    Args:
        ticker (str): Ticker saham.
    
    Returns:
        dict: Hasil analisis berisi skor, ringkasan, dan berita terkait.
    """
    try:
        news_items = fetch_news(ticker, limit=10)
        
        if not news_items:
            return {
                "ticker": ticker,
                "score": 5,  # Skor netral jika tidak ada berita
                "summary": "Tidak ada berita relevan yang ditemukan.",
                "articles": [],
            }
        
        # Analisis sentimen sederhana (contoh)
        positive_keywords = ["naik", "laba", "optimis", "ekspansi"]
        negative_keywords = ["turun", "rugi", "pesimis", "masalah"]
        
        sentiment_score = 0
        for item in news_items:
            title = item.get("title", "").lower()
            description = item.get("description", "").lower()
            
            for keyword in positive_keywords:
                if keyword in title or keyword in description:
                    sentiment_score += 1
            
            for keyword in negative_keywords:
                if keyword in title or keyword in description:
                    sentiment_score -= 1
        
        # Normalisasi skor ke rentang 0-10
        if sentiment_score > 5:
            score = 10
        elif sentiment_score < -5:
            score = 0
        else:
            score = 5 + sentiment_score
        
        summary = f"Sentimen berita untuk {ticker} cenderung {'positif' if score > 5 else 'negatif' if score < 5 else 'netral'}."
        
        return {
            "ticker": ticker,
            "score": score,
            "summary": summary,
            "articles": news_items,
        }
    
    except Exception as e:
        return {
            "ticker": ticker,
            "score": 5,
            "summary": f"Error saat menganalisis berita: {e}",
            "articles": [],
        }

if __name__ == "__main__":
    # Contoh penggunaan
    ticker = "BBCA"
    analysis_result = analyze(ticker)
    print(f"Hasil Analisis untuk {ticker}:")
    print(f"  Skor: {analysis_result['score']}")
    print(f"  Ringkasan: {analysis_result['summary']}")
    print("  Artikel Terkait:")
    for article in analysis_result['articles'][:3]:
        print(f"    - {article['title']}")