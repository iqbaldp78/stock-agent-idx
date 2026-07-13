import os
import json
import logging
import psycopg2
import requests
from typing import List, Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

DB_URI = "postgresql://vectoruser:vectorpassword@vector_postgres:5432/vectoragent"
ROUTER_EMBED_URL = "https://router.hamboo.me/v1/embeddings"
EMBED_MODEL = "gemini/gemini-embedding-2-preview"

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
        with psycopg2.connect(DB_URI) as conn:
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

def search_by_ticker(ticker: str, limit: int = 5) -> List[Dict]:
    """Find latest news specifically tagged with a ticker symbol."""
    # The tickers column is JSONB storing a list of strings like ["MYOR", "BBCA"]
    query = """
        SELECT stream_id, content, summary, sentiment, impact_scope, created_at
        FROM news_signals 
        WHERE tickers ? %s
        ORDER BY created_at DESC
        LIMIT %s;
    """
    return _execute_query(query, (ticker.upper(), limit))

def search_by_vector(query_text: str, limit: int = 3) -> List[Dict]:
    """Find most semantically similar news using cosine distance."""
    emb = _get_embedding(query_text)
    if not emb:
        return []
    
    # Cast python list to pgvector literal format '[0.1, 0.2, ...]'
    vec_str = f"[{','.join(map(str, emb))}]"
    
    # <=> is the cosine distance operator for vector/halfvec
    query = """
        SELECT stream_id, content, summary, sentiment, impact_scope, created_at,
               1 - (embedding <=> %s::halfvec) as similarity
        FROM news_signals
        ORDER BY embedding <=> %s::halfvec
        LIMIT %s;
    """
    return _execute_query(query, (vec_str, vec_str, limit))

def format_for_prompt(records: List[Dict]) -> str:
    """Formats retrieved DB rows into a clean string for LLM injection."""
    if not records:
        return "No recent news available."
        
    lines = []
    for r in records:
        date_str = r.get("created_at", datetime.now()).strftime("%Y-%m-%d %H:%M")
        sent = r.get("sentiment", "Neutral")
        impact = r.get("impact_scope", "Unknown")
        summary = r.get("summary", "")
        lines.append(f"[{date_str}] ({sent} | {impact}) - {summary}")
        
    return "\n".join(lines)

if __name__ == "__main__":
    # Quick test when running the file directly
    print("Testing Ticker Search (MYOR):")
    myor_news = search_by_ticker("MYOR", limit=2)
    print(format_for_prompt(myor_news))
