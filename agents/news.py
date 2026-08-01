"""
Agent — News & Report Intelligence
Menganalisis berita dan laporan saham (RAG local) terkait ticker untuk sentimen dan relevansi.

Fungsi yang disediakan:
- analyze(ticker: str) -> dict
"""

from data.fetcher_news import fetch_news


def analyze(ticker: str) -> dict:
    """
    Menganalisis berita dan laporan untuk ticker saham dan menghasilkan skor berdasarkan sentimen RAG.
    
    Args:
        ticker (str): Ticker saham.
    
    Returns:
        dict: Hasil analisis berisi skor (0-10), ringkasan, dan daftar berita/laporan terkait.
    """
    try:
        items = fetch_news(ticker, limit=10)
        
        if not items:
            return {
                "ticker": ticker,
                "score": 5.0,  # Skor netral jika tidak ada berita/report
                "summary": "Tidak ada berita atau laporan relevan yang ditemukan.",
                "articles": [],
            }
        
        sentiment_score = 0.0
        total_weight = 0.0
        news_count = 0
        report_count = 0
        
        for item in items:
            doc_type = item.get("doc_type", "news")
            # Weight: reports receive higher weight (1.5x) than standard news
            weight = 1.5 if doc_type == "report" else 1.0
            total_weight += weight
            
            if doc_type == "report":
                report_count += 1
            else:
                news_count += 1
                
            sent_tag = str(item.get("sentiment", "NEUTRAL")).upper()
            
            if "BULLISH" in sent_tag or "POSITIF" in sent_tag:
                sentiment_score += 2.0 * weight
            elif "BEARISH" in sent_tag or "NEGATIF" in sent_tag:
                sentiment_score -= 2.0 * weight
            else:
                # Text keyword fallback analysis
                title = item.get("title", "").lower()
                desc = item.get("description", "").lower()
                
                pos_kw = ["naik", "laba", "optimis", "ekspansi", "deviden", "dividend", "tumbuh"]
                neg_kw = ["turun", "rugi", "pesimis", "masalah", "gugatan", "sanksi"]
                
                pos_hits = sum(1 for kw in pos_kw if kw in title or kw in desc)
                neg_hits = sum(1 for kw in neg_kw if kw in title or kw in desc)
                
                sentiment_score += (pos_hits - neg_hits) * weight

        # Normalize total score to range 0 - 10 (base 5.0)
        normalized_score = 5.0 + (sentiment_score / max(total_weight, 1.0)) * 2.5
        score = round(max(0.0, min(10.0, normalized_score)), 1)
        
        counts_str = []
        if news_count > 0:
            counts_str.append(f"{news_count} berita")
        if report_count > 0:
            counts_str.append(f"{report_count} report")
            
        summary = (
            f"Sentimen pasar ({', '.join(counts_str)}) untuk {ticker} "
            f"cenderung {'positif' if score > 6.0 else 'negatif' if score < 4.0 else 'netral'} (score: {score})."
        )
        
        return {
            "ticker": ticker,
            "score": score,
            "summary": summary,
            "articles": items,
        }
    
    except Exception as e:
        return {
            "ticker": ticker,
            "score": 5.0,
            "summary": f"Error saat menganalisis berita/laporan: {e}",
            "articles": [],
        }


if __name__ == "__main__":
    ticker = "BBCA"
    analysis_result = analyze(ticker)
    print(f"Hasil Analisis untuk {ticker}:")
    print(f"  Skor: {analysis_result['score']}")
    print(f"  Ringkasan: {analysis_result['summary']}")
    print("  Artikel/Report Terkait:")
    for article in analysis_result['articles'][:5]:
        print(f"    - {article['title']}")