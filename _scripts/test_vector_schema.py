import os
import time
import pytest
import psycopg2

def wait_for_db(timeout=10):
    start = time.time()
    while time.time() - start < timeout:
        try:
            conn = psycopg2.connect("postgresql://vectoruser:vectorpassword@vector_postgres:5432/vectoragent")
            conn.close()
            return True
        except Exception:
            time.sleep(0.5)
    return False

def test_db_schema_exists():
    assert wait_for_db(), "Database not available"
    conn = psycopg2.connect("postgresql://vectoruser:vectorpassword@vector_postgres:5432/vectoragent")
    cur = conn.cursor()
    
    # Check extension
    cur.execute("SELECT extname FROM pg_extension WHERE extname = 'vector';")
    assert cur.fetchone() is not None, "vector extension not installed"
    
    # Check table
    cur.execute("""
        SELECT column_name, data_type, udt_name 
        FROM information_schema.columns 
        WHERE table_name = 'news_signals';
    """)
    cols = {row[0]: row[1] if row[1] != 'USER-DEFINED' else row[2] for row in cur.fetchall()}
    assert 'id' in cols
    assert 'embedding' in cols
    assert cols['embedding'] == 'vector'
    
    # Clean up test data if any
    conn.rollback()
    cur.close()
    conn.close()
