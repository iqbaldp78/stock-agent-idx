"""
Stock Agent IDX — Streamlit Dashboard (Full)
Phase 5: Top Picks, Bandarmologi Detail, Performance Tracker, On-demand trigger.
"""
import streamlit as st
import psycopg2
import psycopg2.extras
import os
import json
import logging
from datetime import date, datetime, timedelta

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

st.set_page_config(
    page_title="Stock Agent IDX",
    page_icon="🤖",
    layout="wide",
)


# === Database Helper ===

def get_db_conn():
    return psycopg2.connect(
        dbname=os.getenv("POSTGRES_DB", "stockagent"),
        user=os.getenv("POSTGRES_USER", "stockuser"),
        password=os.getenv("POSTGRES_PASSWORD", "stockpassword"),
        host=os.getenv("POSTGRES_HOST", "postgres"),
        port=os.getenv("POSTGRES_PORT", "5432"),
    )


def query_db(sql, params=None):
    try:
        conn = get_db_conn()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(sql, params)
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return rows
    except Exception as e:
        logger.error(f"DB query error: {e}")
        return []


# === Sidebar ===

st.sidebar.title("🤖 Stock Agent IDX")
page = st.sidebar.radio(
    "Navigation",
    ["📈 Top Picks", "🔍 Bandarmologi", "📊 Performance", "⚙️ Settings"],
)

st.sidebar.divider()

# On-demand trigger
if st.sidebar.button("▶️ Run Analysis Now", type="primary"):
    with st.sidebar.status("Running analysis...", expanded=True):
        try:
            from graph.workflow import run_full_analysis
            from db.tracker import save_full_result
            from config import get_universe

            st.write("🔄 Filtering universe...")
            result = run_full_analysis()
            st.write(f"✅ Analyzed {len(result.get('composites', {}))} tickers")
            st.write(f"🏆 {len(result.get('top_picks', []))} top picks selected")

            save_full_result(result)
            st.write("💾 Saved to database")

            # Store in session for immediate display
            st.session_state["last_result"] = result
            st.session_state["last_run"] = datetime.now()
        except Exception as e:
            st.error(f"Error: {e}")
            logger.exception("Analysis failed")

st.sidebar.divider()

# Last run info
last_run = st.session_state.get("last_run")
if last_run:
    st.sidebar.caption(f"Last run: {last_run.strftime('%d %b %Y, %H:%M WIB')}")


# === PAGE: Top Picks ===

if page == "📈 Top Picks":
    st.title("📈 TOP PICKS")

    # Get latest signals from DB
    signals = query_db("""
        SELECT * FROM signals
        WHERE run_date = (SELECT MAX(run_date) FROM signals)
        ORDER BY rank
        LIMIT 5
    """)

    # Also check session state for fresh results
    last_result = st.session_state.get("last_result", {})
    top_picks_live = last_result.get("top_picks", [])

    if top_picks_live:
        # Show live results
        report = last_result.get("final_report", {})
        st.caption(f"Generated: {report.get('generated_at', 'N/A')}")
        st.info(f"🌐 Market: {report.get('market_condition', 'N/A')}")

        for pick in top_picks_live:
            ticker = pick["ticker"]
            rank = pick["rank"]
            conviction = pick.get("conviction", "N/A")
            conv_icon = "✅" if conviction == "HIGH" else "⚠️" if conviction == "MEDIUM" else "❓"

            with st.container(border=True):
                col1, col2, col3 = st.columns([1, 3, 2])

                with col1:
                    st.markdown(f"### #{rank}")
                    st.markdown(f"## {ticker}")

                with col2:
                    score = pick.get("final_score", pick.get("composite_score", 0))
                    st.progress(min(score / 10, 1.0))
                    st.markdown(f"**{score:.2f}/10** — Conviction: {conv_icon} {conviction}")

                    # Entry info
                    entry = pick.get("entry_zone", "N/A")
                    max_e = pick.get("max_entry", "N/A")
                    st.markdown(f"🎯 Entry Ideal: **{entry}** | Max: **{max_e}**")

                    # Targets
                    t1 = pick.get("target_1", "N/A")
                    sl = pick.get("stop_loss", "N/A")
                    rr = pick.get("risk_reward", "N/A")
                    st.markdown(f"Target: **{t1}** | SL: **{sl}** | R/R: **{rr}**")

                with col3:
                    # Bandar signal
                    signal = pick.get("bandarm_signal", "N/A")
                    brokers = pick.get("broker_to_watch", [])
                    st.markdown(f"⚡ **{signal}**")
                    if brokers:
                        st.caption(f"Broker: {', '.join(brokers[:2])}")

                    # Thesis
                    thesis = pick.get("thesis", "")
                    if thesis:
                        st.caption(thesis[:150])

        # Watchlist & Avoid
        col_w, col_a = st.columns(2)
        with col_w:
            watchlist = report.get("watchlist", [])
            if watchlist:
                st.markdown(f"👀 **Watchlist:** {', '.join(watchlist)}")
        with col_a:
            avoid = report.get("avoid", [])
            if avoid:
                st.warning(f"⚠️ Hindari: {'; '.join(avoid[:2])}")

    elif signals:
        # Show from database
        run_date = signals[0]["run_date"]
        st.caption(f"Data from: {run_date}")

        for sig in signals:
            with st.container(border=True):
                col1, col2, col3 = st.columns([1, 3, 2])

                with col1:
                    st.markdown(f"### #{sig['rank']}")
                    st.markdown(f"## {sig['ticker']}")

                with col2:
                    score = float(sig.get("composite_score", 0) or 0)
                    st.progress(min(score / 10, 1.0))
                    st.markdown(f"**{score:.2f}/10** — Conviction: {sig.get('conviction', 'N/A')}")

                    entry_l = sig.get("entry_low")
                    entry_h = sig.get("entry_high")
                    if entry_l and entry_h:
                        st.markdown(f"🎯 Entry: **{entry_l:,.0f}–{entry_h:,.0f}**")

                    t1 = sig.get("target_1")
                    sl = sig.get("stop_loss")
                    t1_str = f"{t1:,.0f}" if t1 else "N/A"
                    sl_str = f"{sl:,.0f}" if sl else "N/A"
                    st.markdown(
                        f"Target: **{t1_str}** | SL: **{sl_str}**"
                    )

                with col3:
                    st.markdown(f"⚡ Mode: **{sig.get('weight_mode', 'N/A')}**")
                    broker = sig.get("broker_utama", "")
                    if broker:
                        st.caption(f"Broker: {broker}")
                    thesis = sig.get("thesis", "")
                    if thesis:
                        st.caption(thesis[:120])
    else:
        st.info("Belum ada data. Klik **Run Analysis Now** di sidebar untuk memulai.")


# === PAGE: Bandarmologi ===

elif page == "🔍 Bandarmologi":
    st.title("🔍 BANDARMOLOGI")

    # Ticker selector
    from config import get_universe
    universe = get_universe()
    selected_ticker = st.selectbox("Pilih Saham", universe)

    if selected_ticker:
        tab7, tab30 = st.tabs(["📅 7 Hari", "📅 1 Bulan"])

        # Get bandarm data
        from agents.bandarmologi import analyze as bandarm_analyze

        with st.spinner(f"Analyzing {selected_ticker}..."):
            try:
                result = bandarm_analyze(selected_ticker)
            except Exception as e:
                st.error(f"Error: {e}")
                result = {}

        if result:
            # Summary metrics
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Signal", result.get("signal", "N/A"))
            with col2:
                st.metric("Score", f"{result.get('score', 0)}/10")
            with col3:
                price_analysis = result.get("price_analysis", {})
                cp = price_analysis.get("current_price")
                st.metric("Current Price", f"{cp:,}" if cp else "N/A")
            with col4:
                entry_status = price_analysis.get("entry_status_1m", "N/A")
                st.metric("Entry Status", entry_status[:20] if entry_status else "N/A")

            st.divider()

            with tab7:
                st.subheader("📊 Window 7 Hari")
                w7 = result.get("window_7d", {})

                if isinstance(w7, dict):
                    st.markdown(f"**Period:** {w7.get('period', 'N/A')}")
                    st.markdown(f"**Assessment:** {w7.get('assessment', 'N/A')}")

                    # Top accumulators
                    accumulators = w7.get("top_accumulators", [])
                    if accumulators:
                        st.markdown("**Top Accumulators:**")
                        for acc in accumulators[:5]:
                            if isinstance(acc, dict):
                                st.markdown(
                                    f"- **{acc.get('broker', 'N/A')}** ({acc.get('broker_name', '')}) — "
                                    f"Lot: {acc.get('total_buy_lot', 0):,} | "
                                    f"Avg: {acc.get('avg_price', 0):,.0f} | "
                                    f"Days: {acc.get('active_days', 'N/A')}"
                                )

                    foreign = w7.get("foreign_net_7d", "N/A")
                    if foreign:
                        st.markdown(f"🌍 **Foreign Net 7D:** {foreign}")

            with tab30:
                st.subheader("📊 Window 1 Bulan")
                w1m = result.get("window_1m", {})

                if isinstance(w1m, dict):
                    st.markdown(f"**Period:** {w1m.get('period', 'N/A')}")
                    st.markdown(f"**Assessment:** {w1m.get('assessment', 'N/A')}")

                    accumulators = w1m.get("top_accumulators", [])
                    if accumulators:
                        st.markdown("**Top Accumulators:**")
                        for acc in accumulators[:5]:
                            if isinstance(acc, dict):
                                st.markdown(
                                    f"- **{acc.get('broker', 'N/A')}** ({acc.get('broker_name', '')}) — "
                                    f"Avg: {acc.get('avg_price_1m', 0):,.0f} | "
                                    f"Days: {acc.get('active_days', 'N/A')}"
                                )

                    foreign = w1m.get("foreign_net_1m", "N/A")
                    if foreign:
                        st.markdown(f"🌍 **Foreign Net 1M:** {foreign}")

            # Price Analysis
            st.divider()
            st.subheader("💡 Entry Analysis")

            pa = result.get("price_analysis", {})
            if pa:
                col1, col2, col3 = st.columns(3)
                with col1:
                    avg7 = pa.get("bandar_avg_7d")
                    st.metric("Avg 7 Hari", f"Rp {avg7:,.0f}" if avg7 else "N/A")
                with col2:
                    avg1m = pa.get("bandar_avg_1m")
                    st.metric("Avg 1 Bulan (True Cost)", f"Rp {avg1m:,.0f}" if avg1m else "N/A")
                with col3:
                    cp = pa.get("current_price")
                    st.metric("Harga Sekarang", f"Rp {cp:,.0f}" if cp else "N/A")

                st.markdown(f"📏 Jarak dari avg 7H: **{pa.get('distance_from_7d', 'N/A')}**")
                st.markdown(f"📏 Jarak dari avg 1M: **{pa.get('distance_from_1m', 'N/A')}**")
                st.success(f"🎯 Entry Ideal: **{pa.get('ideal_entry_zone', 'N/A')}** | Max Entry: **{pa.get('max_entry', 'N/A')}**")

                entry_status = pa.get("entry_status_1m", "")
                if "IDEAL" in entry_status:
                    st.success(entry_status)
                elif "ACCEPTABLE" in entry_status:
                    st.info(entry_status)
                elif "CAUTION" in entry_status:
                    st.warning(entry_status)
                elif "AVOID" in entry_status:
                    st.error(entry_status)


# === PAGE: Performance ===

elif page == "📊 Performance":
    st.title("📊 PERFORMANCE TRACKER")

    # Get performance data
    perf_data = query_db("""
        SELECT p.*, s.ticker, s.signal, s.conviction, s.run_date as signal_date
        FROM performance p
        JOIN signals s ON p.signal_id = s.id
        ORDER BY p.check_date DESC
        LIMIT 50
    """)

    if perf_data:
        # Summary stats
        total = len(perf_data)
        hits = sum(1 for p in perf_data if (p.get("result") or "").startswith("HIT_TARGET"))
        losses = sum(1 for p in perf_data if p.get("result") == "HIT_SL")
        opens = sum(1 for p in perf_data if p.get("result") == "OPEN")

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            win_rate = (hits / (hits + losses) * 100) if (hits + losses) > 0 else 0
            st.metric("Win Rate", f"{win_rate:.0f}%")
        with col2:
            st.metric("Profitable", f"{hits} ✅")
        with col3:
            st.metric("Loss", f"{losses} ❌")
        with col4:
            st.metric("Open", f"{opens} 🔄")

        st.divider()

        # Recent signals table
        st.subheader("Recent Signals")
        for p in perf_data[:20]:
            result_icon = "✅" if "HIT_TARGET" in (p.get("result") or "") else "❌" if p.get("result") == "HIT_SL" else "🔄"
            ret = p.get("return_pct", 0) or 0
            st.markdown(
                f"{result_icon} **{p['ticker']}** — {p.get('result', 'OPEN')} "
                f"| Return: {float(ret):+.1f}% | Date: {p.get('check_date', 'N/A')}"
            )
    else:
        # Show agent scores instead
        scores = query_db("""
            SELECT run_date, ticker, composite_score, weight_mode,
                   fundamental_score, technical_score, bandarm_score
            FROM agent_scores
            ORDER BY run_date DESC, composite_score DESC
            LIMIT 30
        """)

        if scores:
            st.subheader("Latest Agent Scores")
            for s in scores:
                st.markdown(
                    f"**{s['ticker']}** — Composite: {s.get('composite_score', 0)} "
                    f"(B:{s.get('bandarm_score', 0)} T:{s.get('technical_score', 0)} "
                    f"F:{s.get('fundamental_score', 0)}) [{s.get('weight_mode', '')}]"
                )
        else:
            st.info("Belum ada data performance. Run analysis untuk menghasilkan signal terlebih dahulu.")

    # Agent accuracy section
    st.divider()
    st.subheader("Agent Accuracy")
    st.caption("Agent accuracy akan ditampilkan setelah ada cukup data performance.")


# === PAGE: Settings ===

elif page == "⚙️ Settings":
    st.title("⚙️ Settings")

    # Custom watchlist
    st.subheader("Custom Watchlist")
    custom_input = st.text_area(
        "Tambahkan ticker (satu per baris):",
        placeholder="BRIS\nAMRT\nMDKA",
        height=100,
    )

    if st.button("Save Watchlist"):
        tickers = [t.strip().upper() for t in custom_input.split("\n") if t.strip()]
        if tickers:
            st.session_state["custom_watchlist"] = tickers
            st.success(f"Saved {len(tickers)} tickers: {', '.join(tickers)}")

    st.divider()

    # System status
    st.subheader("📡 System Status")

    col1, col2, col3 = st.columns(3)
    with col1:
        try:
            conn = get_db_conn()
            conn.close()
            st.metric("Database", "Connected ✅")
        except Exception:
            st.metric("Database", "Disconnected ❌")

    with col2:
        gemini_key = os.getenv("GEMINI_API_KEY", "")
        has_gemini = gemini_key and gemini_key != "your_gemini_key_here"
        st.metric("Gemini API", "Ready ✅" if has_gemini else "Not configured ⚠️")

    with col3:
        anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")
        has_anthropic = anthropic_key and anthropic_key != "your_claude_key_here"
        st.metric("Claude API", "Ready ✅" if has_anthropic else "Not configured ⚠️")

    st.divider()

    # DB Stats
    st.subheader("Database Stats")
    stats = query_db("""
        SELECT
            (SELECT COUNT(*) FROM agent_scores) as total_scores,
            (SELECT COUNT(*) FROM debate_logs) as total_debates,
            (SELECT COUNT(*) FROM signals) as total_signals,
            (SELECT COUNT(*) FROM performance) as total_perf
    """)
    if stats:
        s = stats[0]
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Agent Scores", s.get("total_scores", 0))
        with col2:
            st.metric("Debate Logs", s.get("total_debates", 0))
        with col3:
            st.metric("Signals", s.get("total_signals", 0))
        with col4:
            st.metric("Performance", s.get("total_perf", 0))

    # Debate logs viewer
    st.divider()
    st.subheader("Recent Debate Logs")
    debates = query_db("""
        SELECT run_date, ticker, round, agent, argument, vote
        FROM debate_logs
        ORDER BY run_date DESC, ticker, round, agent
        LIMIT 20
    """)
    if debates:
        for d in debates:
            vote_icon = "🟢" if d["vote"] == "BUY" else "🔴" if d["vote"] == "SELL" else "⚪"
            st.markdown(
                f"{vote_icon} R{d['round']} | **{d['agent']}** → {d['ticker']}: {d['argument']}"
            )
    else:
        st.caption("Belum ada log debate.")

st.divider()
st.caption("Stock Agent IDX v0.1.0 — Phase 0 Setup")
