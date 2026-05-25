"""
Stock Agent IDX — Streamlit Dashboard
Phase 0: Minimal UI dengan database connection test.
"""
import streamlit as st
import psycopg2
import os

st.set_page_config(
    page_title="Stock Agent IDX",
    page_icon="🤖",
    layout="wide",
)

st.title("🤖 Stock Agent IDX")
st.caption("Multi-Agent AI System untuk Stock Picking Pasar Indonesia")

st.divider()


def check_db_connection():
    try:
        conn = psycopg2.connect(
            dbname=os.getenv("POSTGRES_DB", "stockagent"),
            user=os.getenv("POSTGRES_USER", "stockuser"),
            password=os.getenv("POSTGRES_PASSWORD", "stockpassword"),
            host=os.getenv("POSTGRES_HOST", "postgres"),
            port=os.getenv("POSTGRES_PORT", "5432"),
        )
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public'")
        table_count = cur.fetchone()[0]
        cur.close()
        conn.close()
        return True, table_count
    except Exception as e:
        return False, str(e)


# Status Section
st.subheader("📡 System Status")

col1, col2, col3 = st.columns(3)

with col1:
    db_ok, db_info = check_db_connection()
    if db_ok:
        st.metric("Database", "Connected ✅")
        st.caption(f"{db_info} tables detected")
    else:
        st.metric("Database", "Disconnected ❌")
        st.caption(f"Error: {db_info}")

with col2:
    gemini_key = os.getenv("GEMINI_API_KEY", "")
    has_gemini = gemini_key and gemini_key != "your_gemini_key_here"
    st.metric("Gemini API", "Ready ✅" if has_gemini else "Not configured ⚠️")

with col3:
    anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")
    has_anthropic = anthropic_key and anthropic_key != "your_claude_key_here"
    st.metric("Claude API", "Ready ✅" if has_anthropic else "Not configured ⚠️")

st.divider()

# Phase Status
st.subheader("📋 Implementation Progress")

phases = {
    "Phase 0 — Setup & Docker": "✅ Complete",
    "Phase 1 — Data Fetchers": "⬜ Not started",
    "Phase 2 — Filter & Scoring": "⬜ Not started",
    "Phase 3 — Multi-Agent Debate": "⬜ Not started",
    "Phase 4 — Investment Manager": "⬜ Not started",
    "Phase 5 — Full UI Dashboard": "⬜ Not started",
    "Phase 6 — Scheduler & Validation": "⬜ Not started",
}

for phase, phase_status in phases.items():
    st.text(f"  {phase_status}  {phase}")

st.divider()
st.caption("Stock Agent IDX v0.1.0 — Phase 0 Setup")
