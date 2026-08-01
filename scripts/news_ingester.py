import os
import sys
# Ensure app root is in sys.path so we can import from data.fetcher_stockbit
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import json
import logging
import requests
import psycopg2
from data.fetcher_stockbit import (
    _get_api_key,
    _retry_on_rate_limit,
    refresh_stockbit_token,
    fetch_report_notifications,
    fetch_post_detail,
)
import httpx

logger = logging.getLogger(__name__)

# Constants for router API & Vector DB
ROUTER_CHAT_URL = "https://router.hamboo.me/v1/chat/completions"
ROUTER_EMBED_URL = "https://router.hamboo.me/v1/embeddings"
DB_URI = os.getenv("VECTOR_DB_URI", "postgresql://vectoruser:vectorpassword@vector_postgres:5432/vectoragent")


def get_db_connection():
    try:
        return psycopg2.connect(DB_URI)
    except Exception as e:
        # Fallback to localhost:5122 for direct host execution outside container
        if "vector_postgres" in DB_URI:
            fallback_uri = DB_URI.replace("vector_postgres:5432", "localhost:5122")
            return psycopg2.connect(fallback_uri)
        raise e


@_retry_on_rate_limit(max_attempts=3, base_delay=1.0)
def fetch_news_stream(limit: int = 10):
    api_key = _get_api_key()
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
    
    with httpx.Client(timeout=15.0) as client:
        response = client.post(url, headers=headers)
        response.raise_for_status()
        return response.json()


def analyze_and_embed(content: str, is_report: bool = False):
    # 1. Analyze text (summary, sentiment, tickers)
    if is_report:
        sys_prompt = (
            "You are a senior financial analyst analyzing corporate reports, research notes, and stock market announcements. "
            "Extract a brief summary, sentiment (Bullish/Bearish/Neutral), impact_scope (Macro/Micro), and a list of related stock tickers from the text. "
            "IMPORTANT: Be proactive. If a report shows earnings growth, dividend payout, beat-expectations, or positive expansion, tag as 'Bullish'. "
            "If it shows declining profits, lawsuits, or negative outlook, tag as 'Bearish'. "
            "Only tag 'Neutral' for strictly non-financial or purely factual, non-indicative events. "
            "Respond ONLY with a JSON object containing keys: 'summary', 'sentiment', 'impact_scope', 'tickers'."
        )
    else:
        sys_prompt = (
            "You are a financial news analyst. Extract a brief summary, sentiment (Bullish/Bearish/Neutral), impact_scope (Macro/Micro), and a list of related stock tickers from the text. "
            "IMPORTANT: Be proactive. If a report shows earnings growth, beat-expectations, or positive expansion, tag as 'Bullish'. "
            "If it shows declining profits, lawsuits, or negative outlook, tag as 'Bearish'. "
            "Only tag 'Neutral' for strictly non-financial or purely factual, non-indicative events. "
            "Respond ONLY with a JSON object containing keys: 'summary', 'sentiment', 'impact_scope', 'tickers'."
        )

    chat_payload = {
        "model": "LLM-stock-agent",
        "messages": [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": content}
        ],
        "stream": False
    }

    try:
        api_key = os.getenv("NINEROUTER_API_KEY", "")
        headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        res = requests.post(ROUTER_CHAT_URL, json=chat_payload, headers=headers, timeout=15)
        res.raise_for_status()
        
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

        if analysis_str.startswith("```json"):
            analysis_str = analysis_str[7:-3].strip()
        elif analysis_str.startswith("```"):
            analysis_str = analysis_str[3:-3].strip()
            
        analysis = json.loads(analysis_str)
    except Exception as e:
        logger.error(f"Failed to analyze text: {e}")
        analysis = {"summary": content[:300], "sentiment": "Neutral", "impact_scope": "Micro", "tickers": []}

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
        embedding = [0.0] * 3072  # Match dimension for gemini-embedding-2-preview
        
    return analysis, embedding


def save_to_db(stream_id: int, content: str, analysis: dict, embedding: list, doc_type: str = "news"):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("""
            INSERT INTO news_signals 
            (stream_id, content, summary, sentiment, impact_scope, tickers, embedding, doc_type)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (stream_id) DO NOTHING
        """, (
            stream_id, 
            content, 
            analysis.get("summary"), 
            analysis.get("sentiment"), 
            analysis.get("impact_scope"), 
            json.dumps(analysis.get("tickers", [])),
            embedding,
            doc_type
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
        conn = get_db_connection()
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


def run_news_ingester(limit: int = 50):
    logger.info("Fetching news stream...")
    try:
        data = fetch_news_stream(limit)
        items = data.get("data", {}).get("stream", [])
    except Exception as e:
        logger.error(f"Failed to fetch news stream: {e}")
        return 0
        
    valid_items = [item for item in items[:limit] if item.get("stream_id") and item.get("content")]
    all_stream_ids = [item.get("stream_id") for item in valid_items]
    
    existing_ids = get_existing_stream_ids(all_stream_ids)
    if existing_ids:
        logger.info(f"[News] Found {len(existing_ids)} existing items in DB. Skipping them.")
        
    processed = 0
    for item in valid_items:
        stream_id = item.get("stream_id")
        content = item.get("content", "")
        
        if stream_id in existing_ids:
            continue
            
        logger.info(f"[News] Processing NEW stream_id: {stream_id}")
        analysis, embedding = analyze_and_embed(content, is_report=False)
        
        if save_to_db(stream_id, content, analysis, embedding, doc_type="news"):
            logger.info(f"[News] Successfully saved stream_id: {stream_id}")
            processed += 1
            
    logger.info(f"[News] Ingestion complete. Processed {processed} new news items.")
    return processed


def run_report_ingester(limit: int = 25):
    logger.info("Fetching report notifications...")
    try:
        res = fetch_report_notifications(limit=limit)
        notif_items = res.get("data", [])
    except Exception as e:
        logger.error(f"Failed to fetch report notifications: {e}")
        return 0

    if not notif_items:
        logger.info("[Report] No report notifications found.")
        return 0

    # Extract items and target stream_id / post_id
    valid_reports = []
    for item in notif_items:
        if not isinstance(item, dict):
            continue
        n_id = item.get("id") or item.get("notif_id")
        data_obj = item.get("data", {}) or {}
        if isinstance(data_obj, dict):
            post_id = data_obj.get("post_id") or data_obj.get("stream_id") or n_id
        else:
            post_id = n_id
        
        if post_id:
            try:
                numeric_id = int(post_id)
                valid_reports.append({
                    "stream_id": numeric_id,
                    "post_id": post_id,
                    "title": item.get("title") or item.get("subject") or "",
                    "message": item.get("message") or item.get("description") or "",
                    "notif_type": item.get("type") or "NOTIF_TYPE_NEW_REPORT"
                })
            except Exception:
                pass

    if not valid_reports:
        logger.info("[Report] No valid report IDs found.")
        return 0

    all_ids = [r["stream_id"] for r in valid_reports]
    existing_ids = get_existing_stream_ids(all_ids)
    if existing_ids:
        logger.info(f"[Report] Found {len(existing_ids)} existing report items in DB. Skipping.")

    processed = 0
    for rep in valid_reports:
        stream_id = rep["stream_id"]
        if stream_id in existing_ids:
            continue

        logger.info(f"[Report] Processing NEW report stream_id: {stream_id}")
        
        # Try fetching detail post for full report content
        detail_content = ""
        try:
            detail_res = fetch_post_detail(rep["post_id"])
            post_data = detail_res.get("data", {})
            if isinstance(post_data, dict):
                detail_content = post_data.get("content") or post_data.get("post", {}).get("content") or ""
        except Exception as e:
            logger.warning(f"[Report] Detail post fetch failed for post_id={rep['post_id']}: {e}. Fallback to snippet.")

        if not detail_content:
            detail_content = f"{rep['title']}: {rep['message']}".strip()

        # Prefix content with notification metadata context
        full_report_text = f"[{rep['notif_type']}] {rep['title']}\n{detail_content}"

        analysis, embedding = analyze_and_embed(full_report_text, is_report=True)

        if save_to_db(stream_id, full_report_text, analysis, embedding, doc_type="report"):
            logger.info(f"[Report] Successfully saved report stream_id: {stream_id}")
            processed += 1

    logger.info(f"[Report] Ingestion complete. Processed {processed} new report items.")
    return processed


def run(limit: int = 50):
    logger.info("=== START UNIFIED INGESTER (NEWS & REPORT) ===")
    p_news = run_news_ingester(limit)
    p_report = run_report_ingester(limit=25)
    logger.info(f"=== UNIFIED INGESTER COMPLETED: {p_news} news, {p_report} reports ===")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run(50)
