import os
import json
import logging
import psycopg2
import requests
from typing import List, Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

DB_URI = os.getenv("VECTOR_DB_URI", "postgresql://vectoruser:vectorpassword@vector_postgres:5432/vectoragent")
ROUTER_EMBED_URL = "https://router.hamboo.me/v1/embeddings"
EMBED_MODEL = "gemini/gemini-embedding-2-preview"

def _get_db_connection():
    try:
        return psycopg2.connect(DB_URI)
    except Exception as e:
        if "vector_postgres" in DB_URI:
            fallback_uri = DB_URI.replace("vector_postgres:5432", "localhost:5122")
            return psycopg2.connect(fallback_uri)
        raise e

def _get_embedding(text: str) -> Optional[List[float]]:
    """Gets 3072-dim embedding for a query string via 9router."""
    payload = {
        "model": EMBED_MODEL,
        "input": text
    }
    api_key = os.getenv("OPENAI_API_KEY", os.getenv("NINEROUTER_API_KEY", ""))
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    
    try:
        res = requests.post(ROUTER_EMBED_URL, json=payload, headers=headers, timeout=5)
        res.raise_for_status()
        return res.json()["data"][0]["embedding"]
    except Exception as e:
        logger.error(f"Error embedding query '{text[:30]}...': {e}")
        return None

def _execute_query(query: str, params: tuple = ()) -> List[Dict]:
    """Executes a SELECT query and returns rows as dictionaries."""
    try:
        with _get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                columns = [desc[0] for desc in cur.description]
                results = []
                for row in cur.fetchall():
                    results.append(dict(zip(columns, row)))
                return results
    except Exception as e:
        logger.error(f"Database query failed: {e}")
        return []

def search_by_ticker(ticker: str, limit: int = 10, doc_type: Optional[str] = None) -> List[Dict]:
    """Find latest news & reports specifically tagged with a ticker symbol."""
    if doc_type:
        query = """
            SELECT stream_id, content, summary, sentiment, sentiment_score, impact_scope, doc_type, created_at
            FROM news_signals 
            WHERE tickers ? %s AND doc_type = %s
            ORDER BY created_at DESC
            LIMIT %s;
        """
        return _execute_query(query, (ticker.upper(), doc_type, limit))
    else:
        query = """
            SELECT stream_id, content, summary, sentiment, sentiment_score, impact_scope, doc_type, created_at
            FROM news_signals 
            WHERE tickers ? %s
            ORDER BY created_at DESC
            LIMIT %s;
        """
        return _execute_query(query, (ticker.upper(), limit))

def search_by_vector(query_text: str, limit: int = 5, doc_type: Optional[str] = None) -> List[Dict]:
    """Find most semantically similar news & reports using cosine distance."""
    emb = _get_embedding(query_text)
    if not emb:
        return []
    
    vec_str = f"[{','.join(map(str, emb))}]"
    
    if doc_type:
        query = """
            SELECT stream_id, content, summary, sentiment, sentiment_score, impact_scope, doc_type, created_at,
                   1 - (embedding <=> %s::halfvec) as similarity
            FROM news_signals
            WHERE doc_type = %s
            ORDER BY embedding <=> %s::halfvec
            LIMIT %s;
        """
        return _execute_query(query, (vec_str, doc_type, vec_str, limit))
    else:
        query = """
            SELECT stream_id, content, summary, sentiment, sentiment_score, impact_scope, doc_type, created_at,
                   1 - (embedding <=> %s::halfvec) as similarity
            FROM news_signals
            ORDER BY embedding <=> %s::halfvec
            LIMIT %s;
        """
        return _execute_query(query, (vec_str, vec_str, limit))

def format_for_prompt(records: List[Dict]) -> str:
    """Formats retrieved DB rows into clean strings for LLM injection, highlighting research reports as key drivers."""
    if not records:
        return "No recent news or reports available."
        
    reports = [r for r in records if r.get("doc_type") == "report"]
    news = [r for r in records if r.get("doc_type") != "report"]
    
    sections = []
    if reports:
        lines = ["[KEY DRIVER — RESEARCH & COMPANY REPORTS]"]
        for r in reports:
            created_at = r.get("created_at")
            date_str = created_at.strftime("%Y-%m-%d %H:%M") if hasattr(created_at, "strftime") else str(created_at or "")
            sent = r.get("sentiment", "Neutral")
            score = r.get("sentiment_score", 5)
            if score is None: score = 5
            impact = r.get("impact_scope", "Unknown")
            summary = r.get("summary", "")
            lines.append(f"• [{date_str}] ({sent} {score}/10 | {impact}) - {summary}")
        sections.append("\n".join(lines))

    if news:
        lines = ["[NEWS HEADLINES]"]
        for r in news:
            created_at = r.get("created_at")
            date_str = created_at.strftime("%Y-%m-%d %H:%M") if hasattr(created_at, "strftime") else str(created_at or "")
            sent = r.get("sentiment", "Neutral")
            score = r.get("sentiment_score", 5)
            if score is None: score = 5
            impact = r.get("impact_scope", "Unknown")
            summary = r.get("summary", "")
            lines.append(f"• [{date_str}] ({sent} {score}/10 | {impact}) - {summary}")
        sections.append("\n".join(lines))

    return "\n\n".join(sections)

if __name__ == "__main__":
    print("Testing Ticker Search (MYOR):")
    myor_news = search_by_ticker("MYOR", limit=5)
    print(format_for_prompt(myor_news))
