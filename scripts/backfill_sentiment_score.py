#!/usr/bin/env python3
"""
scripts/backfill_sentiment_score.py
====================================
Backfill script to re-analyze existing news & report records in vector_postgres DB,
extracting full Stockbit AI summary objects and assigning granular sentiment_score (1-10).
"""

import json
import logging
import os
import sys
import time
import psycopg2

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from data.fetcher_stockbit import fetch_post_detail
from scripts.news_ingester import analyze_and_embed, get_db_connection

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("backfill_sentiment")


def run_backfill(batch_size: int = 50):
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT stream_id, content, doc_type, summary 
        FROM news_signals 
        WHERE sentiment_score IS NULL OR sentiment = 'PENDING' OR sentiment_score = 5
        ORDER BY created_at DESC;
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()

    total_records = len(rows)
    logger.info(f"Starting backfill sentiment score for {total_records} records...")

    if total_records == 0:
        logger.info("No records need backfill.")
        return

    processed = 0
    failed_items = []

    for idx, row in enumerate(rows, 1):
        stream_id, raw_content, doc_type, old_summary = row
        is_report = (doc_type == "report")
        logger.info(f"[{idx}/{total_records}] Processing stream_id: {stream_id} ({doc_type})...")

        full_text = raw_content
        if is_report:
            # Re-fetch post detail to get Stockbit AI summary object
            try:
                detail_res = fetch_post_detail(stream_id)
                post_data = detail_res.get("data", {})
                if isinstance(post_data, dict):
                    title = post_data.get("title", "")
                    content_text = post_data.get("content") or post_data.get("post", {}).get("content") or ""

                    summary_obj = post_data.get("summary") or {}
                    ai_parts = []
                    if isinstance(summary_obj, dict):
                        st_sum = summary_obj.get("summary") or ""
                        st_takeaway = summary_obj.get("key_takeaway") or ""
                        st_kp = summary_obj.get("key_points") or []
                        if st_sum:
                            ai_parts.append(f"Ringkasan Kinerja: {st_sum}")
                        if isinstance(st_kp, list) and st_kp:
                            ai_parts.append("Poin Kunci:\n- " + "\n- ".join(st_kp))
                        if st_takeaway:
                            ai_parts.append(f"Kesimpulan: {st_takeaway}")

                    ai_summary_text = "\n".join(ai_parts)
                    detail_content = f"{content_text}\n\n{ai_summary_text}".strip()
                    if not detail_content:
                        detail_content = title
                    full_text = f"[NOTIF_TYPE_NEW_REPORT] {title}\n{detail_content}"
            except Exception as e:
                logger.warning(f"Fetch detail post failed for stream_id={stream_id}: {e}")

        # Analyze with LLM
        analysis = None
        embedding = None
        for attempt in range(2):
            try:
                analysis, embedding = analyze_and_embed(full_text, is_report=is_report)
                break
            except Exception as e:
                logger.error(f"Attempt {attempt+1} failed for stream_id={stream_id}: {e}")
                time.sleep(2.0)

        if not analysis:
            logger.error(f"Failed to analyze stream_id: {stream_id}. Queueing for retry.")
            failed_items.append((stream_id, full_text, is_report))
            continue

        # Save update to DB
        score = analysis.get("sentiment_score", 5)
        sent = analysis.get("sentiment", "Neutral")
        summary_text = analysis.get("summary", "")
        tickers_json = json.dumps(analysis.get("tickers", []))
        impact = analysis.get("impact_scope", "Micro")

        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("""
                UPDATE news_signals 
                SET content=%s, summary=%s, sentiment=%s, sentiment_score=%s, impact_scope=%s, tickers=%s, embedding=%s 
                WHERE stream_id=%s;
            """, (full_text, summary_text, sent, score, impact, tickers_json, embedding, stream_id))
            conn.commit()
            cur.close()
            conn.close()
            processed += 1
            logger.info(f"[{idx}/{total_records}] Updated stream_id {stream_id} -> {sent} ({score}/10) | Tickers: {tickers_json}")
        except Exception as e:
            logger.error(f"DB update failed for stream_id={stream_id}: {e}")

    # Retry queue for failed items
    if failed_items:
        logger.info(f"Retrying {len(failed_items)} failed items...")
        for stream_id, full_text, is_report in failed_items:
            try:
                analysis, embedding = analyze_and_embed(full_text, is_report=is_report)
                score = analysis.get("sentiment_score", 5)
                sent = analysis.get("sentiment", "Neutral")
                summary_text = analysis.get("summary", "")
                tickers_json = json.dumps(analysis.get("tickers", []))
                impact = analysis.get("impact_scope", "Micro")

                conn = get_db_connection()
                cur = conn.cursor()
                cur.execute("""
                    UPDATE news_signals 
                    SET content=%s, summary=%s, sentiment=%s, sentiment_score=%s, impact_scope=%s, tickers=%s, embedding=%s 
                    WHERE stream_id=%s;
                """, (full_text, summary_text, sent, score, impact, tickers_json, embedding, stream_id))
                conn.commit()
                cur.close()
                conn.close()
                processed += 1
                logger.info(f"[Retry Success] Updated stream_id {stream_id} -> {sent} ({score}/10)")
            except Exception as e:
                logger.error(f"[Retry Failed] stream_id {stream_id}: {e}")

    logger.info(f"Backfill complete! Successfully processed {processed}/{total_records} records.")


if __name__ == "__main__":
    run_backfill()
