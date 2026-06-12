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
from datetime import date, datetime, timedelta
from pathlib import Path

import os

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


# === Sidebar ===

st.sidebar.title("🤖 Stock Agent IDX")
page = st.sidebar.radio(
    "Navigation",
    ["📈 Top Picks", "🔍 Bandarmologi", "📈 IHSG Predictor", "🧪 Backtest", "📊 Performance", "⚙️ Settings"],
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
            st.info(
                "Filtering saham berdasarkan:\n"
                "- Rata-rata volume 20 hari >= 300.000\n"
                "- Market cap >= 1 Triliun IDR\n"
                "Universe awal diambil dari config (LQ45/IDX30/Bluechip)."
            )
            result = run_full_analysis()
            st.write(f"✅ Analyzed {len(result.get('composites', {}))} tickers")
            st.write(f"🏆 {len(result.get('top_picks', []))} top picks selected")

            save_full_result(result)
            st.write("💾 Saved to database")

            debate_log = result.get("debate_log", [])
            if debate_log:
                st.session_state["last_debate_log"] = debate_log
                st.write(f"🗣️ Log debat ({len(debate_log)} entri) dihasilkan")

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

        debate_log = last_result.get("debate_log") or st.session_state.get("last_debate_log", [])
        if debate_log:
            from agents.debate.logging_utils import format_debate_log_text
            with st.expander(f"🗣️ Log debat antar agent ({len(debate_log)} entri)", expanded=False):
                st.text(format_debate_log_text(debate_log))

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

                    # Take-Profit Levels
                    tp1 = pick.get("tp1", "N/A")
                    tp2 = pick.get("tp2", "N/A")
                    tp3 = pick.get("tp3", "N/A")
                    tp1_size = pick.get("tp1_size", 0.30)
                    tp2_size = pick.get("tp2_size", 0.40)
                    tp3_size = pick.get("tp3_size", 0.30)
                    sl = pick.get("stop_loss", "N/A")

                    # Display TP levels with position sizing
                    if tp1 != "N/A" and tp2 != "N/A" and tp3 != "N/A":
                        st.markdown("### 📊 Take-Profit Strategy")
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("🎯 TP1 (Exit 30%)", f"Rp {tp1:,.0f}" if isinstance(tp1, (int, float)) else tp1)
                            st.caption(pick.get("risk_reward_tp1", "N/A"))
                        with col2:
                            st.metric("🎯 TP2 (Exit 40%)", f"Rp {tp2:,.0f}" if isinstance(tp2, (int, float)) else tp2)
                            st.caption(pick.get("risk_reward_tp2", "N/A"))
                        with col3:
                            st.metric("🎯 TP3 (Exit 30%)", f"Rp {tp3:,.0f}" if isinstance(tp3, (int, float)) else tp3)
                            st.caption(pick.get("risk_reward_tp3", "N/A"))
                        st.metric("🛑 Stop Loss", f"Rp {sl:,.0f}" if isinstance(sl, (int, float)) else sl)
                        st.info(f"Position Strategy: {pick.get('position_strategy', 'N/A')}")
                    else:
                        # Fallback to old target display if TP levels not available
                        t1 = pick.get("target_1", "N/A")
                        rr = pick.get("risk_reward", "N/A")
                        st.markdown(f"Target: **{t1}** | SL: **{sl}** | R/R: **{rr}**")

                    # Fundamental Fair Value
                    fair_value = pick.get("fair_value", {})
                    if fair_value:
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

                        with st.expander(f"📐 Detail Fair Value {ticker}", expanded=False):
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

                    # ML Day-1 Prediction
                    ml_pred = pick.get("ml_prediction", {})
                    if ml_pred:
                        pred_return = ml_pred.get("pred_return", 0)
                        ml_signal = ml_pred.get("signal", "N/A")
                        ml_conf = ml_pred.get("confidence", "N/A")

                        # Signal color
                        if ml_signal == "STRONG BUY":
                            signal_color = "🟢"
                        elif ml_signal == "BUY":
                            signal_color = "🟡"
                        elif ml_signal == "AVOID":
                            signal_color = "🔴"
                        else:
                            signal_color = "⚪"

                        st.markdown(f"🤖 **ML Forecast (T+1):** {signal_color} **{ml_signal}** | Return: **{pred_return:+.2f}%** | Confidence: {ml_conf}")

                    # Price Prediction
                    price_pred = pick.get("price_prediction", {})
                    if price_pred:
                        with st.expander("📊 **Price Prediction (1/3/5/7 hari ke depan)**", expanded=True):
                            # Current price
                            cp = price_pred.get('current_price', 'N/A')
                            st.metric("💰 Harga Sekarang", f"Rp {cp:,.0f}" if isinstance(cp, (int, float)) else cp)
                            
                            # Predictions in columns
                            predictions = price_pred.get("predictions", {})
                            col_d1, col_d3, col_d5, col_d7 = st.columns(4)
                            
                            if "day_1" in predictions:
                                pred = predictions["day_1"]
                                pct = pred.get('pct_change', 'N/A')
                                price = pred.get('price', 'N/A')
                                pct_num = float(str(pct).replace('%', '').replace('+', '')) if isinstance(pct, str) else 0
                                with col_d1:
                                    st.metric(
                                        "D+1", 
                                        f"Rp {int(price):,.0f}" if isinstance(price, (int, float)) else price,
                                        pct,
                                        delta_color="normal" if pct_num >= 0 else "inverse"
                                    )
                            
                            if "day_3" in predictions:
                                pred = predictions["day_3"]
                                pct = pred.get('pct_change', 'N/A')
                                price = pred.get('price', 'N/A')
                                pct_num = float(str(pct).replace('%', '').replace('+', '')) if isinstance(pct, str) else 0
                                with col_d3:
                                    st.metric(
                                        "D+3", 
                                        f"Rp {int(price):,.0f}" if isinstance(price, (int, float)) else price,
                                        pct,
                                        delta_color="normal" if pct_num >= 0 else "inverse"
                                    )
                            
                            if "day_5" in predictions:
                                pred = predictions["day_5"]
                                pct = pred.get('pct_change', 'N/A')
                                price = pred.get('price', 'N/A')
                                pct_num = float(str(pct).replace('%', '').replace('+', '')) if isinstance(pct, str) else 0
                                with col_d5:
                                    st.metric(
                                        "D+5", 
                                        f"Rp {int(price):,.0f}" if isinstance(price, (int, float)) else price,
                                        pct,
                                        delta_color="normal" if pct_num >= 0 else "inverse"
                                    )
                            
                            if "day_7" in predictions:
                                pred = predictions["day_7"]
                                pct = pred.get('pct_change', 'N/A')
                                price = pred.get('price', 'N/A')
                                pct_num = float(str(pct).replace('%', '').replace('+', '')) if isinstance(pct, str) else 0
                                with col_d7:
                                    st.metric(
                                        "D+7", 
                                        f"Rp {int(price):,.0f}" if isinstance(price, (int, float)) else price,
                                        pct,
                                        delta_color="normal" if pct_num >= 0 else "inverse"
                                    )
                            
                            st.divider()
                            
                            # Reasoning section
                            reasoning = price_pred.get("reasoning", "")
                            if reasoning:
                                st.markdown("### 📝 Reasoning")
                                st.markdown(reasoning)
                            
                            # Confidence badge
                            confidence = price_pred.get('confidence', 'N/A')
                            conf_color = "🟢" if confidence == "HIGH" else "🟡" if confidence == "MEDIUM" else "🔴"
                            st.markdown(f"{conf_color} **Confidence:** {confidence}")
                            
                            # Key drivers
                            drivers = price_pred.get("key_drivers", [])
                            if drivers:
                                st.markdown("### 📈 Key Drivers:")
                                for i, driver in enumerate(drivers, 1):
                                    st.markdown(f"{i}. {driver}")
                            
                            # Risks
                            risks = price_pred.get("risks", [])
                            if risks:
                                st.markdown("### ⚠️ Risks:")
                                for i, risk in enumerate(risks, 1):
                                    st.markdown(f"{i}. {risk}")

                with col3:
                    # Bandar signal
                    signal = pick.get("bandarm_signal", "N/A")
                    brokers = pick.get("broker_to_watch", [])
                    st.markdown(f"⚡ **{signal}**")
                    if brokers:
                        st.caption(f"Broker: {', '.join(brokers[:2])}")

                    broker_true_costs = pick.get("broker_true_costs", {})
                    true_cost_rows = broker_true_costs.get("w1m") or broker_true_costs.get("w7") or []
                    if true_cost_rows:
                        with st.expander("🏦 True Cost Broker Akumulasi", expanded=False):
                            import pandas as pd

                            def format_value(val):
                                if val >= 1e12: return f"{val/1e12:.2f}T"
                                if val >= 1e9: return f"{val/1e9:.2f}M"
                                if val >= 1e6: return f"{val/1e6:.2f}Jt"
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

                    broker_distributors = pick.get("broker_distributors", {})
                    dist_rows = broker_distributors.get("w1m") or broker_distributors.get("w7") or []
                    if dist_rows:
                        with st.expander("📉 Avg Sell Distribusi", expanded=False):
                            import pandas as pd

                            def format_value(val):
                                if val >= 1e12: return f"{val/1e12:.2f}T"
                                if val >= 1e9: return f"{val/1e9:.2f}M"
                                if val >= 1e6: return f"{val/1e6:.2f}Jt"
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
                    t1_str = f"{float(t1):,.0f}" if t1 else "N/A"
                    sl_str = f"{float(sl):,.0f}" if sl else "N/A"
                    st.markdown(
                        f"Target: **{t1_str}** | "
                        f"SL: **{sl_str}**"
                    )

                    # ML Day-1 Prediction from DB
                    ml_pred = sig.get("ml_prediction") or {}
                    if ml_pred:
                        pred_return = ml_pred.get("pred_return", 0)
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
                            f"🤖 **ML Forecast (T+1):** {signal_color} **{ml_signal}** "
                            f"| Return: **{float(pred_return):+.2f}%** | Confidence: {ml_conf}"
                        )

                    # Price Prediction from DB
                    price_pred = sig.get("price_prediction") or {}
                    if price_pred:
                        with st.expander("📊 **Price Prediction (1/3/5/7 hari ke depan)**", expanded=True):
                            cp = price_pred.get('current_price', 'N/A')
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

                    # Broker True Costs from DB
                    broker_true_costs = sig.get("broker_true_costs") or {}
                    true_cost_rows = broker_true_costs.get("w1m") or broker_true_costs.get("w7") or []
                    if true_cost_rows:
                        with st.expander("🏦 True Cost Broker Akumulasi", expanded=False):
                            import pandas as pd

                            def format_value(val):
                                if val >= 1e12: return f"{val/1e12:.2f}T"
                                if val >= 1e9: return f"{val/1e9:.2f}M"
                                if val >= 1e6: return f"{val/1e6:.2f}Jt"
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

                    # Broker Distributors from DB
                    broker_distributors = sig.get("broker_distributors") or {}
                    dist_rows = broker_distributors.get("w1m") or broker_distributors.get("w7") or []
                    if dist_rows:
                        with st.expander("📉 Avg Sell Distribusi", expanded=False):
                            import pandas as pd

                            def format_value(val):
                                if val >= 1e12: return f"{val/1e12:.2f}T"
                                if val >= 1e9: return f"{val/1e9:.2f}M"
                                if val >= 1e6: return f"{val/1e6:.2f}Jt"
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
                            if val >= 1e9: return f"{val/1e9:.2f}M"
                            if val >= 1e6: return f"{val/1e6:.2f}Jt"
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
                            if val >= 1e9: return f"{val/1e9:.2f}M"
                            if val >= 1e6: return f"{val/1e6:.2f}Jt"
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
                            if val >= 1e9: return f"{val/1e9:.2f}M"
                            if val >= 1e6: return f"{val/1e6:.2f}Jt"
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
                            if val >= 1e9: return f"{val/1e9:.2f}M"
                            if val >= 1e6: return f"{val/1e6:.2f}Jt"
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
        hits = sum(1 for p in perf_data if (p.get("result") or "").startswith("HIT_") and p.get("result") != "HIT_SL")
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
            result_icon = "✅" if (p.get("result") or "").startswith("HIT_") and p.get("result") != "HIT_SL" else "❌" if p.get("result") == "HIT_SL" else "🔄"
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
        st.caption("Status training dan validasi model ML Day-1.")

        model_path = "models/checkpoints/lgbm_day1.pkl"
        meta_path = "models/checkpoints/lgbm_day1_meta.json"
        if os.path.exists(model_path):
            st.success(f"Model aktif ditemukan: `{model_path}`")
        else:
            st.warning("Model aktif belum ditemukan. Workflow akan memakai rule-based fallback.")
            st.code("make train-ml", language="bash")

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
            st.info("Belum ada metadata training. Jalankan `make train-ml`.")

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

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Momentum", f"{comp.get('momentum', 0):.2f}")
        with col2:
            st.metric("Breadth", f"{comp.get('breadth', 0):.2f}")
        with col3:
            st.metric("Macro", f"{comp.get('macro', 0):.2f}")
        with col4:
            st.metric("Sectors", f"{comp.get('sectors', 0):.2f}")

        st.divider()

        # Analysis details
        st.subheader("📝 Analysis")
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
