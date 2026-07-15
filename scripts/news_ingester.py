import os
import sys
# Ensure app root is in sys.path so we can import from data.fetcher_stockbit
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import json
import logging
import requests
import psycopg2
# from db.cache import get_cached_stock_info
from data.fetcher_stockbit import _retry_on_rate_limit, refresh_stockbit_token

logger = logging.getLogger(__name__)

# Constants for router API
ROUTER_CHAT_URL = "https://router.hamboo.me/v1/chat/completions"
ROUTER_EMBED_URL = "https://router.hamboo.me/v1/embeddings"
DB_URI = "postgresql://vectoruser:vectorpassword@vector_postgres:5432/vectoragent"

@_retry_on_rate_limit(max_attempts=3, base_delay=1.0)
def fetch_news_stream(limit: int = 10):
    api_key = os.getenv("STOCKBIT_API_KEY")
    if not api_key:
        api_key = refresh_stockbit_token()
        
    url = "https://exodus.stockbit.com/stream/v3/user/Stockbit"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Origin": "https://stockbit.com",
        "Referer": "https://stockbit.com/"
    }
    
    response = requests.post(url, headers=headers, data='')
    response.raise_for_status()
    return response.json()


def analyze_and_embed(content: str):
    # 1. Analyze text (summary, sentiment, tickers)
    chat_payload = {
        "model": "LLM-stock-agent",
        "messages": [
            {
                "role": "system",
                "content": "You are a financial news analyst. Extract a brief summary, sentiment (Bullish/Bearish/Neutral), impact_scope (Macro/Micro), and a list of related stock tickers from the text. Respond ONLY with a JSON object containing keys: 'summary', 'sentiment', 'impact_scope', 'tickers'."
            },
            {
                "role": "user",
                "content": content
            }
        ]
    }
    # Force non-streaming response
    chat_payload["stream"] = False
    try:
        api_key = os.getenv("NINEROUTER_API_KEY", "")
        headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        res = requests.post(ROUTER_CHAT_URL, json=chat_payload, headers=headers, timeout=10)
        res.raise_for_status()
        
        # Manually parse SSE format if the server ignores stream=False
        res_text = res.text
        if res_text.startswith("data:"):
            full_content = ""
            for line in res_text.splitlines():
                if line.startswith("data: ") and line.strip() != "data: [DONE]":
                    try:
                        chunk = json.loads(line[6:])
                        if chunk.get("choices") and chunk["choices"][0].get("delta"):
                            full_content += chunk["choices"][0]["delta"].get("content", "")
                    except Exception:
                        pass
            analysis_str = full_content
        else:
            analysis_str = res.json()["choices"][0]["message"]["content"]

        
        # Clean markdown formatting if present
        if analysis_str.startswith("```json"):
            analysis_str = analysis_str[7:-3].strip()
            
        analysis = json.loads(analysis_str)
    except Exception as e:
        logger.error(f"Failed to analyze text: {e}")
        analysis = {"summary": content, "sentiment": "Neutral", "impact_scope": "Micro", "tickers": []}

    # 2. Get embeddings for the summary
    embed_payload = {
        "model": "gemini/gemini-embedding-2-preview",
        "input": analysis.get("summary", content)
    }
    try:
        api_key = os.getenv("OPENAI_API_KEY", os.getenv("NINEROUTER_API_KEY", ""))
        headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        res = requests.post(ROUTER_EMBED_URL, json=embed_payload, headers=headers, timeout=10)
        res.raise_for_status()
        embedding = res.json()["data"][0]["embedding"]
    except Exception as e:
        logger.error(f"Failed to get embedding: {e}")
        embedding = [0.0] * 3072 # Match dimension for gemini-embedding-2-preview
        
    return analysis, embedding

def save_to_db(stream_id: int, content: str, analysis: dict, embedding: list):
    try:
        conn = psycopg2.connect(DB_URI)
        cur = conn.cursor()
        
        cur.execute("""
            INSERT INTO news_signals 
            (stream_id, content, summary, sentiment, impact_scope, tickers, embedding)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (stream_id) DO NOTHING
        """, (
            stream_id, 
            content, 
            analysis.get("summary"), 
            analysis.get("sentiment"), 
            analysis.get("impact_scope"), 
            json.dumps(analysis.get("tickers", [])),
            embedding
        ))
        
        inserted = cur.rowcount > 0
        conn.commit()
        cur.close()
        conn.close()
        return inserted
    except Exception as e:
        logger.error(f"Failed to save to db: {e}")
        return False

def get_existing_stream_ids(stream_ids: list) -> set:
    if not stream_ids:
        return set()
    try:
        conn = psycopg2.connect(DB_URI)
        cur = conn.cursor()
        format_strings = ','.join(['%s'] * len(stream_ids))
        cur.execute(f"SELECT stream_id FROM news_signals WHERE stream_id IN ({format_strings})", tuple(stream_ids))
        existing = {row[0] for row in cur.fetchall()}
        cur.close()
        conn.close()
        return existing
    except Exception as e:
        logger.error(f"Failed to check existing ids: {e}")
        return set()

def run(limit: int = 50):
    logger.info("Fetching news stream...")
    
    try:
        data = fetch_news_stream(limit)
        items = data.get("data", {}).get("stream", [])
    except Exception as e:
        logger.error(f"Failed to fetch news stream: {e}")
        return
        
    # Extract IDs to check
    valid_items = [item for item in items[:limit] if item.get("stream_id") and item.get("content")]
    all_stream_ids = [item.get("stream_id") for item in valid_items]
    
    # Check DB for existing IDs
    existing_ids = get_existing_stream_ids(all_stream_ids)
    if existing_ids:
        logger.info(f"Found {len(existing_ids)} existing news items in DB. Skipping them.")
        
    processed = 0
    for item in valid_items:
        stream_id = item.get("stream_id")
        content = item.get("content", "")
        
        # KEY LOGIC: SKIP IF ALREADY IN DB
        if stream_id in existing_ids:
            continue
            
        logger.info(f"Processing NEW stream_id: {stream_id}")
        analysis, embedding = analyze_and_embed(content)
        
        if save_to_db(stream_id, content, analysis, embedding):
            logger.info(f"Successfully saved stream_id: {stream_id}")
            processed += 1
            
    logger.info(f"Ingestion complete. Processed {processed} new items.")
if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    run(50)
