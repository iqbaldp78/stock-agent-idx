import pytest
import psycopg2

def test_ingester_script_imports():
    # If the script successfully imports, syntax is basically fine
    try:
        import scripts.news_ingester
    except Exception as e:
        pytest.fail(f"Could not import news_ingester: {e}")

def test_ingester_db_connection():
    # Make sure we can connect
    conn = psycopg2.connect("postgresql://vectoruser:vectorpassword@vector_postgres:5432/vectoragent")
    conn.close()
