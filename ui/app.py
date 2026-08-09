"""
Stock Agent IDX — Streamlit Dashboard (Full)
Phase 5: Top Picks, Bandarmologi Detail, Performance Tracker, On-demand trigger.
"""
import sys
sys.path.insert(0, "/app")

import streamlit as st
import psycopg2
import psycopg2.extras
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
import subprocess
import signal

import os
import uuid
from ui.login import render_login_page, init_cookie_manager
from ui.konglo_play import render_konglo_play_page
import extra_streamlit_components as stx

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@st.cache_data(ttl=300)
def get_live_price(ticker: str):
    try:
        from data.fetcher_stockbit import get_current_price_stockbit
        return get_current_price_stockbit(ticker)
    except Exception as e:
        logger.error(f"Error fetching live price from Stockbit for {ticker}: {e}")
        return None

st.set_page_config(
    page_title="Stock Agent IDX",
    page_icon="🤖",
    layout="wide",
)

# === Premium UI Injection ===
# (Keeping all the CSS intact)
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap');

html, body, [class*="css"]  {
    font-family: 'Outfit', sans-serif !important;
}

/* Glassmorphism containers */
div[data-testid="stContainer"] {
    background: rgba(30, 32, 45, 0.4) !important;
    backdrop-filter: blur(12px) !important;
    -webkit-backdrop-filter: blur(12px) !important;
    border-radius: 16px !important;
    border: 1px solid rgba(255, 255, 255, 0.08) !important;
    box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.3) !important;
    transition: transform 0.3s ease, box-shadow 0.3s ease;
}
div[data-testid="stContainer"]:hover {
    transform: translateY(-2px);
    box-shadow: 0 12px 40px 0 rgba(0, 0, 0, 0.5) !important;
    border: 1px solid rgba(255, 255, 255, 0.15) !important;
}

/* Custom Buttons */
div.stButton > button {
    background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%) !important;
    color: white !important;
    border-radius: 8px !important;
    border: none !important;
    font-weight: 600 !important;
    padding: 0.5rem 1rem !important;
    transition: all 0.2s ease;
}
div.stButton > button:hover {
    background: linear-gradient(135deg, #60a5fa 0%, #3b82f6 100%) !important;
    transform: scale(1.02);
    box-shadow: 0 4px 15px rgba(37, 99, 235, 0.4) !important;
}

/* Metrics Styling */
[data-testid="stMetricValue"] {
    font-weight: 700 !important;
    background: -webkit-linear-gradient(45deg, #60a5fa, #a78bfa);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}

/* Sidebar styling */
[data-testid="stSidebar"] {
    background: rgba(20, 22, 35, 0.95) !important;
    border-right: 1px solid rgba(255, 255, 255, 0.05) !important;
}

/* Expander styling */
[data-testid="stExpander"] {
    border: 1px solid rgba(255, 255, 255, 0.1) !important;
    border-radius: 12px !important;
    background: rgba(30, 32, 45, 0.3) !important;
}
</style>
""", unsafe_allow_html=True)


# === Database Helper ===

def get_db_conn():
    return psycopg2.connect(
        dbname=os.getenv("POSTGRES_DB", "stockagent"),
        user=os.getenv("POSTGRES_USER", "stockuser"),
        password=os.getenv("POSTGRES_PASSWORD", "stockpassword"),
        host=os.getenv("POSTGRES_HOST", os.getenv("DB_HOST", "stock_postgres")),
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


def find_backtest_result_path():
    candidates = [
        Path("backtest_result.json"),
        Path("/app/backtest_result.json"),
        Path(__file__).resolve().parents[1] / "backtest_result.json",
    ]
    for path in candidates:
        if path.exists():
            return path
    return candidates[0]


def load_backtest_result(path=None):
    result_path = Path(path) if path else find_backtest_result_path()
    if not result_path.exists():
        return None, result_path, f"File tidak ditemukan: {result_path}"
    try:
        with result_path.open("r") as f:
            return json.load(f), result_path, None
    except Exception as e:
        return None, result_path, str(e)


# === Authentication Wrapper ===
cookie_manager = init_cookie_manager(key="main_cookie_mgr")
# Handle the race condition where the browser hasn't deleted the cookie yet after logout
# We must do this BEFORE handling logout_requested, to avoid clearing deleted_token prematurely.
raw_auth_token = cookie_manager.get("auth_token")
auth_token = raw_auth_token

if auth_token and auth_token == st.session_state.get('deleted_token'):
    auth_token = None
elif 'deleted_token' in st.session_state:
    # Clear the deleted token state once the token actually disappears or changes
    if not auth_token:
        del st.session_state['deleted_token']

if st.session_state.get('logout_requested'):
    if raw_auth_token:
        st.session_state['deleted_token'] = raw_auth_token
    # Using set with max_age=0 and a unique key guarantees the cookie is deleted across all paths
    # and bypasses Streamlit's component caching which ignores repeated identical component calls.
    cookie_manager.set("auth_token", "", max_age=0, key=str(uuid.uuid4()))
    st.session_state['authenticated'] = False
    del st.session_state['logout_requested']
    auth_token = None

if auth_token:
    st.session_state['authenticated'] = True
    st.session_state['username'] = auth_token

if not st.session_state.get('authenticated'):
    render_login_page(get_db_conn)
    st.stop()


# === Sidebar ===

st.sidebar.title("🤖 Stock Agent IDX")

if st.sidebar.button("Logout", use_container_width=True):
    st.session_state['logout_requested'] = True
    st.rerun()

st.sidebar.divider()

page = st.sidebar.radio(
    "Navigation",
    ["📈 Top Picks", "🔍 Screener", "💹 Trading Engine", "📊 Analytics", "🔍 Bandarmologi", "📈 IHSG Predictor", "🧪 Backtest", "🤖 ML Validation", "📊 Performance", "💼 Portfolio", "🌍 Universe", "🐋 Konglo Play", "⚙️ Settings"]
)

st.sidebar.divider()

@st.fragment(run_every="1s")
def render_analysis_status():
    if not st.session_state.get("analysis_running"):
        return

    pid = st.session_state.get("analysis_pid")
    is_alive = False
    if pid:
        try:
            os.kill(pid, 0)
            is_alive = True
            # Periksa apakah proses menjadi zombie (sudah selesai tapi belum di-reap)
            try:
                with open(f"/proc/{pid}/stat", "r") as f:
                    stat_line = f.read()
                    if len(stat_line.split()) >= 3 and stat_line.split()[2] == 'Z':
                        is_alive = False
            except Exception:
                pass
        except OSError:
            pass

    if is_alive:
        st.info(f"🔄 Analysis is running... (PID: {pid})")
        if st.button("🛑 Cancel Analysis", type="primary", use_container_width=True, key="cancel_analysis_btn"):
            try:
                os.killpg(os.getpgid(pid), signal.SIGTERM)
            except Exception as e:
                logger.error(f"Failed to kill process {pid}: {e}")
            st.session_state["analysis_running"] = False
            st.warning("Analysis cancelled.")
            st.rerun()
    else:
        st.session_state["analysis_running"] = False
        result_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "last_analysis_result.json")
        if os.path.exists(result_file):
            try:
                with open(result_file, 'r') as f:
                    result = json.load(f)
                st.session_state["last_result"] = result
                st.session_state["last_run"] = datetime.now()
                debate_log = result.get("debate_log", [])
                if debate_log:
                    st.session_state["last_debate_log"] = debate_log
                st.success("Analysis complete!")
            except Exception as e:
                logger.error(f"Failed to load analysis result: {e}")
                st.error("Analysis finished but failed to load results.")
        else:
            st.error("Analysis finished but no results file found. It may have crashed.")
        st.rerun()


# On-demand trigger
if not st.session_state.get("analysis_running"):
    if st.sidebar.button("▶️ Run Analysis Now", type="primary"):
        st.session_state["analysis_running"] = True
        
        # Start the process in background
        p = subprocess.Popen([sys.executable, "scripts/run_analysis_job.py"], preexec_fn=os.setsid)
        st.session_state["analysis_pid"] = p.pid
        st.rerun()
else:
    with st.sidebar:
        render_analysis_status()

st.sidebar.divider()

# Last run info
last_run = st.session_state.get("last_run")
if last_run:
    st.sidebar.caption(f"Last run: {last_run.strftime('%d %b %Y, %H:%M WIB')}")


# === PAGE: Top Picks ===

if page == "📈 Top Picks":
    st.title("📈 TOP PICKS")

    def render_signals_list(signals):
        if not signals:
            return
        # Show from database
        run_date = signals[0]["run_date"]
        if isinstance(run_date, datetime):
            display_rd = (run_date + timedelta(hours=7)).strftime("%d %b %Y, %H:%M WIB")
        elif isinstance(run_date, str):
            try:
                parsed = datetime.strptime(run_date[:19], "%Y-%m-%d %H:%M:%S")
                display_rd = (parsed + timedelta(hours=7)).strftime("%d %b %Y, %H:%M WIB")
            except:
                display_rd = run_date
        else:
            display_rd = str(run_date)
            
        st.caption(f"Data from: {display_rd}")
    
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
                    
                    entry_style = ""
                    try:
                        price_pred = sig.get("price_prediction") or {}
                        cp = price_pred.get("current_price")
                        if cp and isinstance(cp, (int, float)) and entry_l and entry_h:
                            el = float(entry_l)
                            eh = float(entry_h)
                            if cp < el * 0.995:
                                entry_style = " 🚀 *(Buy on Breakout)*"
                            elif cp > eh * 1.005:
                                entry_style = " 📉 *(Buy on Weakness)*"
                            else:
                                entry_style = " 🛒 *(Market Buy)*"
                    except Exception:
                        pass
    
                    if entry_l and entry_h:
                        st.markdown(f"🎯 Entry: **{entry_l:,.0f}–{entry_h:,.0f}**{entry_style}")
    
                    entry_reason = sig.get("entry_reasoning", "")
                    if entry_reason:
                        st.caption(f"💡 *{entry_reason}*")
    
                    t1 = sig.get("target_1")
                    sl = sig.get("stop_loss")
                    t1_str = f"{float(t1):,.0f}" if t1 else "N/A"
                    sl_str = f"{float(sl):,.0f}" if sl else "N/A"
                    st.markdown(
                        f"Target: **{t1_str}** | "
                        f"SL: **{sl_str}**"
                    )
    
                    # ML Swing (5-Day) Prediction from DB
                    ml_pred = sig.get("ml_prediction") or {}
                    if ml_pred:
                        price_pred_temp = sig.get("price_prediction") or {}
                        cp_live_temp = get_live_price(sig['ticker'])
                        cp_temp = cp_live_temp if cp_live_temp else price_pred_temp.get('current_price', 1)
                        day_5_temp = price_pred_temp.get("predictions", {}).get("day_5", {})
                        day_5_price_temp = day_5_temp.get("price", cp_temp)
                        
                        try:
                            pred_return = ((float(day_5_price_temp) - float(cp_temp)) / float(cp_temp)) * 100
                        except (ValueError, TypeError, ZeroDivisionError):
                            pred_return = 0.0
    
                        ml_signal = ml_pred.get("signal", "N/A")
                        ml_conf = ml_pred.get("confidence", "N/A")
    
                        if ml_signal == "STRONG BUY":
                            signal_color = "🟢"
                        elif ml_signal == "BUY":
                            signal_color = "🟡"
                        elif ml_signal == "AVOID":
                            signal_color = "🔴"
                        else:
                            signal_color = "⚪"
    
                        st.markdown(
                            f"🤖 **ML Forecast (T+5):** {signal_color} **{ml_signal}** "
                            f"| Return: **{float(pred_return):+.2f}%** | Confidence: {ml_conf}"
                        )
    
                    # Price Prediction from DB
                    price_pred = sig.get("price_prediction") or {}
                    if price_pred:
                        with st.expander("📊 **Price Prediction (1/3/5/7 hari ke depan)**", expanded=True):
                            cp_live = get_live_price(sig['ticker'])
                            cp = cp_live if cp_live else price_pred.get('current_price', 'N/A')
                            st.metric("💰 Harga Sekarang", f"Rp {cp:,.0f}" if isinstance(cp, (int, float)) else cp)
    
                            predictions = price_pred.get("predictions", {})
                            col_d1, col_d3, col_d5, col_d7 = st.columns(4)
                            for col, key in [(col_d1, "day_1"), (col_d3, "day_3"), (col_d5, "day_5"), (col_d7, "day_7")]:
                                if key in predictions:
                                    pred = predictions[key]
                                    pct = pred.get('pct_change', 'N/A')
                                    price = pred.get('price', 'N/A')
                                    pct_num = float(str(pct).replace('%', '').replace('+', '')) if isinstance(pct, str) and pct not in ('N/A', '') else (pct if isinstance(pct, (int, float)) else 0)
                                    with col:
                                        st.metric(
                                            key.replace('_', '+').upper(),
                                            f"Rp {int(price):,.0f}" if isinstance(price, (int, float)) else price,
                                            pct,
                                            delta_color="normal" if pct_num >= 0 else "inverse"
                                        )
    
                            st.divider()
                            reasoning = price_pred.get("reasoning", "")
                            if reasoning:
                                st.markdown("### 📝 Reasoning")
                                st.markdown(reasoning)
    
                            confidence = price_pred.get('confidence', 'N/A')
                            conf_color = "🟢" if confidence == "HIGH" else "🟡" if confidence == "MEDIUM" else "🔴"
                            st.markdown(f"{conf_color} **Confidence:** {confidence}")
    
                            drivers = price_pred.get("key_drivers", [])
                            if drivers:
                                st.markdown("### 📈 Key Drivers:")
                                for i, driver in enumerate(drivers, 1):
                                    st.markdown(f"{i}. {driver}")
    
                            risks = price_pred.get("risks", [])
                            if risks:
                                st.markdown("### ⚠️ Risks:")
                                for i, risk in enumerate(risks, 1):
                                    st.markdown(f"{i}. {risk}")
    
                with col3:
                    st.markdown(f"⚡ Mode: **{sig.get('weight_mode', 'N/A')}**")
                    broker = sig.get("broker_utama", "")
                    if broker:
                        st.caption(f"Broker: {broker}")
    
                    # Fundamental Fair Value (moved here for UI alignment)
                    fair_value = sig.get("fair_value")
                    if isinstance(fair_value, str):
                        import json
                        try:
                            fair_value = json.loads(fair_value)
                        except Exception:
                            fair_value = {}
                    elif not fair_value:
                        fair_value = {}
    
                    if fair_value and isinstance(fair_value, dict):
                        fv_base = fair_value.get("fair_value_base")
                        fv_low = fair_value.get("fair_value_low")
                        fv_high = fair_value.get("fair_value_high")
                        upside = fair_value.get("upside_pct")
                        label = fair_value.get("valuation_label", "N/A")
                        confidence = fair_value.get("confidence", "N/A")
    
                        if label in ("DEEP_UNDERVALUED", "UNDERVALUED"):
                            fv_icon = "🟢"
                        elif label in ("OVERVALUED", "EXPENSIVE"):
                            fv_icon = "🔴"
                        else:
                            fv_icon = "🟡"
    
                        fv_text = f"Rp {fv_base:,.0f}" if isinstance(fv_base, (int, float)) else "N/A"
                        upside_text = f"{upside:+.2f}%" if isinstance(upside, (int, float)) else "N/A"
                        st.markdown(f"💰 **Fair Value:** {fv_icon} **{fv_text}** | Upside: **{upside_text}** | {label} ({confidence})")
    
                        with st.expander(f"📐 Detail Fair Value {sig['ticker']}", expanded=False):
                            if fv_low and fv_high:
                                st.markdown(f"**Range:** Rp {fv_low:,.0f} – Rp {fv_high:,.0f}")
                            methods = fair_value.get("methods", {})
                            for method_name, method_data in methods.items():
                                if method_data.get("available"):
                                    fv = method_data.get("fair_value")
                                    st.markdown(f"- **{method_name}**: Rp {fv:,.0f}")
                            notes = fair_value.get("notes", [])
                            if notes:
                                st.caption(" | ".join(notes[:3]))
    
                    # Broker True Costs from DB
                    broker_true_costs = sig.get("broker_true_costs")
                    if isinstance(broker_true_costs, str):
                        import json
                        try:
                            broker_true_costs = json.loads(broker_true_costs)
                        except Exception:
                            broker_true_costs = {}
                    elif not broker_true_costs:
                        broker_true_costs = {}
                        
                    true_cost_rows = broker_true_costs.get("w1m") or broker_true_costs.get("w7") or []
                    if true_cost_rows:
                        with st.expander("🏦 True Cost Broker Akumulasi", expanded=False):
                            import pandas as pd
    
                            def format_value(val):
                                if val >= 1e12: return f"{val/1e12:.2f}T"
                                if val >= 1e9: return f"{val/1e9:.2f}B"
                                if val >= 1e6: return f"{val/1e6:.2f}M"
                                return f"{val:,.0f}"
    
                            def format_lot(lot):
                                if lot >= 1000: return f"{lot/1000:.1f}K"
                                return f"{lot:,.0f}"
    
                            rows = []
                            for b in true_cost_rows[:5]:
                                dist = b.get("distance_pct")
                                rows.append({
                                    "Broker": b.get("broker", ""),
                                    "True Cost": b.get("true_cost", 0),
                                    "Total Buy Lot": format_lot(b.get("total_buy_lot", 0)),
                                    "Total Buy Value": format_value(b.get("total_buy_value", 0)),
                                    "Harga vs Cost": f"{dist:+.2f}%" if isinstance(dist, (int, float)) else "N/A",
                                    "Active": b.get("active_days", ""),
                                })
                            st.dataframe(
                                pd.DataFrame(rows),
                                use_container_width=True,
                                hide_index=True,
                                column_config={
                                    "True Cost": st.column_config.NumberColumn(format="Rp %.0f"),
                                },
                            )
                            if broker_true_costs.get("w1m") and broker_true_costs.get("w7"):
                                st.caption("Menampilkan 1 bulan; 7 hari tersedia di halaman Bandarmologi.")
    
                    # Broker Distributors from DB
                    broker_distributors = sig.get("broker_distributors")
                    if isinstance(broker_distributors, str):
                        import json
                        try:
                            broker_distributors = json.loads(broker_distributors)
                        except Exception:
                            broker_distributors = {}
                    elif not broker_distributors:
                        broker_distributors = {}
                        
                    dist_rows = broker_distributors.get("w1m") or broker_distributors.get("w7") or []
                    if dist_rows:
                        with st.expander("📉 Avg Sell Distribusi", expanded=False):
                            import pandas as pd
    
                            def format_value(val):
                                if val >= 1e12: return f"{val/1e12:.2f}T"
                                if val >= 1e9: return f"{val/1e9:.2f}B"
                                if val >= 1e6: return f"{val/1e6:.2f}M"
                                return f"{val:,.0f}"
    
                            def format_lot(lot):
                                if lot >= 1000: return f"{lot/1000:.1f}K"
                                return f"{lot:,.0f}"
    
                            rows_d = []
                            for b in dist_rows[:5]:
                                dist = b.get("distance_pct")
                                rows_d.append({
                                    "Broker": b.get("broker", ""),
                                    "Avg Sell": b.get("avg_sell", 0),
                                    "Total Sell Lot": format_lot(b.get("total_sell_lot", 0)),
                                    "Total Sell Value": format_value(b.get("total_sell_value", 0)),
                                    "Harga vs Avg Sell": f"{dist:+.2f}%" if isinstance(dist, (int, float)) else "N/A",
                                    "Active": b.get("active_days", ""),
                                })
                            st.dataframe(
                                pd.DataFrame(rows_d),
                                use_container_width=True,
                                hide_index=True,
                                column_config={
                                    "Avg Sell": st.column_config.NumberColumn(format="Rp %.0f"),
                                },
                            )
                            if broker_distributors.get("w1m") and broker_distributors.get("w7"):
                                st.caption("Menampilkan 1 bulan; 7 hari tersedia di halaman Bandarmologi.")
    
                    thesis = sig.get("thesis", "")
                    if thesis:
                        with st.expander("📝 Investment Thesis", expanded=False):
                            st.markdown(thesis)
    
    

    tab_regular, tab_konglo = st.tabs(["📊 Regular Top Picks", "🐋 Konglo Play Picks"])

    with tab_regular:
        latest_meta_reg = query_db("""
            SELECT MAX(run_date) AS max_run_date
            FROM signals
            WHERE batch_id IS NOT NULL AND (is_konglo IS FALSE OR is_konglo IS NULL)
        """)
        latest_run_date_reg = latest_meta_reg[0]["max_run_date"] if latest_meta_reg else None
        
        latest_batch_reg = None
        if latest_run_date_reg is not None:
            latest_batch_res = query_db("""
                SELECT batch_id
                FROM signals
                WHERE run_date = %s
                AND batch_id IS NOT NULL AND (is_konglo IS FALSE OR is_konglo IS NULL)
                LIMIT 1
            """, (latest_run_date_reg,))
            latest_batch_reg = (latest_batch_res[0]["batch_id"] if latest_batch_res else None)
            
        signals_reg = []
        if latest_run_date_reg is not None:
            if latest_batch_reg:
                signals_reg = query_db("""
                    SELECT * FROM signals
                    WHERE batch_id = %s
                    AND (is_konglo IS FALSE OR is_konglo IS NULL)
                    AND rank IS NOT NULL
                    ORDER BY rank
                    LIMIT 3
                """, (latest_batch_reg,))
            else:
                signals_reg = query_db("""
                    SELECT * FROM signals
                    WHERE run_date = %s
                    AND (is_konglo IS FALSE OR is_konglo IS NULL)
                    AND rank IS NOT NULL
                    ORDER BY rank
                    LIMIT 3
                """, (latest_run_date_reg,))
                
        if signals_reg:
            render_signals_list(signals_reg)
        else:
            st.info("Belum ada Regular Picks. Silahkan jalankan analisis terlebih dahulu.")
            
    with tab_konglo:
        latest_meta_konglo = query_db("""
            SELECT MAX(run_date) AS max_run_date
            FROM signals
            WHERE batch_id IS NOT NULL AND is_konglo = TRUE
        """)
        latest_run_date_konglo = latest_meta_konglo[0]["max_run_date"] if latest_meta_konglo else None
        
        latest_batch_konglo = None
        if latest_run_date_konglo is not None:
            latest_batch_res = query_db("""
                SELECT batch_id
                FROM signals
                WHERE run_date = %s
                AND batch_id IS NOT NULL AND is_konglo = TRUE
                LIMIT 1
            """, (latest_run_date_konglo,))
            latest_batch_konglo = (latest_batch_res[0]["batch_id"] if latest_batch_res else None)
            
        signals_konglo = []
        if latest_run_date_konglo is not None:
            if latest_batch_konglo:
                signals_konglo = query_db("""
                    SELECT * FROM signals
                    WHERE batch_id = %s
                    AND is_konglo = TRUE
                    AND rank IS NOT NULL
                    ORDER BY rank
                    LIMIT 3
                """, (latest_batch_konglo,))
            else:
                signals_konglo = query_db("""
                    SELECT * FROM signals
                    WHERE run_date = %s
                    AND is_konglo = TRUE
                    AND rank IS NOT NULL
                    ORDER BY rank
                    LIMIT 3
                """, (latest_run_date_konglo,))
                
        if signals_konglo:
            render_signals_list(signals_konglo)
        else:
            st.info("👋 Belum ada data Konglo Picks. Silahkan jalankan 'Konglo Analysis' dari menu Konglo Play terlebih dahulu.")

# === PAGE: Screener ===
elif page == "🔍 Screener":
    st.title("🔍 STOCK SCREENER BEI")
    st.caption("Skrining saham IHSG berbasis Candlestick Pattern, HAKA Volume, Broker Accumulation, & Technical Breakout.")
    
    from services.screener_service import get_screener_data
    import pandas as pd
    
    col_type, col_univ, col_action = st.columns([2.5, 1.5, 1])
    
    with col_type:
        screener_type = st.selectbox(
            "Pilih Tipe Screener",
            [
                "🕯️ Candlestick Patterns (BEI Win-Rate)",
                "⚡ HAKA / Volume Spike",
                "🏛️ Broker Dominance (Akumulasi)",
                "📈 Technical Breakout (TradingView TA)",
                "💎 Deep Undervalued Gem",
                "🐋 Konglo Group Momentum",
                "🎯 Oversold Bounce (RSI < 35)"
            ]
        )
        
    with col_univ:
        universe_type = st.selectbox("Universe Saham", ["ALL", "LQ45", "KONGLO", "CUSTOM"])
        
    with col_action:
        st.write("")
        st.write("")
        run_scan = st.button("▶️ Scan Now", type="primary", use_container_width=True)
        
    with st.spinner("Mengambil hasil screening saham..."):
        data = get_screener_data(screener_type, universe_type, force_scan=run_scan)
        
    if not data:
        st.warning("⚠️ Tidak ada emiten yang memenuhi kriteria screener pada universe/tipe ini. Silahkan klik '▶️ Scan Now' untuk memperbarui data.")
    else:
        # Summary metrics
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("📊 Total Sinyal", len(data))
        
        if "candlestick" in screener_type.lower():
            bullish_count = len([x for x in data if "BULLISH" in str(x.get("signal", ""))])
            avg_wr = sum([x.get("win_rate", 50) for x in data]) / len(data) if data else 0
            m2.metric("🟢 Bullish Patterns", bullish_count)
            m3.metric("🎯 Avg Win-Rate", f"{avg_wr:.1f}%")
            m4.metric("🏆 Top Pick", data[0].get("ticker", "-") if data else "-")
        elif "haka" in screener_type.lower():
            super_haka = len([x for x in data if "SUPER" in str(x.get("status", ""))])
            max_vol = max([x.get("volume_multiplier", 0) for x in data], default=0)
            m2.metric("🚀 Super HAKA", super_haka)
            m3.metric("📈 Max Vol Multiplier", f"{max_vol:.2f}x")
            m4.metric("🏆 Highest Vol", data[0].get("ticker", "-") if data else "-")
        elif "broker" in screener_type.lower() or "dominance" in screener_type.lower():
            accum = len([x for x in data if x.get("accumulation_status") == "ACCUMULATION"])
            m2.metric("🏛️ Akumulasi Net Buy", accum)
            m3.metric("🌐 Foreign Net Buy", len([x for x in data if x.get("foreign_flow") == "NET BUY"]))
            m4.metric("🏆 Top Accumulation", data[0].get("ticker", "-") if data else "-")
        else:
            m2.metric("🟢 High Conviction", len(data))
            m3.metric("⚡ Status", "Active")
            m4.metric("🏆 Top Ticker", data[0].get("ticker", "-") if data else "-")

        st.divider()
        
        # Interactive DataFrame
        df_display = pd.DataFrame(data)
        st.dataframe(df_display, use_container_width=True, height=380)
        
        # Detail view per ticker
        st.subheader("🔍 Detail & Quick Analysis")
        selected_tick = st.selectbox("Pilih Saham untuk Detail Analyst View", [d.get("ticker") for d in data if isinstance(d, dict) and "ticker" in d])
        if selected_tick:
            item_detail = next((x for x in data if isinstance(x, dict) and x.get("ticker") == selected_tick), None)
            if item_detail:
                st.json(item_detail)

elif page == "💹 Trading Engine":
    st.title("💹 TRADING ENGINE")
    st.markdown("**Virtual Portfolio Validator** — Test trading strategy dengan modal virtual")
    
    # Import paper trading service
    try:
        from services.paper_trading import PaperTradingService
        pt_service = PaperTradingService()
    except ImportError as e:
        st.error(f"Trading Engine service tidak tersedia: {e}")
        st.stop()
    
    # --- WALLET SECTION ---
    st.header("💰 WALLET")
    col_topup, col_reset, col_summary = st.columns([2, 2, 8])
    
    with col_topup:
        with st.popover("Topup Modal"):
            amount = st.number_input(
                "Jumlah Topup (Rp)",
                min_value=10000000,
                max_value=1000000000,
                value=100000000,
                step=5000000,
                format="%d"
            )
            if st.button("💸 Topup", use_container_width=True):
                with st.spinner(f"Topup Rp {amount:,.0f}..."):
                    result = pt_service.topup(amount)
                    if result["status"] == "success":
                        st.success(result["message"])
                    else:
                        st.error(result["message"])
    
    with col_reset:
        if st.button("🔄 Reset Portfolio", use_container_width=True, type="secondary"):
            if st.checkbox("Konfirmasi reset semua trades"):
                result = pt_service.reset_wallet()
                st.success(result["message"])
    
    # Wallet summary
    with st.container(border=True):
        summary = pt_service.get_wallet_summary()
        
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            st.metric(
                "💵 Cash", 
                f"Rp {summary['cash']:,.0f}",
                help="Saldo cash tersedia untuk beli"
            )
        with col2:
            st.metric(
                "💼 Invested", 
                f"Rp {summary['total_invested']:,.0f}",
                help="Total dana yang sedang diinvestasikan di saham"
            )
        with col3:
            st.metric(
                "📊 Total Equity", 
                f"Rp {summary['total_equity']:,.0f}",
                f"{summary['total_return_pct']:+.2f}%"
            )
        with col4:
            st.metric(
                "📈 Realized P&L", 
                f"Rp {summary['realized_pnl']:,.0f}",
                help="Profit/loss dari trades yang sudah closed"
            )
        with col5:
            st.metric(
                "📊 Unrealized P&L", 
                f"Rp {summary['unrealized_pnl']:,.0f}",
                help="Profit/loss dari open positions"
            )
        
        # Progress bar for invested vs cash
        if summary['total_topup'] > 0:
            invest_pct = (summary['total_invested'] / summary['total_topup']) * 100
            st.progress(min(invest_pct / 100, 1.0), text=f"Invested: {invest_pct:.1f}%")
    
    # --- EQUITY CURVE ---
    st.header("📈 EQUITY CURVE")
    equity = pt_service.get_equity_history()
    
    if len(equity["points"]) > 1:
        import pandas as pd
        import plotly.graph_objects as go
        
        df_equity = pd.DataFrame(equity["points"])
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df_equity["date"],
            y=df_equity["equity"],
            mode="lines+markers",
            name="Total Equity",
            line=dict(color="#00d4aa", width=2),
            marker=dict(size=8),
            hovertemplate="<b>%{x}</b><br>Equity: Rp %{y:,.0f}<extra></extra>"
        ))
        
        # Add baseline (initial topup)
        fig.add_hline(
            y=equity["start_equity"],
            line_dash="dash",
            line_color="gray",
            annotation_text=f"Modal: Rp {equity['start_equity']:,.0f}"
        )
        
        fig.update_layout(
            title=f"Portfolio Growth: {equity['total_return_pct']:+.2f}%",
            xaxis_title="Date",
            yaxis_title="Equity (Rp)",
            height=300,
            margin=dict(l=0, r=0, t=40, b=0),
            hovermode="x unified"
        )
        
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Equity curve akan muncul setelah ada trades.")
    
    def _fetch_live_prices_for_open(tickers: list[str]) -> dict:
        prices = {}
        for ticker in tickers:
            try:
                p = get_live_price(ticker)
                if p is not None:
                    prices[ticker] = p
            except Exception:
                pass
        return prices
    
    # --- CHECK ACTUAL TP/SL ---
    st.header("🎯 CHECK ACTUAL TP/SL")
    st.caption("Cek harga live dan tutup otomatis posisi yang sudah kena TP/SL.")
    
    col_check, col_info = st.columns([2, 6])
    with col_check:
        if st.button("🔍 Cek TP/SL Sekarang", type="primary", use_container_width=True):
            try:
                summary_now = pt_service.get_wallet_summary(auto_check_tpsl=False)
                open_tickers = [p["ticker"] for p in summary_now.get("positions", [])]
                if not open_tickers:
                    st.info("Tidak ada open position untuk dicek.")
                else:
                    with st.spinner("Fetching live prices..."):
                        live_prices = _fetch_live_prices_for_open(open_tickers)
                    st.write("Live prices:", live_prices)
                    results = pt_service.check_tp_sl(current_prices=live_prices)
                    if results:
                        st.success(f"Auto-closed {len(results)} position(s). Refresh untuk lihat perubahan.")
                        st.rerun()
                    else:
                        st.success("Tidak ada posisi yang kena TP/SL.")
            except Exception as e:
                st.error(f"Check TP/SL failed: {e}")
    
    # --- QUICK BUY FROM TOP PICKS ---
    st.header("🎯 QUICK BUY dari Top Picks")
    
    # AUTO-EXECUTE ALL button
    col_auto_all, col_space = st.columns([2, 6])
    with col_auto_all:
        if st.button("⚡ INVEST SEMUA (15% each)", type="primary", use_container_width=True):
            with st.spinner("Executing all top picks..."):
                result = pt_service.auto_execute_all_top_picks(budget_pct_per_trade=0.15)
                if result["status"] == "success":
                    st.success(f"✅ {result['message']}")
                    st.rerun()
                elif result["status"] == "info":
                    st.info(result["message"])
                else:
                    st.error(result.get("message", "Unknown error"))
    
    # Get latest top picks
    try:
        signals = query_db("""
            SELECT * FROM signals
            WHERE run_date = (SELECT MAX(run_date) FROM signals WHERE is_konglo = FALSE)
            AND is_konglo = FALSE
            AND rank IS NOT NULL
            ORDER BY rank
            LIMIT 5
        """)
    except:
        signals = []
    
    if signals:
        for sig in signals:
            with st.container(border=True):
                col_info, col_buy, col_auto = st.columns([3, 3, 2])
                
                with col_info:
                    st.markdown(f"**{sig['ticker']}** — #{sig['rank']}")
                    entry_low = sig.get('entry_low') or 0
                    entry_high = sig.get('entry_high') or 0
                    tp1 = sig.get('target_1') or 0
                    sl = sig.get('stop_loss') or 0
                    st.markdown(f"Entry: Rp {float(entry_low):,.0f}–Rp {float(entry_high):,.0f}")
                    st.caption(f"TP: Rp {float(tp1):,.0f} | SL: Rp {float(sl):,.0f}")
                
                with col_buy:
                    # Get current price (simplified, nanti ambil dari cache)
                    current_price = float(sig.get('price_prediction', {}).get('current_price', 0)) or 1000
                    max_lot = max(1, pt_service.calculate_max_lot(current_price))
                    
                    # Recommended entry (using entry_high or entry_low as default)
                    default_price = float(sig.get('entry_high') or sig.get('entry_low') or current_price)
                    
                    # Layout Lot and Harga side-by-side
                    col_lot, col_price_in = st.columns(2)
                    with col_lot:
                        lot = st.number_input(
                            "Lot",
                            min_value=1,
                            max_value=max_lot,
                            value=max(1, min(10, max_lot)),
                            key=f"lot_{sig['ticker']}_{sig['id']}"
                        )
                    with col_price_in:
                        input_price = st.number_input(
                            "Harga",
                            min_value=1,
                            value=int(default_price) if default_price > 0 else int(current_price),
                            key=f"price_{sig['ticker']}_{sig['id']}"
                        )
                
                with col_auto:
                    # Buttons
                    if st.button(f"🛒 Buy {lot} lot", key=f"buy_{sig['ticker']}_{sig['id']}", use_container_width=True):
                        price = input_price
                        result = pt_service.buy(
                            ticker=sig['ticker'],
                            lot=lot,
                            price=price,
                            signal_id=sig['id'],
                            tp1=float(sig.get('target_1')) if sig.get('target_1') else None,
                            stop_loss=float(sig.get('stop_loss')) if sig.get('stop_loss') else None,
                            notes=f"Manual buy from Trading Engine UI"
                        )
                        if result["status"] == "success":
                            st.success(result["message"])
                            st.rerun()
                        else:
                            st.error(result["message"])
                    
                    # Auto-execute button (20% budget)
                    if st.button(f"⚡ Auto 20%", key=f"auto_{sig['ticker']}_{sig['id']}", use_container_width=True, type="secondary"):
                        with st.spinner("Auto-executing..."):
                            result = pt_service.auto_execute_signal(
                                signal_id=sig['id'],
                                budget_pct=0.20,
                                price=input_price
                            )
                            if result["status"] == "success":
                                st.success(result["message"])
                                st.rerun()
                            else:
                                st.error(result["message"])
    else:
        st.info("No top picks found. Run analysis first.")
    
    # Split positions into active and pending
    active_positions = [p for p in summary['positions'] if p['status'] == 'OPEN']
    pending_orders = [p for p in summary['positions'] if p['status'] in ['PENDING', 'PENDING_LIMIT', 'PENDING_STOP']]

    # --- PENDING ORDERS ---
    st.header("⏳ PENDING ORDERS")
    if pending_orders:
        for pos in pending_orders:
            with st.container(border=True):
                col_ticker, col_stats, col_actions = st.columns([2, 6, 2])
                with col_ticker:
                    st.markdown(f"### {pos['ticker']}")
                    st.markdown(f"{pos['lot']} lot ({pos['shares']:,} lembar)")
                    if pos['status'] == 'PENDING_STOP':
                        st.caption("📈 Buy Stop")
                    else:
                        st.caption("📉 Buy Limit")
                with col_stats:
                    col_price, col_value = st.columns(2)
                    with col_price:
                        st.caption(f"Target Bid: Rp {pos['buy_price']:,.0f}")
                        st.caption(f"Current Now: Rp {pos['current_price']:,.0f}")
                        
                        diff_val = abs(pos['current_price'] - pos['buy_price'])
                        diff_pct = (diff_val / pos['current_price'] * 100) if pos['current_price'] else 0
                        
                        if pos['status'] == 'PENDING_STOP':
                            st.caption(f"Harus Naik: {diff_pct:.2f}% lagi")
                        else:
                            st.caption(f"Harus Turun: {diff_pct:.2f}% lagi")
                    with col_value:
                        st.caption(f"Locked Cash: Rp {pos['current_value']:,.0f}")
                        if pos.get('tp1'):
                            st.caption(f"Target TP1: Rp {pos['tp1']:,.0f}")
                        if pos.get('stop_loss'):
                            st.caption(f"Target SL: Rp {pos['stop_loss']:,.0f}")
                with col_actions:
                    if st.button("❌ CANCEL", key=f"cancel_{pos['id']}", use_container_width=True, type="primary"):
                        result = pt_service.cancel_pending_order(pos['id'])
                        if result["status"] == "success":
                            st.success(result["message"])
                            st.rerun()
                        else:
                            st.error(result["message"])
    else:
        st.info("No pending orders.")

    # --- OPEN POSITIONS ---
    st.header("📈 OPEN POSITIONS")
    
    if active_positions:
        for pos in active_positions:
            with st.container(border=True):
                col_ticker, col_stats, col_actions = st.columns([2, 6, 2])
                
                with col_ticker:
                    st.markdown(f"### {pos['ticker']}")
                    st.markdown(f"{pos['lot']} lot ({pos['shares']:,} lembar)")
                
                with col_stats:
                    # P&L dengan warna
                    pnl_emoji = "🟢" if pos['unrealized_pnl'] >= 0 else "🔴"
                    st.markdown(f"{pnl_emoji} **P&L: Rp {pos['unrealized_pnl']:+,.0f}** ({pos['unrealized_pnl_pct']:+.2f}%)")
                    
                    # Price info dengan TP/SL proximity
                    col_price, col_value, col_targets = st.columns([3, 3, 3])
                    with col_price:
                        st.caption(f"Buy: Rp {pos['buy_price']:,.0f}")
                        st.caption(f"Now: Rp {pos['current_price']:,.0f}")
                        price_diff_pct = ((pos['current_price'] - pos['buy_price']) / pos['buy_price'] * 100) if pos['buy_price'] > 0 else 0
                        diff_emoji = "📈" if price_diff_pct >= 0 else "📉"
                        st.caption(f"{diff_emoji} {price_diff_pct:+.2f}%")
                    with col_value:
                        st.caption(f"Value: Rp {pos['current_value']:,.0f}")
                        st.caption(f"Lot: {pos['lot']:,} ({pos['shares']:,} lembar)")
                    with col_targets:
                        if pos.get('tp1'):
                            tp_diff_pct = ((pos['tp1'] - pos['current_price']) / pos['current_price'] * 100) if pos['current_price'] > 0 else 0
                            tp_color = "🟢" if tp_diff_pct <= 2 else "🟡"
                            st.caption(f"{tp_color} TP1: Rp {pos['tp1']:,.0f} (+{tp_diff_pct:+.2f}%)")
                        if pos.get('stop_loss'):
                            sl_diff_pct = ((pos['current_price'] - pos['stop_loss']) / pos['current_price'] * 100) if pos['current_price'] > 0 else 0
                            sl_color = "🔴" if sl_diff_pct <= 3 else "🟡"
                            st.caption(f"{sl_color} SL: Rp {pos['stop_loss']:,.0f} ({sl_diff_pct:+.2f}% safety)")
                        if pos.get('opened_at'):
                            st.caption(f"⏰ {pos['opened_at']}")
                
                with col_actions:
                    # Manual sell button
                    if st.button("💱 SELL", key=f"sell_{pos['id']}", use_container_width=True, type="secondary"):
                        # Use current price for sell
                        result = pt_service.sell(
                            trade_id=pos['id'],
                            price=pos['current_price'],
                            reason="MANUAL"
                        )
                        if result["status"] == "success":
                            st.success(f"Sold {pos['ticker']}: P&L Rp {result['trade']['realized_pnl']:+,.0f}")
                            st.rerun()
                        else:
                            st.error(result["message"])
    else:
        st.info("No open positions. Buy some stocks first!")
    
    # --- PERFORMANCE METRICS ---
    st.header("📊 PERFORMANCE")
    
    # Get trade history untuk metrics
    history = pt_service.get_trade_history(limit=100)
    closed_trades = [t for t in history if t['status'] != 'OPEN']
    
    if closed_trades:
        profitable = [t for t in closed_trades if t['realized_pnl'] > 0]
        total_profit = sum(t['realized_pnl'] for t in profitable)
        total_loss = abs(sum(t['realized_pnl'] for t in closed_trades if t['realized_pnl'] < 0))
        
        col_win, col_avg, col_sharpe, col_factor = st.columns(4)
        
        with col_win:
            win_rate = len(profitable) / len(closed_trades) * 100 if closed_trades else 0
            st.metric("🎯 Win Rate", f"{win_rate:.1f}%")
        
        with col_avg:
            avg_return = sum(t['realized_pnl'] for t in closed_trades) / len(closed_trades) if closed_trades else 0
            st.metric("📈 Avg Return", f"Rp {avg_return:,.0f}")
        
        with col_sharpe:
            # Simplified Sharpe (nanti improve)
            sharpe = total_profit / (total_loss + 1) if total_loss > 0 else 0
            st.metric("📊 Profit Factor", f"{sharpe:.2f}")
        
        with col_factor:
            profit_factor = total_profit / total_loss if total_loss > 0 else 0
            st.metric("⚖️ P/L Ratio", f"{profit_factor:.2f}")
        
        # Trade history table
        with st.expander("📜 Trade History"):
            import pandas as pd
            df = pd.DataFrame(history)
            if not df.empty:
                if "status" in df.columns:
                    df = df[df["status"] != "CANCELLED"]
                display_df = df.rename(columns={
                    "price": "Buy @",
                    "exit_price": "Sell @",
                    "tp1": "TP1",
                    "tp2": "TP2",
                    "tp3": "TP3",
                    "stop_loss": "SL",
                    "realized_pnl": "P&L",
                    "realized_pnl_pct": "P&L %",
                    "opened_at": "Opened",
                    "closed_at": "Closed",
                })
                show_cols = [c for c in ["ticker","action","lot","shares","Buy @","Sell @","TP1","TP2","TP3","SL","Amount","P&L","P&L %","Status","Opened","Closed"] if c in display_df.columns]
                display_df = display_df[show_cols]
                for col in ["Buy @", "Sell @", "P&L"]:
                    if col in display_df.columns:
                        display_df[col] = display_df[col].apply(lambda x: f"Rp {x:,.0f}" if pd.notnull(x) else "-")
                for col in ["TP1", "TP2", "TP3", "SL"]:
                    if col in display_df.columns:
                        display_df[col] = display_df[col].apply(lambda x: f"Rp {x:,.0f}" if pd.notnull(x) else "-")
                if "P&L %" in display_df.columns:
                    display_df["P&L %"] = display_df["P&L %"].apply(lambda x: f"{x:+.2f}%" if pd.notnull(x) else "-")
                for col in ["Opened", "Closed"]:
                    if col in display_df.columns:
                        display_df[col] = display_df[col].apply(lambda x: x.split("T")[0] if isinstance(x, str) and x else (x if pd.notnull(x) else "-"))
                if "Status" in display_df.columns:
                    color_map = {"TP_HIT": "🟢", "SL_HIT": "🔴", "CLOSED": "⚪"}
                    display_df["Status"] = display_df["Status"].map(lambda x: f"{color_map.get(x, '')} {x}")
                st.dataframe(display_df, use_container_width=True)
    else:
        st.info("No closed trades yet. Performance metrics akan muncul setelah ada trades closed.")
    
    # --- INSTRUCTIONS ---
    with st.expander("📖 Cara Pakai"):
        st.markdown("""
        1. **Topup modal** (contoh: 100jt) untuk mulai trading virtual
        2. **Quick Buy** dari top picks — pilih lot atau auto-execute dengan 20% budget
        3. **Monitor open positions** — lihat P&L real-time
        4. **Sell manual** atau tunggu TP/SL hit (auto-check)
        5. **Track performance** — win rate, avg return, profit factor
        """)

# === PAGE: Analytics ===

elif page == "📊 Analytics":
    st.title("📊 PAPER TRADING ANALYTICS")
    st.markdown("**Backtest Validation • Performance Attribution • Reports**")
    
    # Initialize analytics service
    try:
        from services.paper_analytics import PaperAnalytics
        analytics = PaperAnalytics()
    except ImportError as e:
        st.error(f"Analytics service tidak tersedia: {e}")
        st.stop()
    
    # Tabs untuk berbagai analytics views
    tab_backtest, tab_attribution, tab_closed, tab_export = st.tabs([
        "🔬 Backtest Validation",
        "📈 Performance Attribution", 
        "💰 Closed Positions",
        "📄 Export Reports"
    ])
    
    # === TAB 1: BACKTEST VALIDATION ===
    with tab_backtest:
        st.header("🔬 Backtest: Signals vs Actual Returns")
        
        col_period, col_signals = st.columns([2, 2])
        with col_period:
            lookback_days = st.selectbox("Lookback Period", [7, 14, 30, 60, 90], index=2)
        with col_signals:
            max_signals = st.slider("Max Signals to Analyze", 5, 50, 20)
        
        if st.button("🔍 Run Backtest", type="primary"):
            with st.spinner("Analyzing historical signals vs actual returns..."):
                result = analytics.backtest_signals_vs_actual(lookback_days=lookback_days, max_signals=max_signals)
                
                if result["status"] == "success":
                    # Display period info
                    st.info(f"📅 **Period**: {result['period']['start_date']} to {result['period']['end_date']} ({lookback_days} days)")
                    
                    # Hypothetical vs Actual comparison
                    st.subheader("📊 Performance Comparison")
                    
                    hyp = result["hypothetical"]["summary"]
                    act = result["actual"]["summary"]
                    
                    col_hyp, col_act, col_diff = st.columns(3)
                    
                    with col_hyp:
                        st.metric(
                            "Hypothetical Win Rate",
                            f"{hyp.get('win_rate', 0):.1f}%",
                            f"Avg: {hyp.get('avg_return_pct', 0):+.2f}%"
                        )
                    
                    with col_act:
                        st.metric(
                            "Actual Win Rate",
                            f"{act.get('win_rate', 0):.1f}%",
                            f"Avg: {act.get('avg_pnl_pct', 0):+.2f}%"
                        )
                    
                    with col_diff:
                        comp_data = result.get("comparison", {})
                        if "performance_comparison" in comp_data:
                            comparison = comp_data["performance_comparison"]
                            diff_emoji = "✅" if comparison["actual_better"] else "⚠️"
                            st.metric(
                                f"{diff_emoji} Performance Gap",
                                f"{comparison['win_rate_diff']:+.1f}%",
                                f"Return: {comparison['avg_return_diff']:+.2f}%"
                            )
                        else:
                            st.metric("Performance Gap", "N/A", "N/A")
                    
                    # Recommendations
                    st.subheader("💡 Recommendations")
                    if "recommendations" in comp_data:
                        for rec in comp_data["recommendations"]:
                            st.write(f"• {rec}")
                    else:
                        st.write("Belum ada data yang cukup untuk membandingkan performa.")
                    
                    # Detailed signals breakdown
                    with st.expander("📋 Detailed Signals Breakdown"):
                        signals_data = result["hypothetical"]["signals"]
                        if signals_data:
                            import pandas as pd
                            df_signals = pd.DataFrame(signals_data)
                            st.dataframe(df_signals, use_container_width=True)
                    
                    # Actual trades breakdown
                    if result["actual"]["trades"]:
                        with st.expander("💹 Actual Paper Trades"):
                            df_trades = pd.DataFrame(result["actual"]["trades"])
                            st.dataframe(df_trades, use_container_width=True)
                
                elif result["status"] == "info":
                    st.info(result["message"])
                else:
                    st.error(result.get("message", "Unknown error"))
    
    # === TAB 2: PERFORMANCE ATTRIBUTION ===
    with tab_attribution:
        st.header("📈 Performance Attribution Analysis")
        st.markdown("Analyze which factors contribute most to your returns.")
        
        if st.button("🔍 Analyze Attribution", type="primary"):
            with st.spinner("Calculating performance attribution..."):
                result = analytics.get_performance_attribution()
                
                if result["status"] == "success":
                    # By Ticker
                    st.subheader("🏆 Performance by Ticker")
                    by_ticker = result["attribution"]["by_ticker"]
                    
                    if by_ticker:
                        ticker_data = []
                        for ticker, stats in by_ticker.items():
                            ticker_data.append({
                                "Ticker": ticker,
                                "Trades": stats["total_trades"],
                                "Total P&L": f"Rp {stats['total_pnl']:+,.0f}",
                                "Avg Return": f"{stats['avg_pnl_pct']:+.2f}%",
                                "Win Rate": f"{stats['win_rate']:.1f}%",
                            })
                        
                        import pandas as pd
                        df_ticker = pd.DataFrame(ticker_data)
                        st.dataframe(df_ticker, use_container_width=True)
                        
                        # Best/worst ticker
                        col_best, col_worst = st.columns(2)
                        with col_best:
                            st.success(f"🏆 **Best**: {result['best_performing_ticker']}")
                        with col_worst:
                            st.error(f"📉 **Worst**: {result['worst_performing_ticker']}")
                    
                    # By Holding Period
                    st.subheader("⏰ Performance by Holding Period")
                    by_period = result["attribution"]["by_holding_period"]
                    
                    period_data = []
                    for period, stats in by_period.items():
                        if stats.get("total_trades", stats.get("count", 0)) > 0:
                            trades_count = stats.get("total_trades", stats.get("count", 0))
                            period_data.append({
                                "Period": period,
                                "Trades": trades_count,
                                "Total P&L": f"Rp {stats['total_pnl']:+,.0f}",
                                "Avg Return": f"{stats['avg_pnl_pct']:+.2f}%",
                            })
                    
                    if period_data:
                        df_period = pd.DataFrame(period_data)
                        st.dataframe(df_period, use_container_width=True)
                
                elif result["status"] == "info":
                    st.info(result["message"])
                else:
                    st.error(result.get("message", "Unknown error"))
    
    # === TAB 3: CLOSED POSITIONS ANALYSIS ===
    with tab_closed:
        st.header("💰 Closed Positions Analysis")
        
        if st.button("🔍 Analyze Closed Trades", type="primary"):
            with st.spinner("Analyzing closed positions..."):
                result = analytics.analyze_closed_positions()
                
                if result["status"] == "success":
                    analysis = result["analysis"]
                    
                    # P&L Distribution
                    st.subheader("📊 P&L Distribution")
                    dist = analysis["pnl_distribution"]
                    
                    col1, col2, col3, col4, col5 = st.columns(5)
                    col1.metric("🔴 Large Loss", dist["large_loss"], "< -5%")
                    col2.metric("🟡 Small Loss", dist["small_loss"], "-5% to 0%")
                    col3.metric("🟢 Small Profit", dist["small_profit"], "0% to 5%")
                    col4.metric("🔵 Medium Profit", dist["medium_profit"], "5% to 10%")
                    col5.metric("🟣 Large Profit", dist["large_profit"], "> 10%")
                    
                    # Holding Period Stats
                    st.subheader("⏰ Holding Period Analysis")
                    period_stats = analysis["holding_period_stats"]
                    
                    period_data = []
                    for period_name, stats in period_stats.items():
                        if stats["count"] > 0:
                            period_data.append({
                                "Category": period_name,
                                "Trades": stats["count"],
                                "Total P&L": f"Rp {stats['total_pnl']:+,.0f}",
                            })
                    
                    if period_data:
                        import pandas as pd
                        df_period = pd.DataFrame(period_data)
                        st.dataframe(df_period, use_container_width=True)
                    
                    # Best/Worst Trades
                    col_best, col_worst = st.columns(2)
                    
                    with col_best:
                        st.subheader("🏆 Best Trades")
                        for trade in analysis["best_trades"]:
                            st.write(f"• **{trade['ticker']}**: {trade['pnl_pct']:+.2f}% (Rp {trade['pnl']:+,.0f})")
                    
                    with col_worst:
                        st.subheader("📉 Worst Trades")
                        for trade in analysis["worst_trades"]:
                            st.write(f"• **{trade['ticker']}**: {trade['pnl_pct']:+.2f}% (Rp {trade['pnl']:+,.0f})")
                
                elif result["status"] == "info":
                    st.info(result["message"])
                else:
                    st.error(result.get("message", "Unknown error"))
    
    # === TAB 4: EXPORT REPORTS ===
    with tab_export:
        st.header("📄 Export Reports")
        
        col_csv, col_md = st.columns(2)
        
        with col_csv:
            st.subheader("📊 Trade History (CSV)")
            if st.button("⬇️ Download CSV", key="download_csv"):
                csv_data = analytics.export_trade_history_csv()
                st.download_button(
                    label="💾 Save CSV",
                    data=csv_data,
                    file_name=f"paper_trades_{datetime.utcnow().strftime('%Y%m%d_%H%M')}.csv",
                    mime="text/csv"
                )
        
        with col_md:
            st.subheader("📝 Performance Summary (Markdown)")
            if st.button("⬇️ Generate Report", key="download_md"):
                md_data = analytics.export_performance_summary_markdown()
                st.download_button(
                    label="💾 Save Markdown",
                    data=md_data,
                    file_name=f"performance_summary_{datetime.utcnow().strftime('%Y%m%d_%H%M')}.md",
                    mime="text/markdown"
                )
        
        # Preview
        st.subheader("👀 Preview")
        preview_type = st.radio("Select Preview", ["Trade History CSV", "Performance Summary"])
        
        if preview_type == "Trade History CSV":
            csv_preview = analytics.export_trade_history_csv()
            st.code(csv_preview[:1000] + "..." if len(csv_preview) > 1000 else csv_preview, language="csv")
        
        elif preview_type == "Performance Summary":
            md_preview = analytics.export_performance_summary_markdown()
            st.markdown(md_preview)

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
                entry_status = price_analysis.get("entry_status", "N/A")
                st.metric("Entry Status", entry_status[:20] if entry_status else "N/A")

            st.divider()

            with tab7:
                st.subheader("📊 Window 7 Hari")
                w7 = result.get("window_7d", {})

                if isinstance(w7, dict):
                    st.markdown(f"**Period:** {w7.get('period', 'N/A')}")
                    st.markdown(f"**Bandar Signal:** {w7.get('bandar_signal', 'N/A')} — {w7.get('assessment', 'N/A')}")
                    net_lot = w7.get("net_lot", 0)
                    net_val = w7.get("net_value", 0)
                    st.markdown(f"**Net Lot:** {net_lot:,.0f} | **Net Value:** {net_val/1e9:,.1f}B")
                    st.markdown(f"**Buyer/Seller:** {w7.get('total_buyer', 0)}/{w7.get('total_seller', 0)}")

                    # True cost bandar per broker
                    top_accumulators = w7.get("top_accumulators", [])
                    if top_accumulators:
                        st.markdown("### 🏦 True Cost Bandar per Broker (7 Hari)")
                        import pandas as pd

                        def format_value(val):
                            if val >= 1e12: return f"{val/1e12:.2f}T"
                            if val >= 1e9: return f"{val/1e9:.2f}B"
                            if val >= 1e6: return f"{val/1e6:.2f}M"
                            return f"{val:,.0f}"

                        def format_lot(lot):
                            if lot >= 1000: return f"{lot/1000:.1f}K"
                            return f"{lot:,.0f}"

                        rows = []
                        current_price = result.get("price_analysis", {}).get("current_price")
                        for b in top_accumulators[:10]:
                            avg_price = b.get("avg_price") or 0
                            distance = None
                            if current_price and avg_price:
                                distance = (current_price - avg_price) / avg_price * 100
                            rows.append({
                                "Broker": b.get("broker", ""),
                                "Nama Broker": b.get("broker_name", ""),
                                "True Cost / Avg": avg_price,
                                "Total Buy Lot": format_lot(b.get("total_buy_lot", 0)),
                                "Total Buy Value": format_value(b.get("total_buy_value", 0)),
                                "Active Days": b.get("active_days", ""),
                                "Harga vs Cost": f"{distance:+.2f}%" if distance is not None else "N/A",
                                "Status": b.get("status", ""),
                            })
                        df_true_cost_7d = pd.DataFrame(rows)
                        st.dataframe(
                            df_true_cost_7d,
                            use_container_width=True,
                            hide_index=True,
                            column_config={
                                "True Cost / Avg": st.column_config.NumberColumn(format="Rp %.0f"),
                            },
                        )

                    # True cost distribusi per broker
                    top_distributors = w7.get("top_distributors", [])
                    if top_distributors:
                        st.markdown("### 📉 Avg Sell Distribusi per Broker (7 Hari)")
                        import pandas as pd

                        def format_value(val):
                            if val >= 1e12: return f"{val/1e12:.2f}T"
                            if val >= 1e9: return f"{val/1e9:.2f}B"
                            if val >= 1e6: return f"{val/1e6:.2f}M"
                            return f"{val:,.0f}"

                        def format_lot(lot):
                            if lot >= 1000: return f"{lot/1000:.1f}K"
                            return f"{lot:,.0f}"

                        rows_dist = []
                        current_price = result.get("price_analysis", {}).get("current_price")
                        for b in top_distributors[:10]:
                            avg_price = b.get("avg_price") or 0
                            distance = None
                            if current_price and avg_price:
                                distance = (current_price - avg_price) / avg_price * 100
                            rows_dist.append({
                                "Broker": b.get("broker", ""),
                                "Nama Broker": b.get("broker_name", ""),
                                "Avg Sell": avg_price,
                                "Total Sell Lot": format_lot(b.get("total_sell_lot", 0)),
                                "Total Sell Value": format_value(b.get("total_sell_value", 0)),
                                "Active Days": b.get("active_days", ""),
                                "Harga vs Avg Sell": f"{distance:+.2f}%" if distance is not None else "N/A",
                                "Status": b.get("status", ""),
                            })
                        df_dist_7d = pd.DataFrame(rows_dist)
                        st.dataframe(
                            df_dist_7d,
                            use_container_width=True,
                            hide_index=True,
                            column_config={
                                "Avg Sell": st.column_config.NumberColumn(format="Rp %.0f"),
                            },
                        )

                    # Backward-compatible Top buyers display
                    buyers = w7.get("top_buyers", [])
                    if buyers:
                        st.markdown("**Top Buyers:**")
                        for b in buyers[:5]:
                            st.markdown(
                                f"- **{b.get('broker', '')}** ({b.get('type', '')}) — "
                                f"Net: {b.get('net_lot', '')} lot | "
                                f"Value: {b.get('net_value_B', '')} | "
                                f"Avg: {b.get('avg_price', '')}"
                            )

                    # Top sellers
                    sellers = w7.get("top_sellers", [])
                    if sellers:
                        st.markdown("**Top Sellers:**")
                        for s in sellers[:5]:
                            st.markdown(
                                f"- **{s.get('broker', '')}** ({s.get('type', '')}) — "
                                f"Net: {s.get('net_lot', '')} lot | "
                                f"Value: {s.get('net_value_B', '')} | "
                                f"Avg: {s.get('avg_price', '')}"
                            )

            with tab30:
                st.subheader("📊 Window 1 Bulan")
                w1m = result.get("window_1m", {})

                if isinstance(w1m, dict):
                    st.markdown(f"**Period:** {w1m.get('period', 'N/A')}")
                    st.markdown(f"**Bandar Signal:** {w1m.get('bandar_signal', 'N/A')} — {w1m.get('assessment', 'N/A')}")
                    net_lot = w1m.get("net_lot", 0)
                    net_val = w1m.get("net_value", 0)
                    st.markdown(f"**Net Lot:** {net_lot:,.0f} | **Net Value:** {net_val/1e9:,.1f}B")
                    st.markdown(f"**Buyer/Seller:** {w1m.get('total_buyer', 0)}/{w1m.get('total_seller', 0)}")

                    # True cost bandar per broker
                    top_accumulators = w1m.get("top_accumulators", [])
                    if top_accumulators:
                        st.markdown("### 🏦 True Cost Bandar per Broker (1 Bulan)")
                        import pandas as pd

                        def format_value(val):
                            if val >= 1e12: return f"{val/1e12:.2f}T"
                            if val >= 1e9: return f"{val/1e9:.2f}B"
                            if val >= 1e6: return f"{val/1e6:.2f}M"
                            return f"{val:,.0f}"

                        def format_lot(lot):
                            if lot >= 1000: return f"{lot/1000:.1f}K"
                            return f"{lot:,.0f}"

                        rows = []
                        current_price = result.get("price_analysis", {}).get("current_price")
                        for b in top_accumulators[:10]:
                            avg_price = b.get("avg_price") or 0
                            distance = None
                            if current_price and avg_price:
                                distance = (current_price - avg_price) / avg_price * 100
                            rows.append({
                                "Broker": b.get("broker", ""),
                                "Nama Broker": b.get("broker_name", ""),
                                "True Cost / Avg": avg_price,
                                "Total Buy Lot": format_lot(b.get("total_buy_lot", 0)),
                                "Total Buy Value": format_value(b.get("total_buy_value", 0)),
                                "Active Days": b.get("active_days", ""),
                                "Harga vs Cost": f"{distance:+.2f}%" if distance is not None else "N/A",
                                "Status": b.get("status", ""),
                            })
                        df_true_cost_1m = pd.DataFrame(rows)
                        st.dataframe(
                            df_true_cost_1m,
                            use_container_width=True,
                            hide_index=True,
                            column_config={
                                "True Cost / Avg": st.column_config.NumberColumn(format="Rp %.0f"),
                            },
                        )

                    # True cost distribusi per broker (1 Bulan)
                    top_distributors = w1m.get("top_distributors", [])
                    if top_distributors:
                        st.markdown("### 📉 Avg Sell Distribusi per Broker (1 Bulan)")
                        import pandas as pd

                        def format_value(val):
                            if val >= 1e12: return f"{val/1e12:.2f}T"
                            if val >= 1e9: return f"{val/1e9:.2f}B"
                            if val >= 1e6: return f"{val/1e6:.2f}M"
                            return f"{val:,.0f}"

                        def format_lot(lot):
                            if lot >= 1000: return f"{lot/1000:.1f}K"
                            return f"{lot:,.0f}"

                        rows_dist = []
                        current_price = result.get("price_analysis", {}).get("current_price")
                        for b in top_distributors[:10]:
                            avg_price = b.get("avg_price") or 0
                            distance = None
                            if current_price and avg_price:
                                distance = (current_price - avg_price) / avg_price * 100
                            rows_dist.append({
                                "Broker": b.get("broker", ""),
                                "Nama Broker": b.get("broker_name", ""),
                                "Avg Sell": avg_price,
                                "Total Sell Lot": format_lot(b.get("total_sell_lot", 0)),
                                "Total Sell Value": format_value(b.get("total_sell_value", 0)),
                                "Active Days": b.get("active_days", ""),
                                "Harga vs Avg Sell": f"{distance:+.2f}%" if distance is not None else "N/A",
                                "Status": b.get("status", ""),
                            })
                        df_dist_1m = pd.DataFrame(rows_dist)
                        st.dataframe(
                            df_dist_1m,
                            use_container_width=True,
                            hide_index=True,
                            column_config={
                                "Avg Sell": st.column_config.NumberColumn(format="Rp %.0f"),
                            },
                        )

                    buyers = w1m.get("top_buyers", [])
                    if buyers:
                        st.markdown("**Top Buyers:**")
                        for b in buyers[:5]:
                            st.markdown(
                                f"- **{b.get('broker', '')}** ({b.get('type', '')}) — "
                                f"Net: {b.get('net_lot', '')} lot | "
                                f"Value: {b.get('net_value_B', '')} | "
                                f"Avg: {b.get('avg_price', '')}"
                            )

                    sellers = w1m.get("top_sellers", [])
                    if sellers:
                        st.markdown("**Top Sellers:**")
                        for s in sellers[:5]:
                            st.markdown(
                                f"- **{s.get('broker', '')}** ({s.get('type', '')}) — "
                                f"Net: {s.get('net_lot', '')} lot | "
                                f"Value: {s.get('net_value_B', '')} | "
                                f"Avg: {s.get('avg_price', '')}"
                            )

            # Floor Prices
            st.divider()
            st.subheader("🏢 Floor Price & Fase per Broker")
            floor_prices = result.get("floor_prices", [])
            if floor_prices:
                import pandas as pd
                df = pd.DataFrame(floor_prices)
                df = df[["broker", "type", "floor_price", "net_lot", "net_value_B", "phase", "distance_from_current"]]
                df.columns = ["Broker", "Type", "Floor Price", "Net Lot", "Value (B)", "Fase", "vs Current"]
                st.dataframe(df, use_container_width=True, hide_index=True)

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

                entry_status = pa.get("entry_status", "")
                entry_label = pa.get("entry_label", "")
                display_text = f"{entry_status} {entry_label}" if entry_label else entry_status
                if "IDEAL" in entry_status:
                    st.success(display_text)
                elif "ACCEPTABLE" in entry_status:
                    st.info(display_text)
                elif "CAUTION" in entry_status:
                    st.warning(display_text)
                elif "AVOID" in entry_status:
                    st.error(display_text)


# === PAGE: Performance ===

elif page == "📊 Performance":
    col1, col2 = st.columns([3, 1])
    with col1:
        st.title("📊 PERFORMANCE TRACKER")
    with col2:
        st.write("") # spacing
        if st.button("🔄 Check Signals Now", use_container_width=True):
            with st.spinner("Mengecek performa sinyal ke pasar hari ini..."):
                try:
                    from scheduler import run_performance_check
                    run_performance_check()
                    st.success("Selesai divalidasi!")
                    import time
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

    # Helper to parse json fields
    def load_json_field(field):
        if not field:
            return {}
        if isinstance(field, dict):
            return field
        if isinstance(field, str):
            try:
                return json.loads(field)
            except Exception:
                return {}
        return {}

    # Get performance data with all signal columns
    perf_data = query_db("""
        SELECT p.*, s.ticker, s.signal, s.conviction, s.run_date as signal_date,
               s.entry_low, s.entry_high, s.max_entry, s.target_1, s.target_2, s.target_3, s.stop_loss,
               s.thesis, s.entry_reasoning, s.price_prediction, s.ml_prediction
        FROM performance p
        JOIN signals s ON p.signal_id = s.id
        ORDER BY p.check_date DESC, s.run_date DESC
        LIMIT 50
    """)

    if perf_data:
        # Summary stats
        total = len(perf_data)
        hits = sum(1 for p in perf_data if (p.get("result") or "").startswith("HIT_") and p.get("result") != "HIT_SL")
        losses = sum(1 for p in perf_data if p.get("result") == "HIT_SL")
        opens = sum(1 for p in perf_data if p.get("result") == "OPEN")

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            win_rate = (hits / (hits + losses) * 100) if (hits + losses) > 0 else 0
            st.metric("Win Rate", f"{win_rate:.0f}%")
        with col2:
            st.metric("Profitable (TP Hit)", f"{hits} ✅")
        with col3:
            st.metric("Loss (SL Hit)", f"{losses} ❌")
        with col4:
            st.metric("Open Position", f"{opens} 🔄")

        st.divider()

        # Recent signals interactive table
        st.subheader("Recent Signals Performance")
        import pandas as pd
        df_perf_table = pd.DataFrame(perf_data)
        
        df_display = pd.DataFrame()
        df_display["Ticker"] = df_perf_table["ticker"]
        df_display["Signal Date"] = df_perf_table["signal_date"].apply(lambda d: str(d))
        df_display["Type"] = df_perf_table["signal"]
        df_display["Conviction"] = df_perf_table["conviction"]
        
        # Ideal Entry Zone
        def format_entry(row):
            el = row.get("entry_low")
            eh = row.get("entry_high")
            if el is not None and eh is not None:
                return f"{int(el):,} - {int(eh):,}"
            return "N/A"
        df_display["Entry Zone"] = df_perf_table.apply(format_entry, axis=1)
        
        # Targets & SL
        df_display["Target 1 (TP1)"] = df_perf_table["target_1"].apply(lambda v: f"Rp {int(v):,}" if pd.notnull(v) and v else "N/A")
        df_display["Target 2 (TP2)"] = df_perf_table["target_2"].apply(lambda v: f"Rp {int(v):,}" if pd.notnull(v) and v else "N/A")
        df_display["Stop Loss"] = df_perf_table["stop_loss"].apply(lambda v: f"Rp {int(v):,}" if pd.notnull(v) and v else "N/A")
        
        # Performance info
        df_display["Checked Date"] = df_perf_table["check_date"].apply(lambda d: str(d))
        df_display["Last Price"] = df_perf_table["actual_price"].apply(lambda v: f"Rp {int(v):,}" if pd.notnull(v) and v else "N/A")
        df_display["Return"] = df_perf_table["return_pct"].apply(lambda v: f"{float(v):+.2f}%" if pd.notnull(v) else "0.00%")
        df_display["Result"] = df_perf_table["result"].apply(lambda r: f"✅ {r}" if str(r).startswith("HIT_") and r != "HIT_SL" else f"❌ {r}" if r == "HIT_SL" else f"🔄 {r}")
        
        st.dataframe(df_display, use_container_width=True, hide_index=True)

        st.divider()
        st.subheader("🔍 Deep Validation Sinyal & Prediksi")
        
        # Create selectbox option list
        signal_options = []
        for idx, row in df_perf_table.iterrows():
            signal_options.append(f"{row['ticker']} ({row['signal_date']}) - {row['result']} [Ret: {row['return_pct']:+.1f}%]")
            
        selected_option = st.selectbox(
            "Pilih sinyal untuk melihat validasi detail & analisa pergerakan harga:",
            options=signal_options,
            index=0
        )
        
        if selected_option:
            selected_idx = signal_options.index(selected_option)
            selected_signal = perf_data[selected_idx]
            
            ticker = selected_signal["ticker"]
            sig_date = selected_signal["signal_date"]
            check_date = selected_signal["check_date"]
            
            # Show original thesis & reasoning
            with st.container():
                col_thesis, col_reason = st.columns(2)
                with col_thesis:
                    st.markdown("##### 📝 Original Thesis")
                    st.info(selected_signal.get("thesis") or "N/A")
                with col_reason:
                    st.markdown("##### 🎯 Entry Reasoning")
                    st.success(selected_signal.get("entry_reasoning") or "N/A")

            # Load predictions
            ml_pred = load_json_field(selected_signal.get("ml_prediction"))
            price_pred = load_json_field(selected_signal.get("price_prediction"))
            
            # Query actual price history
            price_history = query_db("""
                SELECT trade_date, close, open, high, low, volume
                FROM ohlcv_prices
                WHERE ticker = %s AND trade_date >= %s
                ORDER BY trade_date ASC
            """, (ticker, sig_date - timedelta(days=7)))
            
            # Query actual trading days from signal date onwards to map horizons
            post_signal_prices = query_db("""
                SELECT trade_date, close
                FROM ohlcv_prices
                WHERE ticker = %s AND trade_date >= %s
                ORDER BY trade_date ASC
                LIMIT 15
            """, (ticker, sig_date))
            
            # Render chart and validation tables
            col_chart, col_val = st.columns([3, 2])
            
            with col_chart:
                st.markdown("##### 📈 Chart Pergerakan Harga vs Key Levels")
                if price_history:
                    df_prices = pd.DataFrame(price_history)
                    df_prices["trade_date"] = pd.to_datetime(df_prices["trade_date"])
                    df_prices = df_prices.sort_values("trade_date")
                    
                    import plotly.graph_objects as go
                    fig = go.Figure()
                    
                    # Add price line
                    fig.add_trace(go.Scatter(
                        x=df_prices["trade_date"],
                        y=df_prices["close"],
                        mode="lines+markers",
                        name="Harga Close",
                        line=dict(color="#3b82f6", width=3),
                    ))
                    
                    # Add targets & SL
                    tp1 = float(selected_signal.get("target_1") or 0)
                    tp2 = float(selected_signal.get("target_2") or 0)
                    sl = float(selected_signal.get("stop_loss") or 0)
                    el = float(selected_signal.get("entry_low") or 0)
                    eh = float(selected_signal.get("entry_high") or 0)
                    
                    if tp1 > 0:
                        fig.add_hline(y=tp1, line_dash="dash", line_color="#10b981", 
                                      annotation_text=f"TP1 (Rp {tp1:,.0f})", annotation_position="top left")
                    if tp2 > 0:
                        fig.add_hline(y=tp2, line_dash="dash", line_color="#059669", 
                                      annotation_text=f"TP2 (Rp {tp2:,.0f})", annotation_position="top left")
                    if sl > 0:
                        fig.add_hline(y=sl, line_dash="dash", line_color="#ef4444", 
                                      annotation_text=f"SL (Rp {sl:,.0f})", annotation_position="top left")
                                      
                    if el > 0 and eh > 0:
                        fig.add_hrect(y0=el, y1=eh, fillcolor="#f59e0b", opacity=0.15, 
                                      line_width=0, annotation_text="Ideal Entry Zone", annotation_position="inside top left")
                                      
                    fig.update_layout(
                        template="plotly_dark",
                        hovermode="x unified",
                        margin=dict(l=10, r=10, t=10, b=10),
                        height=350,
                    )
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning("Data harga historis tidak tersedia.")
            
            with col_val:
                st.markdown("##### 🔬 Validasi Prediksi Model")
                
                # Map actual trading price horizons
                actual_trading_prices = {}
                if post_signal_prices:
                    baseline_close = float(post_signal_prices[0]["close"])
                    actual_trading_prices["baseline"] = baseline_close
                    
                    horizons_indices = {"day_1": 1, "day_3": 3, "day_5": 5, "day_7": 7}
                    for key, idx in horizons_indices.items():
                        if len(post_signal_prices) > idx:
                            actual_close = float(post_signal_prices[idx]["close"])
                            actual_pct = (actual_close - baseline_close) / baseline_close * 100
                            actual_trading_prices[key] = {
                                "price": actual_close,
                                "pct_change": actual_pct,
                                "date": str(post_signal_prices[idx]["trade_date"])
                            }
                
                # Validation tabs
                pred_val_tabs = st.tabs(["🤖 ML Forecast (T+5)", "📊 Price Predictor"])
                
                with pred_val_tabs[0]:
                    if ml_pred:
                        multiday_pred = ml_pred.get("predictions_multiday", {}) or {}
                        pred_keys = {"day_1": "1d", "day_3": "3d", "day_5": "5d", "day_7": "7d"}
                        
                        ml_rows = []
                        for key, pkey in pred_keys.items():
                            pred_ret = multiday_pred.get(pkey) or multiday_pred.get(key)
                            if pred_ret is not None:
                                pred_ret = float(pred_ret)
                                actual_data = actual_trading_prices.get(key)
                                if actual_data:
                                    actual_ret = actual_data["pct_change"]
                                    
                                    dir_ok = "✅ Benar" if (pred_ret * actual_ret > 0) or (pred_ret == 0 and actual_ret == 0) else "❌ Salah"
                                    
                                    ml_rows.append({
                                        "Horizon": key.upper().replace("_", " "),
                                        "Pred Return": f"{pred_ret:+.2f}%",
                                        "Act Return": f"{actual_ret:+.2f}%",
                                        "Arah": dir_ok,
                                        "Error": f"{abs(pred_ret - actual_ret):.2f}%"
                                    })
                        
                        if ml_rows:
                            st.dataframe(pd.DataFrame(ml_rows), use_container_width=True, hide_index=True)
                            
                            # ML info details
                            st.markdown(f"**ML Signal:** `{ml_pred.get('signal', 'N/A')}` | **Confidence:** `{ml_pred.get('confidence', 'N/A')}`")
                        else:
                            st.info("Data horizon realisasi belum lengkap untuk memvalidasi ML.")
                    else:
                        st.info("Tidak ada data prediksi ML untuk sinyal ini.")
                        
                with pred_val_tabs[1]:
                    if price_pred:
                        forecast_prices = price_pred.get("predictions", {}) or {}
                        
                        price_rows = []
                        for key in ["day_1", "day_3", "day_5", "day_7"]:
                            forecast_data = forecast_prices.get(key)
                            if forecast_data:
                                pred_price = forecast_data.get("price")
                                pred_pct = forecast_data.get("pct_change")
                                if pred_price is not None:
                                    pred_price = float(pred_price)
                                    actual_data = actual_trading_prices.get(key)
                                    if actual_data:
                                        actual_price_val = actual_data["price"]
                                        error_pct = abs(pred_price - actual_price_val) / actual_price_val * 100
                                        
                                        price_rows.append({
                                            "Horizon": key.upper().replace("_", " "),
                                            "Pred Price": f"Rp {int(pred_price):,}",
                                            "Act Price": f"Rp {int(actual_price_val):,}",
                                            "Pred Change": str(pred_pct),
                                            "Act Change": f"{actual_data['pct_change']:+.2f}%",
                                            "Error": f"{error_pct:.2f}%"
                                        })
                        
                        if price_rows:
                            st.dataframe(pd.DataFrame(price_rows), use_container_width=True, hide_index=True)
                            
                            # Price predictor details
                            st.markdown(f"**Confidence:** `{price_pred.get('confidence', 'N/A')}`")
                        else:
                            st.info("Data horizon realisasi belum lengkap untuk memvalidasi Price Predictor.")
                    else:
                        st.info("Tidak ada data prediksi harga untuk sinyal ini.")
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

    accuracy_tab, ml_tab = st.tabs(["📊 Signal Performance", "🤖 ML Validation"])

    with accuracy_tab:
        agent_perf = query_db("""
            SELECT
                s.ticker,
                s.signal,
                s.conviction,
                DATE_TRUNC('month', p.check_date)::date AS month,
                p.result,
                p.return_pct
            FROM performance p
            JOIN signals s ON p.signal_id = s.id
            ORDER BY p.check_date DESC
            LIMIT 500
        """)

        if agent_perf:
            import pandas as pd
            df_perf = pd.DataFrame(agent_perf)
            df_perf["return_pct"] = pd.to_numeric(df_perf["return_pct"], errors="coerce").fillna(0.0)
            df_perf["is_hit"] = df_perf["result"].fillna("").apply(
                lambda r: str(r).startswith("HIT_") and r != "HIT_SL"
            )
            df_perf["is_loss"] = df_perf["result"].fillna("").eq("HIT_SL")
            df_closed = df_perf[df_perf["is_hit"] | df_perf["is_loss"]]

            c1, c2, c3, c4 = st.columns(4)
            with c1:
                closed = len(df_closed)
                win_rate = (df_closed["is_hit"].sum() / closed * 100) if closed else 0
                st.metric("Closed Win Rate", f"{win_rate:.0f}%")
            with c2:
                avg_ret = df_perf["return_pct"].mean()
                st.metric("Avg Return", f"{avg_ret:+.2f}%")
            with c3:
                st.metric("Tracked Rows", len(df_perf))
            with c4:
                open_count = (df_perf["result"].fillna("") == "OPEN").sum()
                st.metric("Open Rows", int(open_count))

            col_a, col_b = st.columns(2)
            with col_a:
                st.caption("Result Distribution")
                result_counts = df_perf["result"].fillna("UNKNOWN").value_counts().reset_index()
                result_counts.columns = ["result", "count"]
                st.dataframe(result_counts, use_container_width=True, hide_index=True)
            with col_b:
                st.caption("Win Rate per Ticker (closed signals)")
                if not df_closed.empty:
                    ticker_stats = (
                        df_closed.groupby("ticker")
                        .agg(
                            closed=("result", "count"),
                            hits=("is_hit", "sum"),
                            avg_return=("return_pct", "mean"),
                        )
                        .reset_index()
                    )
                    ticker_stats["win_rate"] = ticker_stats["hits"] / ticker_stats["closed"] * 100
                    ticker_stats = ticker_stats.sort_values("win_rate", ascending=False)
                    st.dataframe(
                        ticker_stats[["ticker", "closed", "hits", "win_rate", "avg_return"]],
                        use_container_width=True,
                        hide_index=True,
                    )
                else:
                    st.info("Belum ada closed signal (HIT_TP/HIT_SL).")

            st.caption("Monthly Win Rate")
            if not df_closed.empty:
                monthly = (
                    df_closed.groupby("month")
                    .agg(closed=("result", "count"), hits=("is_hit", "sum"))
                    .reset_index()
                )
                monthly["win_rate"] = monthly["hits"] / monthly["closed"] * 100
                st.bar_chart(monthly.set_index("month")[["win_rate"]])
            else:
                st.info("Monthly win rate akan muncul setelah ada closed signal.")
        else:
            st.info("Belum ada data performance untuk menghitung agent accuracy.")

    with ml_tab:
        st.warning("⚠️ **Model ML Swing (Day-1) ini telah DEPRECATED.** Disarankan untuk menggunakan model Multi-Day (T+1 s/d T+7).")
        st.caption("Status training dan validasi model ML Swing (Day-1 - Deprecated).")

        model_path = "models/checkpoints/lgbm_day1.pkl"
        meta_path = "models/checkpoints/lgbm_day1_meta.json"
        if os.path.exists(model_path):
            st.info(f"Model Day-1 ditemukan: `{model_path}`")
        else:
            st.warning("Model Day-1 tidak aktif.")
            st.code("make train-ml-multiday", language="bash")

        if os.path.exists(meta_path):
            try:
                with open(meta_path, "r") as f:
                    meta = json.load(f)
                metrics = meta.get("holdout_metrics", {})
                rows = meta.get("rows", {})
                run_date = meta.get("run_date", "N/A")
                try:
                    run_date = datetime.fromisoformat(run_date).strftime("%d %b %Y, %H:%M")
                except Exception:
                    pass

                st.markdown(f"**Last training:** {run_date}")
                c1, c2, c3, c4 = st.columns(4)
                with c1:
                    st.metric("Tickers Trained", rows.get("tickers_trained", 0))
                with c2:
                    st.metric("Final Rows", rows.get("final_train_rows", 0))
                with c3:
                    st.metric("Holdout DirAcc", f"{metrics.get('directional_accuracy', 0):.1f}%")
                with c4:
                    st.metric("Holdout MAE", f"{metrics.get('mae_pct', 0):.3f}%")

                with st.expander("Training metadata", expanded=False):
                    st.json(meta)
            except Exception as e:
                st.error(f"Gagal membaca metadata training: {e}")
        else:
            st.info("Belum ada metadata training untuk model Day-1.")

        st.divider()
        st.caption("Menampilkan hasil dari `scripts/validate_ml_accuracy.py` jika file `validate_ml_result.json` tersedia.")
        ml_result_path = "validate_ml_result.json"
        if os.path.exists(ml_result_path):
            try:
                import pandas as pd
                with open(ml_result_path, "r") as f:
                    ml_result = json.load(f)
                summary = ml_result.get("summary", [])
                if summary:
                    df_ml = pd.DataFrame(summary)
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        st.metric("Avg Directional Accuracy", f"{df_ml['dir_acc'].mean():.1f}%")
                    with c2:
                        st.metric("Avg MAE", f"{df_ml['mae_pct'].mean():.3f}%")
                    with c3:
                        st.metric("Tickers Validated", len(df_ml))
                    st.dataframe(df_ml, use_container_width=True, hide_index=True)
                    st.bar_chart(df_ml.set_index("ticker")[["dir_acc"]])
                else:
                    st.warning("File validate_ml_result.json ada, tapi summary kosong.")
            except Exception as e:
                st.error(f"Gagal membaca validate_ml_result.json: {e}")
        else:
            st.info("Belum ada hasil ML validation. Jalankan: `make validate-ml` atau `python scripts/validate_ml_accuracy.py --ticker BBCA`")


# === PAGE: IHSG Predictor ===

elif page == "📈 IHSG Predictor":
    st.title("📈 IHSG PREDICTOR")

    tab_live, tab_backtest, tab_outlook = st.tabs(["🔮 Live Prediction & Track Record", "🧪 Backtest Strategi IHSG", "🌐 1-Year Outlook & Reversal Detector"])

    with tab_live:
        # Get latest IHSG prediction
        ihsg_pred = query_db("""
            SELECT * FROM ihsg_predictions
            WHERE run_date = (SELECT MAX(run_date) FROM ihsg_predictions)
            LIMIT 1
        """)

        if ihsg_pred:
            pred = ihsg_pred[0]

            # Header metrics
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Current Level", f"{pred.get('current_price', 0):,.0f}")
            with col2:
                conf_icon = "🟢" if pred.get('confidence') == "HIGH" else "🟡" if pred.get('confidence') == "MEDIUM" else "🔴"
                st.metric("Confidence", f"{conf_icon} {pred.get('confidence', 'N/A')}")
            with col3:
                st.metric("Direction", pred.get('direction', 'N/A'))
            with col4:
                st.metric("Volatility", pred.get('volatility_level', 'N/A'))

            st.divider()

            # Predictions (D1, D3, D5, D7)
            st.subheader("📊 Price Predictions")
            col_d1, col_d3, col_d5, col_d7 = st.columns(4)

            with col_d1:
                pct = pred.get('day_1_pct', 0)
                color = "normal" if pct >= 0 else "inverse"
                st.metric("D+1", f"{pred.get('day_1_price', 0):,.0f}", f"{pct:+.2f}%", delta_color=color)

            with col_d3:
                pct = pred.get('day_3_pct', 0)
                color = "normal" if pct >= 0 else "inverse"
                st.metric("D+3", f"{pred.get('day_3_price', 0):,.0f}", f"{pct:+.2f}%", delta_color=color)

            with col_d5:
                pct = pred.get('day_5_pct', 0)
                color = "normal" if pct >= 0 else "inverse"
                st.metric("D+5", f"{pred.get('day_5_price', 0):,.0f}", f"{pct:+.2f}%", delta_color=color)

            with col_d7:
                pct = pred.get('day_7_pct', 0)
                color = "normal" if pct >= 0 else "inverse"
                st.metric("D+7", f"{pred.get('day_7_price', 0):,.0f}", f"{pct:+.2f}%", delta_color=color)

            st.divider()

            # Component scores
            st.subheader("⚙️ Component Scores")
            comp = pred.get('component_scores') or {}
            if isinstance(comp, str):
                comp = json.loads(comp)

            col1, col2, col3, col4, col5 = st.columns(5)
            with col1:
                st.metric("Momentum", f"{comp.get('momentum', 0):.2f}")
            with col2:
                st.metric("Breadth", f"{comp.get('breadth', 0):.2f}")
            with col3:
                st.metric("Macro", f"{comp.get('macro', 0):.2f}")
            with col4:
                st.metric("Sectors", f"{comp.get('sectors', 0):.2f}")
            with col5:
                st.metric("News", f"{comp.get('news', 0):.2f}")

            st.divider()

            # --- PERFORMA IHSG ---
            st.subheader("📊 Track Record Akurasi Database")
            try:
                acc_data = query_db('''
                    WITH p_data AS (
                        SELECT DISTINCT ON (run_date::date) run_date::date as pd, direction, current_price FROM ihsg_predictions
                    ),
                    m_data AS (
                        SELECT p.pd, p.direction, p.current_price, a.close as actual,
                            ROUND(((a.close - p.current_price) / p.current_price * 100)::numeric, 2) as actual_pct
                        FROM p_data p
                        JOIN ihsg_ohlcv a ON a.trade_date = (
                            SELECT min(trade_date) FROM ihsg_ohlcv WHERE trade_date > p.pd
                        )
                    )
                    SELECT 
                        COUNT(*) as total,
                        SUM(CASE 
                            WHEN direction = 'BULLISH' AND actual_pct >= 0 THEN 1
                            WHEN direction = 'BEARISH' AND actual_pct < 0 THEN 1
                            WHEN direction = 'SIDEWAYS' AND abs(actual_pct) < 0.5 THEN 1
                            ELSE 0 
                        END) as correct
                    FROM m_data;
                ''')
                if acc_data and acc_data[0]['total'] > 0:
                    t = acc_data[0]['total']
                    c = acc_data[0]['correct']
                    pct = (c / t) * 100
                    st.info(f"**Akurasi Arah Historis (Database Log):** {pct:.1f}% ({c}/{t} hari)")
            except:
                pass
                
            st.subheader("📝 Analysis (LLM Manager)")

            with st.expander("Reasoning", expanded=True):
                st.markdown(pred.get('reasoning', 'N/A'))

            drivers = pred.get('key_drivers') or []
            if isinstance(drivers, str):
                drivers = json.loads(drivers)
            with st.expander("Key Drivers"):
                if drivers:
                    for i, driver in enumerate(drivers, 1):
                        st.markdown(f"{i}. {driver}")
                else:
                    st.info("No drivers identified")

            risks = pred.get('risks') or []
            if isinstance(risks, str):
                risks = json.loads(risks)
            with st.expander("Risk Factors"):
                if risks:
                    for i, risk in enumerate(risks, 1):
                        st.markdown(f"{i}. {risk}")
                else:
                    st.info("No major risks identified")

            st.divider()

            # Historical predictions
            st.subheader("📈 Historical Predictions")
            hist = query_db("""
                SELECT run_date, current_price, day_1_price, day_1_pct, direction, confidence
                FROM ihsg_predictions
                ORDER BY run_date DESC
                LIMIT 20
            """)
            if hist:
                import pandas as pd
                df = pd.DataFrame(hist)
                st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("Belum ada IHSG prediction. Jalankan analysis terlebih dahulu.")

    with tab_backtest:
        st.subheader("🧪 Historical Backtest Strategi IHSG")
        st.caption("Uji akurasi tebakan arah biner (BULLISH vs BEARISH) dan return akumulatif strategi IHSG Predictor terhadap data historis OHLCV.")

        c1, c2 = st.columns([3, 1])
        with c1:
            years_opt = st.select_slider(
                "Pilih Periode Backtest (Tahun):",
                options=[1.0, 2.0, 3.0, 5.0],
                value=3.0,
                format_func=lambda x: f"{int(x)} Tahun" if x == int(x) else f"{x} Tahun"
            )
        with c2:
            st.write("")
            st.write("")
            run_bt = st.button("🚀 Jalankan Backtest", type="primary", use_container_width=True)

        if "ihsg_bt_summary" not in st.session_state or run_bt:
            with st.spinner("Menjalankan simulasi backtest historis..."):
                try:
                    from scripts.backtest_ihsg_strategy import run_ihsg_backtest
                    st.session_state["ihsg_bt_summary"] = run_ihsg_backtest(years=years_opt)
                except Exception as e:
                    st.error(f"Gagal menjalankan backtest: {e}")

        bt = st.session_state.get("ihsg_bt_summary")
        if bt:
            st.success(f"**Periode Evaluasi:** {bt['start_date']} s/d {bt['end_date']} ({bt['total_days']} Hari Perdagangan)")

            # Metric Cards
            m1, m2, m3, m4 = st.columns(4)
            with m1:
                st.metric("D+1 Direction Win Rate", f"{bt['win_rate']:.2f}%", f"{bt['win_count']}/{bt['total_days']} Hari")
            with m2:
                st.metric("Mean Abs Error (MAE)", f"{bt['mae_avg']:.2f}%", "Rata-rata Meleset Target")
            with m3:
                delta_l = bt['cum_strat_long_pct'] - bt['cum_bench_pct']
                st.metric("Return Long-Only", f"{bt['cum_strat_long_pct']:+.2f}%", f"{delta_l:+.2f}% vs Benchmark")
            with m4:
                delta_ls = bt['cum_strat_ls_pct'] - bt['cum_bench_pct']
                st.metric("Return Long-Short", f"{bt['cum_strat_ls_pct']:+.2f}%", f"{delta_ls:+.2f}% vs Benchmark")

            st.divider()

            # Explanatory Guide: Cara Membaca Hasil Backtest
            with st.expander("📖 CARA MEMBACA HASIL BACKTEST IHSG", expanded=True):
                st.markdown("""
### 💡 Panduan Membaca Hasil Evaluasi:
1. **D+1 Direction Win Rate (Akurasi Arah Harian)**:
   - Persentase hari di mana tebakan sinyal (`BULLISH` vs `BEARISH`) tepat sesuai pergerakan IHSG keesokan harinya.
   - **Win Rate > 50%** menandakan sistem memiliki *statistical edge* (keunggulan matematis di atas tebakan acak 50%).
2. **Mean Absolute Error (MAE)**:
   - Jarak rata-rata persentase proyeksi harga target dibanding penutupan pasar aktual.
   - Angka MAE yang kecil (misal $<1.0\%$) membuktikan kalibrasi volatilitas ATR 14-hari berjalan presisi.
3. **Return Long-Only**:
   - Imbal hasil akumulatif jika kamu **hanya membeli / memegang pasar** saat sinyal `BULLISH` dan **memegang CASH (keluar dari pasar)** saat sinyal `BEARISH`.
   - Strategi ini secara efektif memproteksi portofolio dari *downtrend* dan pasar *bearish*.
4. **Return Long-Short**:
   - Imbal hasil jika kamu mengambil posisi *long* saat `BULLISH` dan posisi *short* / defensif saat `BEARISH`.
5. **Benchmark IHSG (Buy & Hold)**:
   - Imbal hasil jika hanya membeli indeks IHSG dan mendiamkannya tanpa strategi (*Buy & Hold*) selama periode tersebut.
""")

            # Equity Curve Simulation Chart
            st.subheader("📈 Kurva Ekuitas Simulasi Strategi vs Benchmark IHSG")
            res_df = bt.get("df")
            if res_df is not None and not res_df.empty:
                import pandas as pd
                chart_df = pd.DataFrame()
                chart_df["Date"] = pd.to_datetime(res_df["date"])
                chart_df["IHSG Benchmark"] = (1 + res_df["actual_return_d1"] / 100).cumprod() * 100
                chart_df["Strategy Long-Only"] = (1 + res_df["strat_long_only"] / 100).cumprod() * 100
                chart_df["Strategy Long-Short"] = (1 + res_df["strat_long_short"] / 100).cumprod() * 100
                chart_df = chart_df.set_index("Date")
                st.line_chart(chart_df)

            # Detailed Logs Table
            with st.expander("🔍 Detail Transaksi & Log Prediksi Harian"):
                if res_df is not None:
                    disp_df = res_df[["date", "close", "combined_score", "predicted_dir", "actual_return_d1", "is_correct_d1", "pred_d1_pct", "mae_d1"]].copy()
                    disp_df.columns = ["Tanggal", "Close IHSG", "Score", "Prediksi Arah", "Actual Return %", "Tebakan Benar?", "Pred Target %", "MAE %"]
                    st.dataframe(disp_df, use_container_width=True, hide_index=True)

    with tab_outlook:
        st.subheader("🌐 1-Year Technical Outlook & Reversal Pivot Detector")
        st.caption("Proyeksi tren 1-tahun, deteksi titik Reversal Bottom/Top (Fibonacci 5-Tahun & Monthly Pivots), serta estimasi jendela waktu (Bulan & Minggu).")

        # Fetch latest 1-year outlook payload
        ihsg_pred = query_db("""
            SELECT * FROM ihsg_predictions
            WHERE run_date = (SELECT MAX(run_date) FROM ihsg_predictions)
            LIMIT 1
        """)
        
        outlook = {}
        if ihsg_pred:
            scores = ihsg_pred[0]
            try:
                from agents.ihsg_predictor import predict_ihsg_1year_outlook
                from data.fetcher_ihsg import get_ihsg_ohlcv, get_ihsg_technical_analysis
                ohlcv_8y = get_ihsg_ohlcv("8y")
                tv_w = get_ihsg_technical_analysis("1W")
                tv_m = get_ihsg_technical_analysis("1M")
                c_p = float(scores.get("current_price") or ohlcv_8y["Close"].iloc[-1])
                outlook = predict_ihsg_1year_outlook(ohlcv_8y, c_p, tv_w, tv_m)
            except Exception as e:
                st.warning(f"Memuat 1-Year Outlook: {e}")

        if outlook:
            # Header metrics
            o1, o2, o3, o4 = st.columns(4)
            with o1:
                dir_color = "🟢" if outlook.get("direction_1year") == "BULLISH" else "🔴"
                st.metric("Arah Tren 1-Tahun", f"{dir_color} {outlook.get('direction_1year', 'N/A')}")
            with o2:
                st.metric("Zona Bottom Confluence", f"{outlook.get('bottom_confluence_level', 0):,.0f}", f"{outlook.get('downside_risk_pct', 0):+.2f}% Risk")
            with o3:
                st.metric("Zona Top Resistance", f"{outlook.get('top_confluence_level', 0):,.0f}", f"{outlook.get('upside_potential_pct', 0):+.2f}% Upside")
            with o4:
                st.metric("Estimasi Waktu Reversal", outlook.get("estimated_reversal_window", "N/A"))

            st.divider()

            # 2-WAY REVERSAL PIVOT TRIGGER BOX
            st.subheader("🔄 Sinyal Konfirmasi Pembalikan Arah (Reversal Triggers)")
            rc1, rc2 = st.columns(2)
            with rc1:
                st.markdown("### 🟢 SAAT BEARISH: Kapan Berbalik NAIK?")
                is_bull_ok = outlook.get("bullish_reversal_confirmed", False)
                status_icon = "✅ SELESAI BOTTOMLAND (BULLISH)" if is_bull_ok else "⏳ DALAM PROSES BOTTOMLAND"
                st.info(f"""
**Status**: {status_icon}
- **Zona Bottom Target**: **{outlook.get('bottom_confluence_level', 0):,.0f}**
- **Syarat Utama**: Harga Breakout & Close di atas **MA50 Weekly ({outlook.get('ma50_weekly', 0):,.0f})**
- **Konfirmasi Sekunder**: Rebound Weekly RSI & Weekly MACD Golden Cross
""")

            with rc2:
                st.markdown("### 🔴 SAAT BULLISH: Kapan Berbalik TURUN?")
                is_bear_ok = outlook.get("bearish_reversal_confirmed", False)
                status_icon_b = "⚠️ BERPOTENSI REVERSAL TURUN" if is_bear_ok else "🟢 TREN NAIK MASIH SOLID"
                st.warning(f"""
**Status**: {status_icon_b}
- **Zona Top Resistance Target**: **{outlook.get('top_confluence_level', 0):,.0f}**
- **Syarat Utama**: Harga Breakdown & Close di bawah **MA50 Weekly ({outlook.get('ma50_weekly', 0):,.0f})**
- **Konfirmasi Sekunder**: Weekly RSI Overbought (>70) & Weekly MACD Death Cross
""")

            st.divider()

            # SEASONALITY REVERSAL TIMING
            st.subheader("📅 Musim Reversal Historis IHSG (Seasonality Window)")
            s1, s2 = st.columns(2)
            with s1:
                st.metric("Bulan Reversal Naik Terkuat", f"🗓️ {outlook.get('best_seasonal_month')}", f"{outlook.get('best_seasonal_win_rate'):.1f}% Win Rate Historis")
            with s2:
                st.metric("Bulan Konsolidasi/Terlemah", f"⚠️ {outlook.get('worst_seasonal_month')}", f"{outlook.get('worst_seasonal_win_rate'):.1f}% Win Rate Historis")

            st.divider()

            # TECHNICAL LEVEL TABLES
            st.subheader("📐 Level Confluence Support & Resistance (Fibonacci 5-Tahun)")
            fibs = outlook.get("fib_levels", {})
            pivs = outlook.get("monthly_pivots", {})
            if fibs and pivs:
                level_df = pd.DataFrame([
                    {"Kategori": "Top Resistance 2", "Tipe Level": "Fibonacci Extension 161.8%", "Nilai IHSG": f"{fibs.get('fib_exp_1618', 0):,.0f}"},
                    {"Kategori": "Top Resistance 1", "Tipe Level": "Fibonacci Extension 127.2%", "Nilai IHSG": f"{fibs.get('fib_exp_1272', 0):,.0f}"},
                    {"Kategori": "Monthly Pivot R1", "Tipe Level": "TradingView Monthly R1", "Nilai IHSG": f"{pivs.get('R1', 0):,.0f}"},
                    {"Kategori": "MA50 Weekly (Reversal Line)", "Tipe Level": "Weekly 50 Moving Average", "Nilai IHSG": f"{outlook.get('ma50_weekly', 0):,.0f}"},
                    {"Kategori": "Monthly Pivot S1", "Tipe Level": "TradingView Monthly S1", "Nilai IHSG": f"{pivs.get('S1', 0):,.0f}"},
                    {"Kategori": "Fibonacci 50.0%", "Tipe Level": "5-Year Retracement 50.0%", "Nilai IHSG": f"{fibs.get('fib_500', 0):,.0f}"},
                    {"Kategori": "Fibonacci 61.8% (Golden Pocket)", "Tipe Level": "5-Year Retracement 61.8%", "Nilai IHSG": f"{fibs.get('fib_618', 0):,.0f}"},
                    {"Kategori": "Bottom Support Confluence", "Tipe Level": "Zona Support Terkuat", "Nilai IHSG": f"{outlook.get('bottom_confluence_level', 0):,.0f}"},
                    {"Kategori": "MA200 Weekly (Major Base)", "Tipe Level": "Weekly 200 Moving Average", "Nilai IHSG": f"{outlook.get('ma200_weekly', 0):,.0f}"},
                ])
                st.dataframe(level_df, use_container_width=True, hide_index=True)
        else:
            st.info("Memuat data 1-Year Outlook IHSG...")


# === PAGE: ML Validation ===

elif page == "🤖 ML Validation":
    st.title("🤖 ML Validation (Multi-Day & Live Predictions)")
    
    tab_perf, tab_live, tab_nextday, tab_backtest, tab_sim, tab_candle = st.tabs([
        "📊 ML Performance & Live Validation",
        "🔴 Live Predictions", 
        "🔮 Next-Day Predictions", 
        "🧪 Backtest Metrics", 
        "💸 Trading Simulator",
        "🕯️ Candlestick Screener"
    ])
    
    with tab_perf:
        st.header("📊 ML Prediction Performance & Live Validation Analytics")
        st.caption("Evaluasi statistik performa riil, akurasi sinyal, realized return, dan visualisasi hasil prediksi machine learning yang divalidasi EOD.")
        
        from datetime import datetime, timedelta
        from db import SessionLocal
        from db.models import MlPredictionLog
        import pandas as pd
        import numpy as np
        import plotly.express as px
        import plotly.graph_objects as go
        
        # --- TOP CONTROLS & FILTERS ---
        col_f1, col_f2, col_f3, col_f4, col_f5 = st.columns([2, 1.2, 1.5, 2, 2])
        with col_f1:
            end_default = datetime.now().date()
            start_default = end_default - timedelta(days=90)
            date_filter = st.date_input(
                "📅 Periode Trade Date",
                value=(start_default, end_default),
                key="perf_date_range_picker"
            )
        with col_f2:
            horizon_filter = st.selectbox("⏳ Horizon", ["ALL", "1d", "3d", "5d", "7d"], index=0, key="perf_horizon_sel")
        with col_f3:
            ticker_filter = st.text_input("🔍 Filter Ticker", value="", placeholder="cth: BBCA", key="perf_ticker_input").strip().upper()
        with col_f4:
            min_prob_filter = st.slider("🎯 Min Prob (%)", min_value=40.0, max_value=90.0, value=50.0, step=1.0, key="perf_min_prob_slider")
        with col_f5:
            st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
            if st.button("🔄 Validate Unverified Now", type="primary", key="btn_run_val_perf_top"):
                with st.spinner("Menjalankan validasi EOD untuk log prediksi di DB..."):
                    import subprocess, sys
                    res = subprocess.run([sys.executable, "scripts/cron_ml_validate.py"], capture_output=True, text=True)
                    if res.returncode == 0:
                        st.success("✅ Validasi EOD selesai dijalankan!")
                        st.rerun()
                    else:
                        st.error(f"❌ Validasi error: {res.stderr}")

        st.divider()

        # Fetch Data from Database
        session = SessionLocal()
        try:
            query = session.query(MlPredictionLog)
            
            # Apply Date Range filter
            if isinstance(date_filter, (tuple, list)) and len(date_filter) == 2:
                query = query.filter(MlPredictionLog.trade_date >= date_filter[0], MlPredictionLog.trade_date <= date_filter[1])
            elif isinstance(date_filter, (tuple, list)) and len(date_filter) == 1:
                query = query.filter(MlPredictionLog.trade_date >= date_filter[0])
                
            # Apply Horizon filter
            if horizon_filter != "ALL":
                query = query.filter(MlPredictionLog.horizon == horizon_filter)
                
            # Apply Ticker filter
            if ticker_filter:
                query = query.filter(MlPredictionLog.ticker.like(f"%{ticker_filter}%"))
                
            all_logs = query.order_by(MlPredictionLog.trade_date.desc(), MlPredictionLog.ticker).all()
            
            if not all_logs:
                st.warning("⚠️ Tidak ada log prediksi ML yang ditemukan dengan filter saat ini.")
            else:
                # Convert logs to DataFrame
                records = []
                for l in all_logs:
                    raw_prob = float(l.pred_return_pct) if l.pred_return_pct is not None else 0.0
                    prob_pct = raw_prob * 100.0 if raw_prob <= 1.0 else raw_prob
                    act_ret = float(l.actual_return_pct) if l.actual_return_pct is not None else None
                    act_close = float(l.actual_close_price) if l.actual_close_price is not None else None
                    
                    records.append({
                        "id": l.id,
                        "trade_date": l.trade_date,
                        "ticker": l.ticker,
                        "horizon": l.horizon,
                        "prob_pct": prob_pct,
                        "pred_price": float(l.pred_price) if l.pred_price else None,
                        "actual_close": act_close,
                        "actual_return_pct": act_ret,
                        "is_correct": l.is_correct,
                        "validated": act_close is not None
                    })
                
                df_perf = pd.DataFrame(records)
                
                # Filter by Min Prob
                df_filtered = df_perf[df_perf["prob_pct"] >= min_prob_filter].copy()
                df_validated = df_filtered[df_filtered["validated"] & df_filtered["actual_return_pct"].notnull()].copy()
                
                # --- KPI CARDS ---
                st.subheader("🎯 Ringkasan Kinerja & Indikator Validasi")
                kpi_col1, kpi_col2, kpi_col3, kpi_col4, kpi_col5 = st.columns(5)
                
                total_val = len(df_validated)
                if total_val > 0:
                    correct_cnt = int(df_validated["is_correct"].sum())
                    hit_rate = (correct_cnt / total_val) * 100.0
                    
                    buy_signals = df_validated[df_validated["prob_pct"] >= min_prob_filter]
                    win_trades = len(buy_signals[buy_signals["actual_return_pct"] > 0])
                    loss_trades = len(buy_signals[buy_signals["actual_return_pct"] <= 0])
                    
                    avg_ret = buy_signals["actual_return_pct"].mean() if not buy_signals.empty else 0.0
                    total_cum_ret = buy_signals["actual_return_pct"].sum() if not buy_signals.empty else 0.0
                    
                    kpi_col1.metric("🎯 Hit Rate (Accuracy)", f"{hit_rate:.1f}%", f"{correct_cnt} benar dari {total_val}")
                    kpi_col2.metric("💰 Realized Return", f"{total_cum_ret:+.2f}%", f"Kumulatif {len(buy_signals)} sinyal")
                    kpi_col3.metric("⚖️ Win / Loss", f"{win_trades} W / {loss_trades} L", f"Win Rate: {(win_trades/max(1, win_trades+loss_trades))*100:.1f}%")
                    kpi_col4.metric("📈 Rata-rata Return / Trade", f"{avg_ret:+.2f}%", "Per Sinyal Validated")
                    kpi_col5.metric("📦 Validated Logs", f"{total_val} Log", f"Dari {len(df_filtered)} total log")
                else:
                    kpi_col1.metric("🎯 Hit Rate (Accuracy)", "N/A", "Belum ada log tervalidasi")
                    kpi_col2.metric("💰 Realized Return", "N/A", "-")
                    kpi_col3.metric("⚖️ Win / Loss", "N/A", "-")
                    kpi_col4.metric("📈 Rata-rata Return", "N/A", "-")
                    kpi_col5.metric("📦 Validated Logs", "0 Log", f"Dari {len(df_filtered)} total log")
                    st.info("💡 Belum ada data tervalidasi EOD. Klik tombol **🔄 Validate Unverified Now** di atas untuk mengambil harga EOD terbaru.")

                st.write("---")

                if not df_validated.empty:
                    # --- CHARTS SECTION 1: EQUITY CURVE & PROBABILITY BINS ---
                    ch_col1, ch_col2 = st.columns(2)
                    
                    with ch_col1:
                        st.subheader("📈 Kurva Returns Kumulatif (Equity Curve)")
                        df_daily = df_validated.groupby("trade_date")["actual_return_pct"].agg(["mean", "sum", "count"]).reset_index()
                        df_daily = df_daily.sort_values("trade_date")
                        df_daily["cum_return"] = df_daily["sum"].cumsum()
                        
                        fig_eq = px.line(
                            df_daily, 
                            x="trade_date", 
                            y="cum_return", 
                            markers=True,
                            title="Akumulasi Realized Return (%) dari Sinyal ML Validated",
                            labels={"trade_date": "Tanggal Trade", "cum_return": "Cumulative Return (%)"}
                        )
                        fig_eq.update_traces(line_color="#00CC96", line_width=3)
                        fig_eq.update_layout(template="plotly_dark", height=380)
                        st.plotly_chart(fig_eq, use_container_width=True)

                    with ch_col2:
                        st.subheader("📊 Akurasi Berdasarkan Level Keyakinan (Probability Bin)")
                        bins = [40, 50, 55, 60, 65, 70, 100]
                        labels = ["40-50%", "50-55%", "55-60%", "60-65%", "65-70%", "70%+"]
                        df_validated["prob_bin"] = pd.cut(df_validated["prob_pct"], bins=bins, labels=labels, right=False)
                        
                        bin_stats = df_validated.groupby("prob_bin", observed=False).agg(
                            total=("is_correct", "count"),
                            correct=("is_correct", lambda x: int(x.sum())),
                            avg_return=("actual_return_pct", "mean")
                        ).reset_index()
                        bin_stats["accuracy"] = np.where(bin_stats["total"] > 0, (bin_stats["correct"] / bin_stats["total"]) * 100.0, 0.0)
                        
                        fig_bin = px.bar(
                            bin_stats,
                            x="prob_bin",
                            y="accuracy",
                            text="total",
                            color="accuracy",
                            color_continuous_scale="Viridis",
                            title="Tingkat Akurasi (%) per Range Probabilitas AI",
                            labels={"prob_bin": "Probability Bin (%)", "accuracy": "Accuracy (%)"}
                        )
                        fig_bin.update_traces(texttemplate="%{text} log", textposition="outside")
                        fig_bin.update_layout(template="plotly_dark", height=380, yaxis_range=[0, 100])
                        st.plotly_chart(fig_bin, use_container_width=True)

                    st.write("---")

                    # --- CHARTS SECTION 2: TICKER LEADERBOARD & CONFUSION MATRIX ---
                    ch_col3, ch_col4 = st.columns(2)
                    
                    with ch_col3:
                        st.subheader("🏆 Leaderboard Performa Ticker Saham")
                        ticker_stats = df_validated.groupby("ticker").agg(
                            total=("is_correct", "count"),
                            correct=("is_correct", lambda x: int(x.sum())),
                            tot_return=("actual_return_pct", "sum"),
                            avg_return=("actual_return_pct", "mean")
                        ).reset_index()
                        ticker_stats["acc_pct"] = (ticker_stats["correct"] / ticker_stats["total"]) * 100.0
                        ticker_stats = ticker_stats.sort_values(by=["acc_pct", "tot_return"], ascending=[False, False])
                        
                        st.markdown("**Top 5 Ticker Terakurat ML:**")
                        top_5 = ticker_stats.head(5).copy()
                        top_5["acc_str"] = top_5["acc_pct"].apply(lambda x: f"{x:.1f}%")
                        top_5["ret_str"] = top_5["tot_return"].apply(lambda x: f"{x:+.2f}%")
                        st.dataframe(top_5[["ticker", "total", "acc_str", "ret_str"]].rename(columns={
                            "ticker": "Ticker", "total": "Total Validated", "acc_str": "Accuracy", "ret_str": "Tot Return"
                        }), use_container_width=True, hide_index=True)
                        
                        st.markdown("**5 Ticker dengan Performa Terendah:**")
                        bot_5 = ticker_stats.tail(5).copy()
                        bot_5["acc_str"] = bot_5["acc_pct"].apply(lambda x: f"{x:.1f}%")
                        bot_5["ret_str"] = bot_5["tot_return"].apply(lambda x: f"{x:+.2f}%")
                        st.dataframe(bot_5[["ticker", "total", "acc_str", "ret_str"]].rename(columns={
                            "ticker": "Ticker", "total": "Total Validated", "acc_str": "Accuracy", "ret_str": "Tot Return"
                        }), use_container_width=True, hide_index=True)

                    with ch_col4:
                        st.subheader("🧩 Confusion Matrix & Performa Per Horizon")
                        tp = len(df_validated[(df_validated["prob_pct"] >= min_prob_filter) & (df_validated["actual_return_pct"] > 0)])
                        fp = len(df_validated[(df_validated["prob_pct"] >= min_prob_filter) & (df_validated["actual_return_pct"] <= 0)])
                        tn = len(df_validated[(df_validated["prob_pct"] < min_prob_filter) & (df_validated["actual_return_pct"] <= 0)])
                        fn = len(df_validated[(df_validated["prob_pct"] < min_prob_filter) & (df_validated["actual_return_pct"] > 0)])
                        
                        cm_matrix = [[tp, fp], [fn, tn]]
                        
                        fig_cm = px.imshow(
                            cm_matrix,
                            labels=dict(x="Actual Movement", y="Predicted Signal", color="Count"),
                            x=["Price NAIK (>0%)", "Price TURUN/FLAT (<=0%)"],
                            y=["BUY Signal (High Prob)", "NO BUY Signal (Low Prob)"],
                            text_auto=True,
                            color_continuous_scale="Blues",
                            title="Matriks Prediksi vs Pergerakan Riil"
                        )
                        fig_cm.update_layout(template="plotly_dark", height=320)
                        st.plotly_chart(fig_cm, use_container_width=True)
                        
                        horiz_stats = df_validated.groupby("horizon").agg(
                            total=("is_correct", "count"),
                            correct=("is_correct", lambda x: int(x.sum())),
                            tot_return=("actual_return_pct", "sum")
                        ).reset_index()
                        horiz_stats["Accuracy (%)"] = (horiz_stats["correct"] / horiz_stats["total"]) * 100.0
                        horiz_stats["Accuracy (%)"] = horiz_stats["Accuracy (%)"].map("{:.1f}%".format)
                        horiz_stats["Total Return (%)"] = horiz_stats["tot_return"].map("{:+.2f}%".format)
                        st.dataframe(horiz_stats[["horizon", "total", "Accuracy (%)", "Total Return (%)"]].rename(columns={"horizon": "Horizon", "total": "Validated Logs"}), use_container_width=True, hide_index=True)

                # --- DATA TABLE OF ALL LOGS ---
                st.write("---")
                st.subheader("📋 Log Detail Prediksi & Validasi ML")
                
                df_table = df_filtered.copy()
                df_table["Status"] = df_table.apply(
                    lambda r: "✅ Correct" if r["is_correct"] == True else ("❌ Incorrect" if r["is_correct"] == False else "⏳ Pending Validasi"),
                    axis=1
                )
                df_table["Prob %"] = df_table["prob_pct"].apply(lambda x: f"{x:.2f}%")
                df_table["Actual Close"] = df_table["actual_close"].apply(lambda x: f"Rp {x:,.0f}" if x is not None else "-")
                df_table["Actual Return"] = df_table["actual_return_pct"].apply(lambda x: f"{x:+.2f}%" if x is not None else "-")
                df_table["Pred Price"] = df_table["pred_price"].apply(lambda x: f"Rp {x:,.0f}" if x is not None else "-")
                
                display_cols = ["trade_date", "ticker", "horizon", "Prob %", "Pred Price", "Actual Close", "Actual Return", "Status"]
                st.dataframe(df_table[display_cols].rename(columns={
                    "trade_date": "Trade Date", "ticker": "Ticker", "horizon": "Horizon"
                }), use_container_width=True, hide_index=True)
                
                csv_data = df_table.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Download CSV Detailed Performance Logs",
                    data=csv_data,
                    file_name=f"ml_performance_validation_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv"
                )
        except Exception as e:
            st.error(f"❌ Gagal memuat data ML Performance: {e}")
        finally:
            session.close()

    with tab_nextday:
        st.header("🔮 Prediksi ML Hari Perdagangan Berikutnya (Next-Day)")
        st.caption("Memprediksi pergerakan harga saham untuk hari bursa berikutnya berdasarkan penutupan bursa terakhir (EOD). Hasil otomatis tersimpan di Database.")
        
        from scripts.cron_ml_predict import get_next_trading_day, run_ml_prediction
        from db import SessionLocal
        from db.models import MlPredictionLog
        import pandas as pd
        
        default_next_dt = get_next_trading_day()
        
        col_nd1, col_nd2, col_nd3 = st.columns([2, 2, 2])
        with col_nd1:
            sel_date = st.date_input("Target Trade Date", value=default_next_dt)
        with col_nd2:
            min_prob_filter = st.slider("Min. 1D Prob (%)", min_value=40.0, max_value=95.0, value=50.0, step=1.0)
        with col_nd3:
            signal_filter = st.selectbox("Filter Sinyal", ["Semua Sinyal", "Hanya BUY / STRONG BUY", "Hanya STRONG BUY"])
            
        col_btn_nd1, col_btn_nd2 = st.columns([2, 4])
        with col_btn_nd1:
            if st.button("🚀 Run & Save Next-Day Predictions", type="primary"):
                with st.spinner(f"Menjalankan ML MultiDayPredictor untuk target {sel_date.strftime('%Y-%m-%d')}..."):
                    count = run_ml_prediction(target_date=sel_date)
                    st.success(f"✅ Prediksi berhasil dihitung & disimpan ke DB ({count} ticker untuk {sel_date})!")
                    st.rerun()
                    
        st.divider()
        
        session = SessionLocal()
        try:
            next_logs = session.query(MlPredictionLog).filter(MlPredictionLog.trade_date == sel_date).order_by(MlPredictionLog.ticker).all()
            if next_logs:
                pivot_dict = {}
                for l in next_logs:
                    key = l.ticker
                    if key not in pivot_dict:
                        pivot_dict[key] = {
                            "Ticker": l.ticker,
                            "Trade Date": str(l.trade_date),
                            "Sinyal 1D": "-",
                            "1D Prob (%)": "-",
                            "Sinyal 3D": "-",
                            "3D Prob (%)": "-",
                            "Sinyal 5D": "-",
                            "5D Prob (%)": "-",
                            "Sinyal 7D": "-",
                            "7D Prob (%)": "-",
                            "Target Price (1D)": "-"
                        }
                    
                    raw_prob = float(l.pred_return_pct) if l.pred_return_pct is not None else 0.0
                    prob_pct = raw_prob * 100.0 if raw_prob <= 1.0 else raw_prob
                    prob_str = f"{prob_pct:.2f}%"
                    
                    is_horizon_buy = (prob_pct >= min_prob_filter)
                    
                    if is_horizon_buy:
                        if prob_pct >= 55.0:
                            sig_label = "🔥 STRONG BUY"
                        else:
                            sig_label = "🟢 BUY"
                    else:
                        sig_label = "-"
                    
                    if l.horizon == "1d":
                        pivot_dict[key]["Sinyal 1D"] = sig_label
                        pivot_dict[key]["1D Prob (%)"] = prob_str if is_horizon_buy else "-"
                        if l.pred_price and is_horizon_buy:
                            pivot_dict[key]["Target Price (1D)"] = f"Rp {float(l.pred_price):,.0f}"
                    elif l.horizon == "3d":
                        pivot_dict[key]["Sinyal 3D"] = sig_label
                        pivot_dict[key]["3D Prob (%)"] = prob_str if is_horizon_buy else "-"
                    elif l.horizon == "5d":
                        pivot_dict[key]["Sinyal 5D"] = sig_label
                        pivot_dict[key]["5D Prob (%)"] = prob_str if is_horizon_buy else "-"
                    elif l.horizon == "7d":
                        pivot_dict[key]["Sinyal 7D"] = sig_label
                        pivot_dict[key]["7D Prob (%)"] = prob_str if is_horizon_buy else "-"
                
                df_next = pd.DataFrame(list(pivot_dict.values()))
                
                # Filter baris yang punya minimal 1 horizon BUY / STRONG BUY
                def is_any_buy(row):
                    for col in ["Sinyal 1D", "Sinyal 3D", "Sinyal 5D", "Sinyal 7D"]:
                        if row.get(col, "-") in ["🔥 STRONG BUY", "🟢 BUY"]:
                            return True
                    return False
                    
                df_next = df_next[df_next.apply(is_any_buy, axis=1)]
                
                if signal_filter == "Hanya STRONG BUY":
                    df_next = df_next[
                        (df_next["Sinyal 1D"] == "🔥 STRONG BUY") |
                        (df_next["Sinyal 3D"] == "🔥 STRONG BUY") |
                        (df_next["Sinyal 5D"] == "🔥 STRONG BUY") |
                        (df_next["Sinyal 7D"] == "🔥 STRONG BUY")
                    ]
                    
                if not df_next.empty:
                    st.dataframe(df_next, use_container_width=True, hide_index=True)
                    
                    csv = df_next.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="📥 Download CSV Hasil Prediksi Next-Day",
                        data=csv,
                        file_name=f"ml_nextday_predictions_{sel_date}.csv",
                        mime="text/csv"
                    )
                else:
                    st.warning("Tidak ada data prediksi yang memenuhi kriteria filter.")
            else:
                st.info(f"Belum ada data prediksi tersimpan di DB untuk tanggal target {sel_date}. Klik tombol **🚀 Run & Save Next-Day Predictions** di atas untuk membuat prediksi baru.")
        except Exception as e:
            st.error(f"Gagal membaca data dari DB: {e}")
        finally:
            session.close()

    with tab_live:
        st.header("🔮 Prediksi ML Hari Ini")
        
        # Tambahan Tombol Validasi Manual
        col_btn1, col_btn2 = st.columns([1, 4])
        with col_btn1:
            if st.button("🔄 Validasi Manual EOD", type="primary"):
                with st.spinner("Menjalankan skrip cron_ml_validate.py..."):
                    import subprocess
                    result = subprocess.run(
                        ["python", "scripts/cron_ml_validate.py"],
                        capture_output=True,
                        text=True
                    )
                    if result.returncode == 0:
                        st.success("✅ Validasi EOD selesai dijalankan!")
                        st.rerun()
                    else:
                        st.error(f"❌ Error: {result.stderr}")
                        
        st.caption("Hasil prediksi Cron Job Pagi (06:00) yang belum atau sudah divalidasi Cron Sore (18:00)")
        
        show_only_buy = st.checkbox("🟢 Hanya tampilkan saham sinyal NAIK / BUY (Prob ≥ 50% pada 1D, 3D, 5D, atau 7D)", value=True)
        
        st.info("**Cara Membaca Angka Probabilitas (Prob):**\n"
                "- **1D Prob:** Peluang harga naik > 0.2% besok (Cocok untuk Day Trading / ODT)\n"
                "- **3D Prob:** Peluang harga naik > 1.0% dlm 3 hari bursa (Cocok untuk Swing Pendek)\n"
                "- **5D Prob:** Peluang harga naik > 1.5% dlm 5 hari bursa\n"
                "- **7D Prob:** Peluang harga naik > 2.0% dlm 7 hari bursa\n"
                "\n*Makin mendekati 100%, makin kuat keyakinan mesin ML bahwa saham ini akan hijau.*")
        
        from db import SessionLocal
        from db.models import MlPredictionLog
        import pandas as pd
        
        session = SessionLocal()
        try:
            logs = session.query(MlPredictionLog).order_by(MlPredictionLog.trade_date.desc(), MlPredictionLog.ticker).limit(2000).all()
            if logs:
                # Pivot data so that 1 ticker = 1 row per date
                pivot_dict = {}
                for l in logs:
                    key = (l.trade_date, l.ticker)
                    if key not in pivot_dict:
                        pivot_dict[key] = {
                            "Trade Date": l.trade_date,
                            "Ticker": l.ticker,
                            "Pred 1D": "-",
                            "1D Prob (%)": "-",
                            "Val 1D": "-",
                            "Pred 3D": "-",
                            "3D Prob (%)": "-",
                            "Val 3D": "-",
                            "Pred 5D": "-",
                            "5D Prob (%)": "-",
                            "Val 5D": "-",
                            "Pred 7D": "-",
                            "7D Prob (%)": "-",
                            "Val 7D": "-"
                        }
                    
                    raw_pred = float(l.pred_return_pct) if l.pred_return_pct is not None else 0.0
                    prob_pct = raw_pred * 100.0 if raw_pred <= 1.0 else raw_pred
                    prob_str = f"{prob_pct:.2f}%"
                    status_icon = "⏳"
                    if l.is_correct is not None:
                        status_icon = "✅" if l.is_correct else "❌"
                    
                    # Threshold dinaikkan jadi 54.0% agar tidak banyak "False Positive" di masa sideways
                    is_horizon_naik = (raw_pred >= 0.54 or prob_pct >= 54.0)
                    
                    if l.horizon == "1d":
                        pivot_dict[key]["Pred 1D"] = "📈 NAIK" if is_horizon_naik else "-"
                        pivot_dict[key]["1D Prob (%)"] = prob_str if is_horizon_naik else "-"
                        pivot_dict[key]["Val 1D"] = status_icon if is_horizon_naik else "-"
                    elif l.horizon == "3d":
                        pivot_dict[key]["Pred 3D"] = "📈 NAIK" if is_horizon_naik else "-"
                        pivot_dict[key]["3D Prob (%)"] = prob_str if is_horizon_naik else "-"
                        pivot_dict[key]["Val 3D"] = status_icon if is_horizon_naik else "-"
                    elif l.horizon == "5d":
                        pivot_dict[key]["Pred 5D"] = "📈 NAIK" if is_horizon_naik else "-"
                        pivot_dict[key]["5D Prob (%)"] = prob_str if is_horizon_naik else "-"
                        pivot_dict[key]["Val 5D"] = status_icon if is_horizon_naik else "-"
                    elif l.horizon == "7d":
                        pivot_dict[key]["Pred 7D"] = "📈 NAIK" if is_horizon_naik else "-"
                        pivot_dict[key]["7D Prob (%)"] = prob_str if is_horizon_naik else "-"
                        pivot_dict[key]["Val 7D"] = status_icon if is_horizon_naik else "-"

                df_live = pd.DataFrame(list(pivot_dict.values()))
                
                # Filter hanya ticker yang punya prob >= 50% di minimal salah satu horizon
                def is_any_horizon_buy(row):
                    for h_col in ["1D Prob (%)", "3D Prob (%)", "5D Prob (%)", "7D Prob (%)"]:
                        val_str = str(row.get(h_col, "-"))
                        try:
                            val_num = float(val_str.replace("%", ""))
                            if val_num >= 54.0:
                                return True
                        except ValueError:
                            pass
                    return False

                if show_only_buy:
                    df_live = df_live[df_live.apply(is_any_horizon_buy, axis=1)]

                def extract_prob(val):
                    try:
                        return float(val.replace("%", ""))
                    except:
                        return 0.0
                        
                df_live["sort_val"] = df_live["1D Prob (%)"].apply(extract_prob)
                df_live = df_live.sort_values(by=["Trade Date", "sort_val"], ascending=[False, False]).drop(columns=["sort_val"])
                    
                if not df_live.empty:
                    st.dataframe(df_live, use_container_width=True, hide_index=True)
                else:
                    st.warning("Tidak ada saham dengan sinyal NAIK / BUY (Prob ≥ 50%) pada tanggal ini.")
                
                # Hit Rate Stats
                st.subheader("Statistik Hit Rate (Per Row Tervalidasi)")
                # Hitung berdasarkan data asli untuk akurasi persis
                val_logs = [l for l in logs if l.is_correct is not None]
                if val_logs:
                    benar = sum(1 for l in val_logs if l.is_correct)
                    total = len(val_logs)
                    st.metric("Akurasi Real-Time", f"{(benar/total)*100:.1f}%", f"{benar} benar dari {total} prediksi divalidasi")
                else:
                    st.info("Belum ada data yang divalidasi oleh Cron EOD 23:00.")
            else:
                st.warning("Belum ada log prediksi di database. Cron mungkin belum berjalan hari ini.")
        except Exception as e:
            st.error(f"Gagal mengambil data live: {e}")
        finally:
            session.close()

    with tab_backtest:
        st.header("🧪 Metrik Backtest Model")
        st.caption("Menampilkan hasil akurasi model LightGBM dari `scripts/train_multiday_model.py`")

        import os
        import json
        import pandas as pd

    meta_path = "models/checkpoints/lgbm_multiday_meta.json"
    if os.path.exists(meta_path):
        try:
            with open(meta_path, 'r') as f:
                meta = json.load(f)
            
            st.success(f"✅ Data model berhasil di-*load* (Trained at: {meta.get('run_date', 'Unknown')})")
            
            config = meta.get("config", {})
            rows = meta.get("rows", {})
            macro_avg = meta.get("holdout_metrics_macro_avg", {})
            tickers_data = meta.get("tickers", [])
            
            col1, col2, col3 = st.columns(3)
            col1.metric("Tickers Trained", rows.get("tickers_trained", 0))
            col2.metric("Total Training Rows", f"{rows.get('final_train_rows', 0):,}")
            col3.metric("Test Data Rows", f"{rows.get('holdout_test_rows', 0):,}")
            
            st.write("---")
            st.subheader("📋 Detail Per Ticker")
            
            if tickers_data:
                # Siapkan data untuk tabel per ticker
                table_data = []
                for t in tickers_data:
                    ticker = t.get("ticker", "UNKNOWN")
                    metrics = t.get("metrics", {})
                    
                    row_data = {
                        "Ticker": ticker,
                        "Tested Rows": t.get("test_rows", 0)
                    }
                    
                    for h in ["1d", "3d", "5d", "7d"]:
                        if h in metrics:
                            m = metrics[h]
                            # Tandai model degenerate: hampir tidak pernah (atau hampir
                            # selalu) memberi sinyal BUY, jadi akurasinya cuma
                            # memantulkan base rate, bukan kemampuan.
                            flag = " ⚠️" if m.get("degenerate") else ""
                            lift = m.get("lift", 0) or 0
                            row_data[f"T_{h.upper()} Acc"] = f"{m.get('accuracy', 0)}%"
                            row_data[f"T_{h.upper()} Base"] = f"{m.get('base_rate', 0)}%"
                            row_data[f"T_{h.upper()} Lift"] = f"{lift:.2f}{flag}"
                            row_data[f"T_{h.upper()} Buy Prec"] = f"{m.get('buy_precision', 0)}%"
                            row_data[f"T_{h.upper()} Buy Rec"] = f"{m.get('buy_recall', 0)}%"
                        else:
                            row_data[f"T_{h.upper()} Acc"] = "-"
                            row_data[f"T_{h.upper()} Base"] = "-"
                            row_data[f"T_{h.upper()} Lift"] = "-"
                            row_data[f"T_{h.upper()} Buy Prec"] = "-"
                            row_data[f"T_{h.upper()} Buy Rec"] = "-"
                            
                    table_data.append(row_data)
                
                df_tickers = pd.DataFrame(table_data)
                st.dataframe(df_tickers, use_container_width=True)
                
            else:
                st.warning("Data per ticker tidak ditemukan di metadata.")
                
            st.subheader("📊 Macro Average Accuracy (Across All Tickers)")
            
            if macro_avg:
                horizons = list(macro_avg.keys())
                
                # Buat DataFrame untuk tabel
                df_metrics = []
                for h in horizons:
                    m = macro_avg[h]
                    acc = m.get("accuracy", 0)
                    base_line = m.get("majority_baseline", 0)
                    df_metrics.append({
                        "Horizon": h.upper(),
                        "Accuracy (%)": acc,
                        "Majority Baseline (%)": base_line,
                        # Kolom inilah penilaian sebenarnya: accuracy hanya berarti
                        # kalau melewati baseline kelas mayoritas.
                        "vs Baseline (pp)": round(acc - base_line, 2),
                        "Base Rate (%)": m.get("base_rate", 0),
                        "Buy Precision (%)": m.get("buy_precision", 0),
                        "Lift": m.get("lift", 0),
                        "Buy Recall (%)": m.get("buy_recall", 0),
                        "Model Usable": m.get("n_usable", 0),
                        "Degenerate": m.get("n_degenerate", 0),
                        "Holdout Rows": m.get("test_rows", 0)
                    })
                
                df_metrics_pd = pd.DataFrame(df_metrics)
                
                # Tampilkan metrik utama sebagai columns
                st.write("---")
                h_cols = st.columns(len(horizons))
                for idx, h in enumerate(horizons):
                    with h_cols[idx]:
                        m = macro_avg[h]
                        acc = m.get("accuracy", 0)
                        base_line = m.get("majority_baseline", 0)
                        lift_val = m.get("lift", 0) or 0
                        # delta dipakai supaya Streamlit mewarnai merah otomatis kalau
                        # negatif — accuracy di bawah baseline harus langsung terlihat,
                        # bukan tersembunyi di balik angka yang kelihatan besar.
                        st.metric(
                            label=f"Horizon {h.upper()} Accuracy", value=f"{acc}%",
                            delta=f"{acc - base_line:+.2f} pp vs baseline",
                        )
                        st.metric(
                            label=f"Horizon {h.upper()} Lift", value=f"{lift_val:.3f}",
                            delta=f"{lift_val - 1:+.3f} vs nol-skill",
                        )
                        st.metric(label=f"Horizon {h.upper()} Buy Precision", value=f"{m.get('buy_precision', 0)}%")
                        
                st.write("---")
                st.write("**Detail Metrik per Horizon Timeframe:**")
                st.dataframe(df_metrics_pd, use_container_width=True)
                
                st.info("💡 **Penjelasan Singkat Metrik Model:**\n"
                        "- **Base Rate**: Seberapa sering harga memang naik melewati ambang target, **tanpa model apa pun**. Ini titik nol pembandingnya.\n"
                        "- **Majority Baseline**: Accuracy yang didapat kalau model selalu menjawab \"tidak naik\". "
                        "Accuracy di bawah angka ini berarti model **kalah dari konstanta** — jadi jangan menilai Accuracy tanpa melihat kolom ini.\n"
                        "- **Accuracy**: Seberapa sering model menebak benar arah harga. Hanya bermakna kalau melewati Majority Baseline.\n"
                        "- **Buy Precision**: Tingkat ketepatan sinyal BUY. Jika 40%, dari 10 rekomendasi BUY, 4 terbukti naik.\n"
                        "- **Lift**: Buy Precision dibagi Base Rate. **1.00 = nol skill** (sinyal BUY tidak lebih baik daripada menebak sesuai proporsi pasar). "
                        "Inilah metrik yang sebenarnya menentukan apakah model berguna, bukan Accuracy.\n"
                        "- **Buy Recall**: Sensitivitas menangkap peluang naik. Dari 100 saham yang benar-benar naik, berapa % yang tertangkap sebagai BUY.\n"
                        "- **Model Usable / Degenerate**: Model degenerate hampir tidak pernah (atau hampir selalu) memberi sinyal BUY, "
                        "sehingga Accuracy-nya cuma memantulkan Base Rate. Model seperti ini **dikeluarkan** dari rata-rata di atas dan ditandai ⚠️ di tabel per-ticker.\n"
                        "- **Holdout Rows**: Jumlah baris data uji (data historis yang **diisolasi** dan TIDAK PERNAH dipakai saat training).")
                
            else:
                st.warning("Belum ada data evaluasi holdout di metadata saat ini.")
                
        except Exception as e:
            st.error(f"Gagal membaca file JSON meta model: {str(e)}")
    else:
        st.warning("⚠️ File hasil training multiday (`models/checkpoints/lgbm_multiday_meta.json`) tidak ditemukan. Silakan jalankan `python scripts/train_multiday_model.py --all`.")

    with tab_sim:
        st.header("💸 Trading Simulator (ML Driven)")
        st.caption("Mengeksekusi backtest P&L dengan sinyal dari model AI yang sudah dilatih, hasil otomatis tersimpan di Database.")
        
        # Section History Sim
        st.markdown("### 🗄️ Histori Simulasi (Tersimpan di Database)")
        try:
            from db import SessionLocal
            from db.models import BacktestSession, BacktestResult # type: ignore
            db = SessionLocal()
            sessions = db.query(BacktestSession).order_by(BacktestSession.run_date.desc()).limit(5).all()
            if not sessions:
                st.info("Belum ada histori simulasi.")
            else:
                for s in sessions:
                    res_count = db.query(BacktestResult).filter(BacktestResult.session_id == s.id).count()
                    date_range = f" | Periode: {s.start_date} s/d {s.end_date}" if getattr(s, 'start_date', None) and getattr(s, 'end_date', None) else ""
                    with st.expander(f"📁 ID {s.id} | {s.run_date.strftime('%d %b %Y %H:%M')} | Horizon: {s.horizon}{date_range} | Tickers: {res_count} | P&L: Rp {s.total_pnl:,.0f}", expanded=False):
                        # get details
                        results = db.query(BacktestResult).filter(BacktestResult.session_id == s.id).all()
                        for r in results:
                            st.markdown(f"**{r.ticker}** - P&L: Rp {r.total_pnl:,.0f} (Win: {r.win_rate}%) | Trades: {r.total_trades}")
                            if r.trades_json:
                                import pandas as pd
                                df = pd.DataFrame(r.trades_json)
                                if not df.empty:
                                    st.dataframe(df[['buy_date', 'prob', 'buy_price', 'sell_date', 'sell_price', 'pnl_pct']], use_container_width=True)
            db.close()
        except Exception as e:
            st.error(f"Gagal memuat histori DB: {e}")
                
        st.divider()
        col_sim1, col_sim2, col_sim3 = st.columns([2, 1, 1])
        with col_sim1:
            sim_ticker = st.text_input("Ticker (Pisahkan koma, atau 'ALL' untuk semua universe)", value="AMMN, BRPT")
        with col_sim2:
            sim_horizon = st.selectbox("Horizon", ["1d", "3d", "5d", "7d"], index=0)
        with col_sim3:
            sim_threshold = st.number_input("Min. Prob (%)", min_value=40.0, max_value=99.0, value=51.0, step=1.0)
            
        col_sim4, col_sim5, col_sim6 = st.columns([2, 1, 1])
        with col_sim4:
            sim_capital = st.number_input("Initial Capital", value=100_000_000, step=1_000_000)
        with col_sim5:
            sim_start_date = st.date_input("Start Date", value=datetime(2026, 1, 1).date())
        with col_sim6:
            sim_end_date = st.date_input("End Date", value=datetime(2026, 7, 24).date())
            
        if not st.session_state.get("sim_running", False):
            if st.button("🚀 Run Simulator", type="primary"):
                import subprocess
                st.session_state["sim_running"] = True
                
                # Setup output file for background job
                import tempfile
                out_fd, out_path = tempfile.mkstemp(suffix=".txt", prefix="sim_out_")
                st.session_state["sim_out_path"] = out_path
                os.close(out_fd)
                
                cmd = [
                    sys.executable, "scripts/backtest_ml_trading.py",
                    "--ticker", sim_ticker.upper(),
                    "--horizon", sim_horizon,
                    "--threshold", str(sim_threshold / 100.0),
                    "--start", sim_start_date.strftime("%Y-%m-%d"),
                    "--end", sim_end_date.strftime("%Y-%m-%d"),
                    "--capital", str(sim_capital)
                ]
                with open(out_path, "w") as f:
                    p = subprocess.Popen(cmd, stdout=f, stderr=subprocess.STDOUT, preexec_fn=os.setsid)
                
                st.session_state["sim_pid"] = p.pid
                st.rerun()
        else:
            # Fragment to auto-refresh background status
            @st.fragment(run_every="2s")
            def render_sim_status():
                pid = st.session_state.get("sim_pid")
                is_alive = False
                if pid:
                    try:
                        os.kill(pid, 0)
                        is_alive = True
                        try:
                            with open(f"/proc/{pid}/stat", "r") as f:
                                stat_line = f.read()
                                if len(stat_line.split()) >= 3 and stat_line.split()[2] == 'Z':
                                    is_alive = False
                        except Exception:
                            pass
                    except OSError:
                        pass
                
                if is_alive:
                    st.info("⏳ Simulator sedang berjalan di background... (Auto-refresh tiap 2 detik)")
                    if st.button("🛑 Batalkan Simulator"):
                        try:
                            import signal
                            os.killpg(os.getpgid(pid), signal.SIGTERM)
                        except Exception:
                            pass
                        st.session_state["sim_running"] = False
                        st.rerun()
                else:
                    st.success("✅ Simulasi Selesai!")
                    st.session_state["sim_running"] = False
                    
                    # Read output
                    out_path = st.session_state.get("sim_out_path")
                    if out_path and os.path.exists(out_path):
                        with open(out_path, "r") as f:
                            output = f.read()
                        st.session_state["sim_last_output"] = output
                        # st.rerun() dipanggil agar form state bisa keluar dari render_sim_status
                        st.rerun()

            render_sim_status()
            
        # Tampilkan hasil kalau sudah beres
        output = st.session_state.get("sim_last_output")
        if output and not st.session_state.get("sim_running", False):
            if "BACKTEST RESULT" in output or "MULTI-TICKER SUMMARY" in output:
                # Parsing the output to make it native Streamlit UI
                lines = output.split('\n')
                summary_lines = []
                table_lines = []
                multi_ticker_summary = []
                is_table = False
                is_multi = False
                
                for line in lines:
                    if "MULTI-TICKER SUMMARY" in line:
                        is_multi = True
                        
                    if is_multi:
                        if "Total Tickers" in line or "Total Trades" in line or "Initial Port" in line or "Final Port" in line or "Net Port P&L" in line:
                            multi_ticker_summary.append(line)
                            
                    if "buy_date" in line and "sell_date" in line:
                        is_table = True
                        table_lines.append("\n" + line) # Add spacing between tables
                    elif is_table:
                        if line.strip() and not line.startswith("---") and not line.startswith("===") and "Trades   :" not in line and "Net P&L  :" not in line:
                            table_lines.append(line)
                        elif line.startswith("---") and len(line.strip().split()) == 3: # "--- AMMN ---"
                            table_lines.append(line)
                            is_table = False
                            
                    if "BACKTEST RESULT" not in line and "===" not in line and not is_multi and not is_table:
                        if line.strip() and "OHLCV" not in line and "Loaded IHSG" not in line and "Running ML" not in line and "cache hit" not in line and not line.startswith("---") and "Trades   :" not in line and "Net P&L  :" not in line:
                            summary_lines.append(line)
                            
                if multi_ticker_summary:
                    st.markdown("### 🏆 Total Portfolio (Gabungan)")
                    for s_line in multi_ticker_summary:
                        if ":" in s_line:
                            k, v = s_line.split(":", 1)
                            st.markdown(f"**{k.strip()}**: {v.strip()}")
                            
                    st.markdown("### 📊 Ringkasan per Ticker")
                    for s_line in summary_lines:
                        if "---" in s_line:
                            st.markdown(f"**{s_line.strip()}**")
                        else:
                            st.text(s_line.strip())
                else:
                    st.markdown("### 📊 Ringkasan Hasil")
                    for s_line in summary_lines:
                        if ":" in s_line:
                            k, v = s_line.split(":", 1)
                            st.markdown(f"**{k.strip()}**: {v.strip()}")
                
                if table_lines and not multi_ticker_summary:
                    st.markdown("### 📜 Histori Transaksi")
                    st.code('\n'.join(table_lines), language="text")
            else:
                st.warning("Tidak ada hasil, pastikan ticker ada dan model terlatih.")
                if output.strip():
                    with st.expander("Show Logs"):
                        st.text(output)

    with tab_candle:
        st.header("🕯️ Candlestick Pattern Screener")
        st.caption("Memindai seluruh 64 saham Universe untuk menemukan pola price action yang terbentuk di penutupan hari ini, dan memfilter pola dengan probabilitas win-rate tertinggi berdasar historis BEI.")
        
        st.markdown("---")
        
        # Manual Screen Button
        col_c1, col_c2 = st.columns([1, 4])
        with col_c1:
            if st.button("🔍 Jalankan Screener Sekarang", key="btn_run_screener", type="primary"):
                with st.spinner("Memindai data Candlestick (±15 detik)..."):
                    import subprocess
                    import os
                    script_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "scripts", "screener_candlestick.py")
                    try:
                        res = subprocess.run(["python", script_path, "--save-db"], capture_output=True, text=True, timeout=60)
                        if res.returncode == 0:
                            st.success("Screener selesai berjalan & data tersimpan ke database!")
                        else:
                            st.error(f"Terjadi error: {res.stderr}")
                    except Exception as e:
                        st.error(f"Error eksekusi script: {e}")
        
        with col_c2:
            st.info("💡 Screener secara otomatis akan berjalan setiap hari bursa pada pukul **18:00 WIB** via background Cronjob.")
            
        st.markdown("### 🗄️ Database Sinyal Pola (Hari Ini)")
        
        # Ambil data hari ini dari database
        try:
            import pandas as pd
            from datetime import date
            today_str = date.today().strftime("%Y-%m-%d")
            
            query = f"""
            SELECT ticker, pattern_name, signal_direction, win_rate, context_note 
            FROM candlestick_signals 
            WHERE scan_date = '{today_str}'
            ORDER BY win_rate DESC
            """
            conn = get_db_conn()
            df_signals = pd.read_sql(query, conn)
            conn.close()
            
            if len(df_signals) > 0:
                # Split into bullish & bearish
                df_bull = df_signals[df_signals['signal_direction'].str.contains('BULL')].copy()
                df_bear = df_signals[df_signals['signal_direction'].str.contains('BEAR')].copy()
                
                col_sum1, col_sum2, col_sum3 = st.columns(3)
                col_sum1.metric("Total Pola Terdeteksi", f"{len(df_signals)} Sinyal")
                col_sum2.metric("Bullish Reversal", f"{len(df_bull)} Sinyal")
                col_sum3.metric("Bearish Reversal", f"{len(df_bear)} Sinyal")
                
                col_t1, col_t2 = st.columns(2)
                
                with col_t1:
                    st.markdown("#### 🎯 Indikasi Bullish")
                    if len(df_bull) > 0:
                        st.dataframe(
                            df_bull.style.map(lambda x: "color: #22c55e", subset=['signal_direction'])
                                   .format({'win_rate': '{:.1f}%'}), 
                            use_container_width=True, hide_index=True
                        )
                    else:
                        st.warning("Tidak ada pola candlestick Bullish yang kuat hari ini.")
                        
                with col_t2:
                    st.markdown("#### ⚠️ Indikasi Bearish")
                    if len(df_bear) > 0:
                        st.dataframe(
                            df_bear.style.map(lambda x: "color: #ef4444", subset=['signal_direction'])
                                   .format({'win_rate': '{:.1f}%'}), 
                            use_container_width=True, hide_index=True
                        )
                    else:
                        st.success("Tidak ada pola candlestick Bearish yang mengancam hari ini.")
                        
            else:
                st.info(f"Belum ada data pola candlestick untuk tanggal **{today_str}**. Silakan klik tombol 'Jalankan Screener' di atas jika market sudah tutup.")
                
        except Exception as e:
            st.error(f"Gagal mengambil data dari database: {str(e)}")

# === PAGE: Backtest ===

elif page == "🧪 Backtest":
    st.title("🧪 HISTORICAL BACKTEST")
    st.caption("Menampilkan hasil dari `scripts/backtest_signals.py` jika file `backtest_result.json` tersedia.")

    result, result_path, error = load_backtest_result()

    if error:
        st.warning(error)
        st.code(
            "make backtest\n"
            "# atau\n"
            "python scripts/backtest_signals.py --tickers BBCA BMRI --output backtest_result.json",
            language="bash",
        )
    else:
        import pandas as pd

        config = result.get("config", {})
        aggregate = result.get("aggregate", {})
        tickers = result.get("tickers", {})

        run_date = result.get("run_date", "N/A")
        try:
            run_date = datetime.fromisoformat(run_date).strftime("%d %b %Y, %H:%M")
        except Exception:
            pass

        st.markdown(f"**Source:** `{result_path}`")
        st.markdown(
            f"**Run:** {run_date} | **Period:** `{config.get('period', 'N/A')}` | "
            f"**Range:** `{config.get('start') or '-'} → {config.get('end') or '-'}` | "
            f"**Holding:** `{config.get('holding_days', 'N/A')}` hari"
        )

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Trades", aggregate.get("trades", 0))
        with col2:
            st.metric("Win Rate", f"{aggregate.get('win_rate', 0):.1f}%")
        with col3:
            st.metric("Avg Return", f"{aggregate.get('avg_return_pct', 0):+.2f}%")
        with col4:
            st.metric("Profit Factor", f"{aggregate.get('profit_factor', 0):.2f}")

        col5, col6, col7, col8 = st.columns(4)
        with col5:
            st.metric("Max Drawdown", f"{aggregate.get('max_drawdown_pct', 0):+.2f}%")
        with col6:
            st.metric("Median Return", f"{aggregate.get('median_return_pct', 0):+.2f}%")
        with col7:
            st.metric("Best Trade", f"{aggregate.get('best_trade_pct', 0):+.2f}%")
        with col8:
            st.metric("Worst Trade", f"{aggregate.get('worst_trade_pct', 0):+.2f}%")

        st.divider()

        summary_rows = []
        all_trades = []
        errors = []
        for ticker, ticker_result in tickers.items():
            if ticker_result.get("error"):
                errors.append({"ticker": ticker.upper(), "error": ticker_result.get("error")})
                continue

            summary = ticker_result.get("summary", {})
            summary_rows.append({
                "ticker": ticker_result.get("ticker", ticker).upper(),
                "rows": ticker_result.get("rows", 0),
                "trades": summary.get("trades", 0),
                "win_rate": summary.get("win_rate", 0),
                "avg_return_pct": summary.get("avg_return_pct", 0),
                "median_return_pct": summary.get("median_return_pct", 0),
                "profit_factor": summary.get("profit_factor", 0),
                "max_drawdown_pct": summary.get("max_drawdown_pct", 0),
                "best_trade_pct": summary.get("best_trade_pct", 0),
                "worst_trade_pct": summary.get("worst_trade_pct", 0),
            })

            for trade in ticker_result.get("trades", []):
                row = trade.copy()
                row["ticker"] = row.get("ticker", ticker).upper()
                all_trades.append(row)

        tab_summary, tab_trades, tab_errors, tab_raw = st.tabs([
            "📊 Summary per Ticker",
            "📋 Trades",
            "⚠️ Errors",
            "🧾 Raw JSON",
        ])

        with tab_summary:
            if summary_rows:
                df_summary = pd.DataFrame(summary_rows).sort_values("avg_return_pct", ascending=False)
                st.dataframe(
                    df_summary,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "ticker": "Ticker",
                        "rows": "Rows",
                        "trades": "Trades",
                        "win_rate": st.column_config.NumberColumn("Win Rate", format="%.1f%%"),
                        "avg_return_pct": st.column_config.NumberColumn("Avg Return", format="%+.2f%%"),
                        "median_return_pct": st.column_config.NumberColumn("Median Return", format="%+.2f%%"),
                        "profit_factor": st.column_config.NumberColumn("Profit Factor", format="%.2f"),
                        "max_drawdown_pct": st.column_config.NumberColumn("Max DD", format="%+.2f%%"),
                        "best_trade_pct": st.column_config.NumberColumn("Best", format="%+.2f%%"),
                        "worst_trade_pct": st.column_config.NumberColumn("Worst", format="%+.2f%%"),
                    },
                )

                chart_df = df_summary.set_index("ticker")[["avg_return_pct", "win_rate"]]
                st.bar_chart(chart_df)
            else:
                st.info("Belum ada summary ticker yang bisa ditampilkan.")

        with tab_trades:
            if all_trades:
                df_trades = pd.DataFrame(all_trades)
                ticker_options = ["ALL"] + sorted(df_trades["ticker"].dropna().unique().tolist())
                selected_ticker = st.selectbox("Ticker", ticker_options)
                result_options = ["ALL"] + sorted(df_trades["result"].dropna().unique().tolist())
                selected_result = st.selectbox("Result", result_options)

                filtered = df_trades.copy()
                if selected_ticker != "ALL":
                    filtered = filtered[filtered["ticker"] == selected_ticker]
                if selected_result != "ALL":
                    filtered = filtered[filtered["result"] == selected_result]

                preferred_cols = [
                    "ticker", "entry_date", "exit_date", "entry_price", "exit_price",
                    "result", "return_pct", "holding_days", "rsi", "ma20", "ma50",
                ]
                visible_cols = [col for col in preferred_cols if col in filtered.columns]
                st.dataframe(
                    filtered[visible_cols].sort_values(["entry_date", "ticker"], ascending=[False, True]),
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "entry_price": st.column_config.NumberColumn("Entry", format="Rp %.0f"),
                        "exit_price": st.column_config.NumberColumn("Exit", format="Rp %.0f"),
                        "return_pct": st.column_config.NumberColumn("Return", format="%+.2f%%"),
                        "rsi": st.column_config.NumberColumn("RSI", format="%.2f"),
                        "ma20": st.column_config.NumberColumn("MA20", format="Rp %.0f"),
                        "ma50": st.column_config.NumberColumn("MA50", format="Rp %.0f"),
                    },
                )

                result_counts = filtered["result"].value_counts().rename_axis("result").reset_index(name="count")
                st.bar_chart(result_counts.set_index("result"))
            else:
                st.info("Tidak ada trade yang ter-generate.")

        with tab_errors:
            if errors:
                st.dataframe(pd.DataFrame(errors), use_container_width=True, hide_index=True)
            else:
                st.success("Tidak ada error ticker di hasil backtest.")

        with tab_raw:
            st.json(result)


# === PAGE: Portfolio ===

elif page == "💼 Portfolio":
    st.title("💼 PORTFOLIO MANAGEMENT")

    # Import portfolio modules
    try:
        from portfolio.manager import (
            get_all_holdings, update_current_prices, get_portfolio_summary,
            add_holding, record_buy, record_sell, get_transactions,
            preview_avg_cost_after_buy, reset_all_holdings
        )
        from portfolio.dca_strategy import (
            get_active_strategies, create_dca_from_signal, create_dca_manual,
            get_strategy_with_levels, recommend_dca_timing, deactivate_strategy
        )
    except ImportError as e:
        st.error(f"Portfolio module not available: {e}")
        st.stop()

    # Tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Holdings Overview",
        "💰 DCA Manager",
        "📜 Transaction History",
        "📈 Performance Report",
        "🤖 AI Analysis"
    ])

    # === TAB 1: Holdings Overview ===
    with tab1:
        st.subheader("📊 Holdings Overview")

        # Get holdings
        holdings = get_all_holdings()

        if holdings:
            # Update prices
            with st.spinner("Updating prices..."):
                holdings = update_current_prices(holdings)

            # Summary cards
            summary = get_portfolio_summary(holdings)
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric(
                    "Total Invested",
                    f"Rp {summary['total_invested']:,.0f}",
                )
            with col2:
                st.metric(
                    "Current Value",
                    f"Rp {summary['total_current_value']:,.0f}",
                    delta=f"{summary['total_pnl']:,.0f}" if summary['total_current_value'] > 0 else None,
                )
            with col3:
                pnl_pct = summary['total_pnl_pct']
                st.metric(
                    "Total P&L",
                    f"{pnl_pct:+.2f}%",
                    delta=f"Rp {summary['total_pnl']:,.0f}",
                )
            with col4:
                best = summary.get('best_performer')
                best_pct = summary.get('best_pnl_pct', 0)
                st.metric(
                    "Best Performer",
                    best or "N/A",
                    delta=f"{best_pct:+.2f}%" if best else None,
                )

            st.divider()

            # Holdings table
            st.markdown("### 📋 Holdings")

            import pandas as pd
            df_holdings = pd.DataFrame(holdings)
            df_holdings['total_invested'] = df_holdings['avg_cost'] * df_holdings['total_shares']

            display_cols = [
                'ticker', 'total_lots', 'avg_cost', 'current_price',
                'current_value', 'unrealized_pnl', 'unrealized_pnl_pct', 'status'
            ]
            df_display = df_holdings[[col for col in display_cols if col in df_holdings.columns]]

            st.dataframe(
                df_display,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "ticker": "Ticker",
                    "total_lots": st.column_config.NumberColumn("Lot", format="%d"),
                    "avg_cost": st.column_config.NumberColumn("Avg Cost", format="Rp %.0f"),
                    "current_price": st.column_config.NumberColumn("Current", format="Rp %.0f"),
                    "current_value": st.column_config.NumberColumn("Value", format="Rp %.0f"),
                    "unrealized_pnl": st.column_config.NumberColumn("P&L (Rp)", format="Rp %+.0f"),
                    "unrealized_pnl_pct": st.column_config.NumberColumn("P&L (%)", format="%+.2f%%"),
                    "status": "Status",
                },
            )

            st.divider()

            # Add new holding form
            with st.expander("➕ Add New Holding"):
                col1, col2, col3 = st.columns(3)
                with col1:
                    new_ticker = st.text_input("Ticker", key="new_holding_ticker").upper()
                with col2:
                    new_lots = st.number_input("Lot", min_value=1, value=10, key="new_holding_lots")
                with col3:
                    new_avg = st.number_input("Avg Cost", min_value=1.0, value=1000.0, key="new_holding_avg")

                if st.button("Add Holding"):
                    if new_ticker:
                        try:
                            result = add_holding(new_ticker, new_lots * 100, new_avg)
                            st.success(f"Added {new_ticker}: {new_lots} lot @ Rp {new_avg:,.0f}")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {e}")
                    else:
                        st.warning("Ticker harus diisi")

            # Record transaction form
            with st.expander("💵 Record Buy/Sell"):
                txn_type = st.radio("Type", ["BUY", "SELL"], horizontal=True, key="txn_type")
                col1, col2, col3 = st.columns(3)
                with col1:
                    txn_ticker = st.selectbox("Ticker", [h['ticker'] for h in holdings], key="txn_ticker")

                # Get current price for default value
                selected_holding = next((h for h in holdings if h['ticker'] == txn_ticker), None)
                current_price_default = selected_holding.get('current_price') if selected_holding else 1000.0
                if not current_price_default or current_price_default <= 0:
                    current_price_default = 1000.0

                with col2:
                    txn_lots = st.number_input("Lot", min_value=1, value=1, key="txn_lots")
                with col3:
                    txn_price = st.number_input("Price", min_value=1.0, value=float(current_price_default), key="txn_price")

                # Calculate total amount
                total_shares = txn_lots * 100
                total_amount = txn_price * total_shares
                st.caption(f"💰 Total: **Rp {total_amount:,.0f}** ({txn_lots} lot × {total_shares} shares × Rp {txn_price:,.0f})")

                # Preview avg cost after buy
                if txn_type == "BUY" and txn_ticker:
                    preview = preview_avg_cost_after_buy(txn_ticker, txn_price, txn_lots)
                    current_avg = preview['current_avg']
                    new_avg = preview['new_avg_cost']
                    current_pnl_pct = selected_holding.get('unrealized_pnl_pct') if selected_holding else None

                    # Calculate percentage change in avg cost
                    if current_avg and current_avg > 0:
                        avg_change_pct = ((new_avg - current_avg) / current_avg) * 100
                        change_text = f" ({avg_change_pct:+.2f}%"
                        # Add current P&L if available
                        if current_pnl_pct is not None:
                            change_text += f" of current P&L {current_pnl_pct:+.2f}%"
                        change_text += ")"
                    else:
                        change_text = " (new position)"

                    st.info(
                        f"Preview: New avg cost = **Rp {new_avg:,.0f}**{change_text} "
                        f"(total {preview['total_lots_after']} lot)"
                    )

                if st.button(f"Record {txn_type}"):
                    try:
                        if txn_type == "BUY":
                            result = record_buy(txn_ticker, txn_lots, txn_price)
                            st.success(f"BUY recorded: {txn_ticker} {txn_lots} lot @ Rp {txn_price:,.0f}")
                        else:
                            result = record_sell(txn_ticker, txn_lots, txn_price)
                            st.success(f"SELL recorded: {txn_ticker} {txn_lots} lot @ Rp {txn_price:,.0f}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")

        else:
            st.info("Belum ada holdings. Tambahkan holdings pertama di form di bawah.")

            with st.form("first_holding"):
                st.markdown("### ➕ Add First Holding")
                col1, col2, col3 = st.columns(3)
                with col1:
                    ticker = st.text_input("Ticker (e.g. TLKM)").upper()
                with col2:
                    lots = st.number_input("Lot", min_value=1, value=10)
                with col3:
                    avg_cost = st.number_input("Avg Cost", min_value=1.0, value=3000.0)

                submitted = st.form_submit_button("Add Holding")
                if submitted and ticker:
                    try:
                        result = add_holding(ticker, lots * 100, avg_cost)
                        st.success(f"Added {ticker}: {lots} lot @ Rp {avg_cost:,.0f}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")

        # Always show Danger Zone at the bottom of Tab 1
        st.divider()
        with st.expander("⚠️ Danger Zone: Reset Portfolio"):
            st.warning("Perhatian: Tindakan ini akan menghapus semua riwayat transaksi, DCA, dan data kepemilikan saham di portofolio secara permanen!")
            if st.button("🚨 Reset All Data Holding", type="primary", use_container_width=True):
                try:
                    if reset_all_holdings():
                        st.success("Seluruh data portofolio telah direset!")
                        st.rerun()
                    else:
                        st.error("Gagal mereset data portofolio.")
                except Exception as e:
                    st.error(f"Error: {e}")

    # === TAB 2: DCA Manager ===
    with tab2:
        st.subheader("💰 DCA Manager")

        # Section 1: Active Strategies
        st.markdown("### 📋 Active DCA Strategies")
        strategies = get_active_strategies()

        if strategies:
            import pandas as pd
            df_strat = pd.DataFrame(strategies)
            display_cols = [
                'ticker', 'total_budget', 'used_budget', 'remaining_budget',
                'used_budget_pct', 'dca_count', 'next_buy_price', 'status'
            ]
            df_display = df_strat[[col for col in display_cols if col in df_strat.columns]]

            st.dataframe(
                df_display,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "ticker": "Ticker",
                    "total_budget": st.column_config.NumberColumn("Budget", format="Rp %.0f"),
                    "used_budget": st.column_config.NumberColumn("Used", format="Rp %.0f"),
                    "remaining_budget": st.column_config.NumberColumn("Remaining", format="Rp %.0f"),
                    "used_budget_pct": st.column_config.ProgressColumn("Progress", format="%.1f%%", min_value=0, max_value=100),
                    "dca_count": st.column_config.NumberColumn("Levels", format="%d"),
                    "next_buy_price": st.column_config.NumberColumn("Next Buy", format="Rp %.0f"),
                    "status": "Status",
                },
            )
        else:
            st.info("Belum ada DCA strategy aktif.")

        st.divider()

        # Section 2: Create New DCA
        st.markdown("### ➕ Create New DCA Strategy")

        dca_mode = st.radio("Mode", ["From TOP PICKS Signal", "Manual Input"], horizontal=True)

        if dca_mode == "From TOP PICKS Signal":
            # Get latest signals
            signals = query_db("""
                SELECT id, ticker, entry_low, entry_high, max_entry, conviction, thesis
                FROM signals
                WHERE run_date = (SELECT MAX(run_date) FROM signals WHERE is_konglo = FALSE)
                AND is_konglo = FALSE
                ORDER BY rank
                LIMIT 10
            """)

            if signals:
                signal_options = {
                    f"{s['ticker']} (Entry: {s['entry_low']}-{s['max_entry']}, {s['conviction']})": s['id']
                    for s in signals
                }
                selected_label = st.selectbox("Select Signal", list(signal_options.keys()))
                selected_signal_id = signal_options[selected_label]

                col1, col2 = st.columns(2)
                with col1:
                    dca_budget = st.number_input("Total Budget (Rp)", min_value=100000, value=2000000, step=100000)
                with col2:
                    dca_count = st.number_input("DCA Levels", min_value=2, max_value=5, value=3)

                if st.button("Preview DCA Levels"):
                    selected_signal = next(s for s in signals if s['id'] == selected_signal_id)
                    from portfolio.manager import calculate_dca_levels
                    levels_data = calculate_dca_levels(
                        entry_low=float(selected_signal['entry_low']),
                        entry_high=float(selected_signal['entry_high'] or selected_signal['entry_low']),
                        max_entry=float(selected_signal['max_entry']),
                        total_budget=dca_budget,
                        dca_count=dca_count,
                    )

                    st.markdown("**Preview Levels:**")
                    import pandas as pd
                    df_levels = pd.DataFrame(levels_data['levels'])
                    st.dataframe(
                        df_levels,
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "level": "Level",
                            "price": st.column_config.NumberColumn("Price", format="Rp %.0f"),
                            "amount_budget": st.column_config.NumberColumn("Budget", format="Rp %.0f"),
                            "actual_amount": st.column_config.NumberColumn("Actual", format="Rp %.0f"),
                            "lots": st.column_config.NumberColumn("Lot", format="%d"),
                            "shares": st.column_config.NumberColumn("Shares", format="%d"),
                        },
                    )

                if st.button("✅ Activate DCA Strategy"):
                    try:
                        result = create_dca_from_signal(selected_signal_id, dca_budget, dca_count)
                        st.success(f"DCA strategy created for {result['ticker']}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")
            else:
                st.warning("Belum ada TOP PICKS signal. Run analysis dulu.")

        else:
            # Manual input
            col1, col2 = st.columns(2)
            with col1:
                manual_ticker = st.text_input("Ticker", key="manual_ticker_input").upper()
                
                # Tambahkan tombol auto-fill di bawah Ticker
                if st.button("🤖 Get AI Entry Recommendation", use_container_width=True):
                    if manual_ticker:
                        from portfolio.dca_strategy import get_quick_ai_entry
                        rec = get_quick_ai_entry(manual_ticker)
                        if rec:
                            st.session_state["manual_entry_low"] = rec["entry_low"]
                            st.session_state["manual_entry_high"] = rec["entry_high"]
                            st.session_state["manual_max_entry"] = rec["max_entry"]
                            st.success(f"✅ Auto-filled with AI recommendations for {manual_ticker}!")
                        else:
                            st.error(f"Gagal mengambil data teknikal untuk {manual_ticker}. Pastikan ticker benar.")
                    else:
                        st.warning("Ketikkan Ticker terlebih dahulu.")

                manual_entry_low = st.number_input("Entry Low", min_value=1.0, value=st.session_state.get("manual_entry_low", 3000.0), key="manual_entry_low")
                manual_entry_high = st.number_input("Entry High", min_value=1.0, value=st.session_state.get("manual_entry_high", 3200.0), key="manual_entry_high")
            with col2:
                manual_max_entry = st.number_input("Max Entry", min_value=1.0, value=st.session_state.get("manual_max_entry", 3400.0), key="manual_max_entry")
                manual_budget = st.number_input("Total Budget", min_value=100000.0, value=2000000.0, step=100000.0, key="manual_budget")
                manual_dca_count = st.number_input("Levels", min_value=2, max_value=5, value=3, key="manual_dca_count")

            if st.button("Preview Manual DCA Levels"):
                from portfolio.manager import calculate_dca_levels
                levels_data = calculate_dca_levels(
                    entry_low=float(manual_entry_low),
                    entry_high=float(manual_entry_high),
                    max_entry=float(manual_max_entry),
                    total_budget=manual_budget,
                    dca_count=manual_dca_count,
                )

                st.markdown("**Preview Levels:**")
                import pandas as pd
                df_levels = pd.DataFrame(levels_data['levels'])
                st.dataframe(
                    df_levels,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "level": "Level",
                        "price": st.column_config.NumberColumn("Price", format="Rp %.0f"),
                        "amount_budget": st.column_config.NumberColumn("Budget", format="Rp %.0f"),
                        "actual_amount": st.column_config.NumberColumn("Actual", format="Rp %.0f"),
                        "lots": st.column_config.NumberColumn("Lot", format="%d"),
                        "shares": st.column_config.NumberColumn("Shares", format="%d"),
                    },
                )

            if st.button("✅ Create Manual DCA"):
                if manual_ticker:
                    try:
                        result = create_dca_manual(
                            ticker=manual_ticker,
                            total_budget=manual_budget,
                            entry_low=manual_entry_low,
                            entry_high=manual_entry_high,
                            max_entry=manual_max_entry,
                            dca_count=manual_dca_count,
                        )
                        st.success(f"Manual DCA strategy created for {manual_ticker}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")
                else:
                    st.warning("Ticker harus diisi")

        st.divider()

        # Section 3: DCA Timing Recommendation
        st.markdown("### 🕐 DCA Timing Recommendation")

        holdings = get_all_holdings()
        if holdings:
            timing_ticker = st.selectbox(
                "Select Ticker",
                [h['ticker'] for h in holdings],
                key="timing_ticker"
            )

            if st.button("Check Timing"):
                try:
                    timing = recommend_dca_timing(timing_ticker)

                    status = timing['status']
                    if status == "IDEAL":
                        status_badge = "🟢 IDEAL"
                        status_color = "green"
                    elif status == "ACCEPTABLE":
                        status_badge = "🟡 ACCEPTABLE"
                        status_color = "orange"
                    elif status == "CAUTION":
                        status_badge = "🟠 CAUTION"
                        status_color = "orange"
                    elif status == "AVOID":
                        status_badge = "🔴 AVOID"
                        status_color = "red"
                    else:
                        status_badge = "⚪ NO DATA"
                        status_color = "gray"

                    st.markdown(f"### {status_badge}")

                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Current Price", f"Rp {timing['current_price']:,.0f}" if timing['current_price'] else "N/A")
                    with col2:
                        st.metric("True Cost 1M", f"Rp {timing['true_cost_1m']:,.0f}" if timing['true_cost_1m'] else "N/A")
                    with col3:
                        dist = timing['distance_pct']
                        st.metric("Distance", f"{dist:+.2f}%" if dist is not None else "N/A")

                    st.info(timing['reason'])

                    if timing['recommended_buy']:
                        st.success(f"💡 Recommended buy price: **Rp {timing['recommended_buy']:,.0f}**")

                except Exception as e:
                    st.error(f"Error: {e}")
        else:
            st.info("Belum ada holdings untuk cek timing.")

    # === TAB 3: Transaction History ===
    with tab3:
        st.subheader("📜 Transaction History")

        transactions = get_transactions()

        if transactions:
            import pandas as pd
            df_txn = pd.DataFrame(transactions)

            # Filters
            col1, col2, col3 = st.columns(3)
            with col1:
                ticker_filter = st.selectbox("Ticker", ["ALL"] + sorted(df_txn['ticker'].unique().tolist()))
            with col2:
                type_filter = st.selectbox("Type", ["ALL", "BUY", "SELL"])
            with col3:
                st.write("")  # spacing

            filtered = df_txn.copy()
            if ticker_filter != "ALL":
                filtered = filtered[filtered['ticker'] == ticker_filter]
            if type_filter != "ALL":
                filtered = filtered[filtered['transaction_type'] == type_filter]

            display_cols = [
                'transaction_date', 'ticker', 'transaction_type', 'lots', 'price', 'amount', 'signal_id', 'notes'
            ]
            df_display = filtered[[col for col in display_cols if col in filtered.columns]]

            st.dataframe(
                df_display.sort_values('transaction_date', ascending=False),
                use_container_width=True,
                hide_index=True,
                column_config={
                    "transaction_date": "Date",
                    "ticker": "Ticker",
                    "transaction_type": "Type",
                    "lots": st.column_config.NumberColumn("Lot", format="%d"),
                    "price": st.column_config.NumberColumn("Price", format="Rp %.0f"),
                    "amount": st.column_config.NumberColumn("Amount", format="Rp %.0f"),
                    "signal_id": "Signal ID",
                    "notes": "Notes",
                },
            )

            # Export
            if st.button("📥 Export to CSV"):
                csv = df_display.to_csv(index=False)
                st.download_button(
                    label="Download CSV",
                    data=csv,
                    file_name=f"transactions_{datetime.now()}.csv",
                    mime="text/csv",
                )
        else:
            st.info("Belum ada transaksi.")

    # === TAB 4: Performance Report ===
    with tab4:
        st.subheader("📈 Performance Report")

        transactions = get_transactions()
        holdings = get_all_holdings()

        if transactions:
            import pandas as pd
            df_txn = pd.DataFrame(transactions)

            # Monthly P&L (simplified)
            df_txn['month'] = pd.to_datetime(df_txn['transaction_date']).dt.to_period('M').astype(str)
            monthly = df_txn.groupby('month').agg({
                'amount': lambda x: (
                    df_txn.loc[x.index][df_txn.loc[x.index]['transaction_type'] == 'SELL']['amount'].sum() -
                    df_txn.loc[x.index][df_txn.loc[x.index]['transaction_type'] == 'BUY']['amount'].sum()
                )
            }).rename(columns={'amount': 'net_flow'})

            st.markdown("### 📊 Monthly Transaction Flow")
            st.bar_chart(monthly)

            st.divider()

            # Per-ticker stats
            st.markdown("### 📋 Per-Ticker Transaction Summary")
            ticker_stats = df_txn.groupby('ticker').agg({
                'amount': 'sum',
                'lots': 'sum',
                'transaction_type': 'count'
            }).rename(columns={'transaction_type': 'count'})

            st.dataframe(
                ticker_stats,
                use_container_width=True,
                column_config={
                    "amount": st.column_config.NumberColumn("Total Amount", format="Rp %.0f"),
                    "lots": st.column_config.NumberColumn("Total Lot", format="%d"),
                    "count": "Transactions",
                },
            )
        else:
            st.info("Belum ada transaksi untuk ditampilkan.")

        # Current holdings performance
        if holdings:
            st.divider()
            st.markdown("### 💼 Current Holdings P&L")

            import pandas as pd
            df_h = pd.DataFrame(holdings)
            df_h = df_h[df_h['unrealized_pnl'].notna()].sort_values('unrealized_pnl_pct', ascending=False)

            if not df_h.empty:
                st.dataframe(
                    df_h[['ticker', 'unrealized_pnl', 'unrealized_pnl_pct']],
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "ticker": "Ticker",
                        "unrealized_pnl": st.column_config.NumberColumn("P&L (Rp)", format="Rp %+.0f"),
                        "unrealized_pnl_pct": st.column_config.NumberColumn("P&L (%)", format="%+.2f%%"),
                    },
                )

    # === TAB 5: AI Analysis ===
    with tab5:
        st.subheader("🤖 AI Portfolio Analysis")
        st.caption("All-in-one analisis portfolio: rebalancing, DCA priority, risk analysis, performance attribution.")

        # Monthly budget config
        col_budget, col_btn = st.columns([2, 1])
        with col_budget:
            monthly_budget = st.number_input(
                "Monthly DCA Budget (Rp)",
                min_value=100_000,
                max_value=100_000_000,
                value=2_000_000,
                step=500_000,
                key="ai_monthly_budget",
            )
        with col_btn:
            st.write("")
            st.write("")
            run_ai = st.button("🤖 Get AI Portfolio Analysis", type="primary", use_container_width=True)

        # Show cached result if available
        cached = st.session_state.get("portfolio_ai_result")

        if run_ai:
            with st.spinner("AI sedang menganalisis portfolio... (bisa 30-60 detik)"):
                try:
                    from agents.portfolio_advisor import analyze_portfolio
                    from portfolio.manager import get_all_holdings, update_current_prices, get_transactions
                    from portfolio.dca_strategy import get_active_strategies
                    from datetime import timedelta

                    # Gather data
                    h_list = get_all_holdings()
                    h_list = update_current_prices(h_list)
                    strats = get_active_strategies()
                    txns = get_transactions(start_date=datetime.now() - timedelta(days=30))

                    # Don't use TOP PICKS - focus on existing holdings only
                    top_picks = []

                    ai_result = analyze_portfolio(
                        holdings=h_list,
                        active_strategies=strats,
                        top_picks=top_picks,
                        monthly_budget=monthly_budget,
                        transactions=txns,
                    )
                    st.session_state["portfolio_ai_result"] = ai_result
                    cached = ai_result
                    st.success("Analisis selesai!")
                except Exception as e:
                    st.error(f"Error: {e}")
                    cached = None

        if cached:
            ai = cached
            generated_at = ai.get("generated_at", "")
            if generated_at:
                st.caption(f"Generated: {generated_at[:19].replace('T', ' ')} WIB")

            # Error banner
            if ai.get("error"):
                st.error(f"AI Error: {ai['error']}")

            # Summary
            summary = ai.get("summary", "")
            if summary:
                st.info(f"📋 **Summary:** {summary}")

            st.divider()

            # === Section 1: Rebalancing ===
            rebal = ai.get("rebalancing", {})
            with st.expander("⚖️ Rebalancing Recommendations", expanded=True):
                needed = rebal.get("needed", False)
                if needed:
                    st.warning("⚠️ Rebalancing diperlukan")
                else:
                    st.success("✅ Portfolio sudah seimbang")

                overweight = rebal.get("overweight", [])
                underweight = rebal.get("underweight", [])

                col_ow, col_uw = st.columns(2)
                with col_ow:
                    st.markdown("**Overweight:**")
                    if overweight:
                        for t in overweight:
                            st.markdown(f"- 🔴 {t}")
                    else:
                        st.caption("Tidak ada")
                with col_uw:
                    st.markdown("**Underweight:**")
                    if underweight:
                        for t in underweight:
                            st.markdown(f"- 🟡 {t}")
                    else:
                        st.caption("Tidak ada")

                actions = rebal.get("actions", [])
                if actions:
                    st.markdown("**Action Plan:**")
                    import pandas as pd
                    df_act = pd.DataFrame(actions)
                    action_icon = {"REDUCE": "🔻", "INCREASE": "🔺", "HOLD": "⏸️"}
                    df_act["action"] = df_act["action"].apply(
                        lambda x: f"{action_icon.get(x, '')} {x}"
                    )
                    st.dataframe(df_act, use_container_width=True, hide_index=True)

            # === Section 2: DCA Priority ===
            dca_prio = ai.get("dca_priority", [])
            with st.expander(f"💰 DCA Priority This Month (Budget: Rp {monthly_budget:,.0f})", expanded=True):
                if dca_prio:
                    for p in dca_prio:
                        rank = p.get("rank", "")
                        ticker = p.get("ticker", "")
                        alloc = p.get("allocation", 0)
                        timing = p.get("timing_status", "N/A")
                        conv = p.get("conviction", "N/A")
                        reason = p.get("reasoning", "")

                        # Timing color
                        timing_icon = {"IDEAL": "🟢", "ACCEPTABLE": "🟡", "CAUTION": "🟠", "AVOID": "🔴"}.get(timing, "⚪")
                        conv_icon = "✅" if conv == "HIGH" else "⚠️" if conv == "MEDIUM" else "❓"

                        with st.container(border=True):
                            c1, c2, c3 = st.columns([1, 2, 3])
                            with c1:
                                st.markdown(f"### #{rank}")
                                st.markdown(f"**{ticker}**")
                            with c2:
                                st.metric("Alokasi", f"Rp {alloc:,.0f}")
                                st.caption(f"{timing_icon} {timing} | {conv_icon} {conv}")
                            with c3:
                                st.caption(reason)
                else:
                    st.info("Tidak ada DCA priority dari AI saat ini.")

            # === Section 3: Risk Analysis ===
            risk = ai.get("risk_analysis", {})
            with st.expander("⚠️ Risk Analysis", expanded=False):
                risk_level = risk.get("risk_level", "N/A")
                div_score = risk.get("diversification_score", 0)
                recs = risk.get("recommendations", [])
                sector_conc = risk.get("sector_concentration", {})

                risk_color = {"LOW": "🟢", "MEDIUM": "🟡", "HIGH": "🔴"}.get(risk_level, "⚪")

                col_r1, col_r2 = st.columns(2)
                with col_r1:
                    st.metric("Risk Level", f"{risk_color} {risk_level}")
                with col_r2:
                    st.metric("Diversification Score", f"{div_score}/10")

                if sector_conc:
                    st.markdown("**Sector Concentration:**")
                    import pandas as pd
                    df_sec = pd.DataFrame([
                        {"Sector": k, "Weight (%)": v}
                        for k, v in sector_conc.items()
                    ]).sort_values("Weight (%)", ascending=False)
                    st.dataframe(df_sec, use_container_width=True, hide_index=True)

                if recs:
                    st.markdown("**Recommendations:**")
                    for r in recs:
                        st.markdown(f"- {r}")

            # === Section 4: Performance Attribution ===
            perf = ai.get("performance_attribution", {})
            with st.expander("📊 Performance Attribution", expanded=False):
                best = perf.get("best_performer")
                worst = perf.get("worst_performer")
                sig_quality = perf.get("signal_quality", "N/A")

                col_b, col_w = st.columns(2)
                with col_b:
                    st.markdown("**🏆 Best Performer:**")
                    if best and isinstance(best, dict):
                        st.metric(
                            best.get("ticker", "N/A"),
                            f"{best.get('return_pct', 0):+.2f}%",
                        )
                        st.caption(best.get("reason", ""))
                    elif isinstance(best, str):
                        st.write(best)
                    else:
                        st.caption("N/A")

                with col_w:
                    st.markdown("**📉 Worst Performer:**")
                    if worst and isinstance(worst, dict):
                        st.metric(
                            worst.get("ticker", "N/A"),
                            f"{worst.get('return_pct', 0):+.2f}%",
                        )
                        st.caption(worst.get("reason", ""))
                    elif isinstance(worst, str):
                        st.write(worst)
                    else:
                        st.caption("N/A")

                st.markdown(f"**Signal Quality:** {sig_quality}")

        else:
            st.markdown("""
            **Fitur AI Portfolio Analysis:**
            - ⚖️ Rebalancing recommendations (overweight/underweight detection)
            - 💰 DCA priority ranking dengan budget allocation per ticker
            - ⚠️ Risk analysis (sector concentration, diversification score)
            - 📊 Performance attribution (best/worst performers, signal quality)

            Klik **Get AI Portfolio Analysis** untuk mulai.
            """)


# === PAGE: Universe ===

elif page == "🌍 Universe":
    st.title("🌍 Universe Management")
    st.caption("Kelola daftar saham yang akan dianalisis oleh AI.")
    
    from db import SessionLocal
    from db.models import Universe
    import pandas as pd
    import re
    
    st.subheader("➕ Tambah Ticker Baru")
    with st.form("add_universe_form"):
        new_tickers = st.text_area(
            "Masukkan ticker (pisahkan dengan koma, spasi, atau baris baru):",
            placeholder="GOTO, PANI\nBRIS AMRT"
        )
        submitted = st.form_submit_button("Tambahkan ke Universe")
        if submitted and new_tickers:
            tickers = [t.strip().upper() for t in re.split(r'[,\s\n]+', new_tickers) if t.strip()]
            if tickers:
                db = SessionLocal()
                added = 0
                for t in tickers:
                    existing = db.query(Universe).filter_by(ticker=t).first()
                    if not existing:
                        db.add(Universe(ticker=t, is_custom=True, active=True))
                        added += 1
                    elif not existing.active:
                        existing.active = True
                        added += 1
                db.commit()
                db.close()
                st.success(f"Berhasil menambahkan atau mengaktifkan {added} ticker.")
                st.rerun()

    st.divider()
    
    st.subheader("📋 Daftar Universe")
    db = SessionLocal()
    records = db.query(Universe).order_by(Universe.ticker).all()
    db.close()
    
    if records:
        df = pd.DataFrame([{
            "id": r.id,
            "ticker": r.ticker,
            "is_lq45": r.is_lq45,
            "is_custom": r.is_custom,
            "active": r.active,
            "delete": False
        } for r in records])
        
        search_query = st.text_input("🔍 Cari Ticker:", "").strip().upper()
        if search_query:
            display_df = df[df['ticker'].str.contains(search_query)]
        else:
            display_df = df
        
        st.caption("Centang kolom **Active** untuk on/off, atau centang **Hapus** untuk menghapus permanen, lalu klik Simpan.")
        edited_df = st.data_editor(
            display_df,
            hide_index=True,
            use_container_width=True,
            disabled=["id", "ticker", "is_lq45", "is_custom"],
            column_config={
                "active": st.column_config.CheckboxColumn("Active (Ikut Dianalisis)"),
                "is_lq45": st.column_config.CheckboxColumn("LQ45"),
                "is_custom": st.column_config.CheckboxColumn("Custom"),
                "delete": st.column_config.CheckboxColumn("🗑️ Hapus", default=False),
            },
            key="universe_editor"
        )
        
        if st.button("💾 Simpan Perubahan", type="primary"):
            rows_to_delete = edited_df[edited_df['delete'] == True]
            changed_rows = edited_df[(edited_df['active'] != display_df['active']) & (edited_df['delete'] == False)]
            
            if not rows_to_delete.empty or not changed_rows.empty:
                db = SessionLocal()
                
                # Proses hapus
                for _, row in rows_to_delete.iterrows():
                    u = db.query(Universe).filter_by(id=row['id']).first()
                    if u:
                        db.delete(u)
                        
                # Proses update status
                for _, row in changed_rows.iterrows():
                    u = db.query(Universe).filter_by(id=row['id']).first()
                    if u:
                        u.active = bool(row['active'])
                        
                db.commit()
                db.close()
                st.success(f"Berhasil: Dihapus {len(rows_to_delete)} saham, Diubah status {len(changed_rows)} saham.")
                st.rerun()
            else:
                st.info("Tidak ada perubahan.")
    else:
        st.info("Belum ada data universe.")

# === PAGE: Konglo Play ===
elif page == "🐋 Konglo Play":
    render_konglo_play_page()

# === PAGE: Settings ===
elif page == "⚙️ Settings":
    st.title("⚙️ Settings")

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
        try:
            from agents.llm_client import get_status
            llm_status = get_status()
            healthy = llm_status.get("healthy", False)
            key_ok = llm_status.get("api_key_configured", False)
            if healthy and key_ok:
                label = "Connected ✅"
            elif key_ok:
                label = "Key set, unreachable ⚠️"
            else:
                label = "Not configured ⚠️"
            st.metric("9Router LLM", label)
        except Exception:
            st.metric("9Router LLM", "Error ⚠️")

    with col3:
        base_url = os.getenv("LLM_BASE_URL", "http://localhost:20128/v1")
        llm_on = os.getenv("LLM_ENABLED", "true").lower() in ("true", "1", "yes")
        st.metric("LLM Mode", "Enabled" if llm_on else "Rule-based only")
        st.caption(base_url[:40] + ("…" if len(base_url) > 40 else ""))

    st.divider()

    # ML Actions
    st.subheader("🤖 Machine Learning")
    ml_col1, ml_col2 = st.columns(2)
    with ml_col1:
        if st.button("🚀 Train ML Multi-Day (--all)", use_container_width=True, help="Setara dengan 'make train-ml-multiday'"):
            import sys
            import subprocess
            import os
            subprocess.Popen([sys.executable, "scripts/train_multiday_model.py", "--all"], preexec_fn=os.setsid)
            st.success("Proses Train ML Multi-Day telah dijalankan di background!")
    with ml_col2:
        if st.button("⚠️ Validate ML Accuracy [DEPRECATED]", use_container_width=True, help="Validasi model Day-1 yang telah deprecated"):
            st.warning("Perhatian: Fitur validasi akurasi ini untuk model Day-1 yang sudah deprecated.")

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
    run_dates = query_db("SELECT DISTINCT run_date FROM debate_logs ORDER BY run_date DESC LIMIT 5")
    selected_date = None
    if run_dates:
        selected_date = st.selectbox(
            "Tanggal run",
            [r["run_date"] for r in run_dates],
            format_func=lambda d: str(d),
        )
    debates = query_db(
        """
        SELECT run_date, ticker, round, agent, argument, vote
        FROM debate_logs
        WHERE run_date = %s
        ORDER BY ticker, round, agent
        """,
        (selected_date,) if selected_date else None,
    ) if selected_date else query_db("""
        SELECT run_date, ticker, round, agent, argument, vote
        FROM debate_logs
        ORDER BY run_date DESC, ticker, round, agent
        LIMIT 50
    """)
    if debates:
        from agents.debate.logging_utils import format_debate_log_text
        entries = [
            {
                "round": d["round"],
                "ticker": d["ticker"],
                "agent": d["agent"],
                "argument": d["argument"],
                "vote": d["vote"],
            }
            for d in debates
        ]
        st.text(format_debate_log_text(entries))
        with st.expander("Detail per baris"):
            for d in debates:
                vote_icon = "🟢" if d["vote"] == "BUY" else "🔴" if d["vote"] == "SELL" else "⚪"
                st.markdown(
                    f"{vote_icon} R{d['round']} | **{d['agent']}** → {d['ticker']}: {d['argument']}"
                )
    else:
        st.caption("Belum ada log debate.")

st.divider()
st.caption("Stock Agent IDX v0.1.0 — Phase 0 Setup")
