if page == "📈 Top Picks":
    st.title("📈 TOP PICKS")

    tab_regular, tab_konglo = st.tabs(["📊 Regular Top Picks", "🐋 Konglo Play Picks"])

    with tab_regular:
        # Get latest signals from DB by latest run_date (Regular)
        latest_meta = query_db("""
            SELECT MAX(run_date) AS max_run_date
            FROM signals
            WHERE batch_id IS NOT NULL AND is_konglo = FALSE
        """)
        latest_run_date = latest_meta[0]["max_run_date"] if latest_meta else None

    latest_batch = None
    if latest_run_date is not None:
        latest_batch = query_db("""
            SELECT batch_id
            FROM signals
            WHERE run_date = %s
            AND batch_id IS NOT NULL AND is_konglo = FALSE
            LIMIT 1
        """, (latest_run_date,))
        latest_batch = (latest_batch[0]["batch_id"] if latest_batch else None)

    if latest_batch or latest_run_date:
        display_batch = latest_batch or f"no-batch-{latest_run_date}"
        if isinstance(latest_run_date, datetime):
            display_lrd = (latest_run_date + timedelta(hours=7)).strftime("%d %b %Y, %H:%M WIB")
        elif isinstance(latest_run_date, str):
            try:
                parsed = datetime.strptime(latest_run_date[:19], "%Y-%m-%d %H:%M:%S")
                display_lrd = (parsed + timedelta(hours=7)).strftime("%d %b %Y, %H:%M WIB")
            except:
                display_lrd = latest_run_date
        else:
            display_lrd = str(latest_run_date)
            
        st.caption(f"Latest batch: `{display_batch}` | Updated: {display_lrd}")

    signals = []
    if latest_run_date is not None:
        if latest_batch:
            signals = query_db("""
                SELECT * FROM signals
                WHERE batch_id = %s
                AND rank IS NOT NULL
                ORDER BY rank
                LIMIT 3
            """, (latest_batch,))
        else:
            signals = query_db("""
                SELECT * FROM signals
                WHERE run_date = %s
                AND rank IS NOT NULL
                ORDER BY rank
                LIMIT 3
            """, (latest_run_date,))

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
                    
                    entry_style = ""
                    try:
                        cp = pick.get("price_prediction", {}).get("current_price")
                        el = pick.get("entry_low")
                        eh = pick.get("entry_high")
                        if el is None or eh is None:
                            parts = str(entry).split("-")
                            el = float(parts[0].replace(",", ""))
                            eh = float(parts[1].replace(",", ""))
                        if cp and isinstance(cp, (int, float)):
                            if cp < el * 0.995:
                                entry_style = " 🚀 *(Buy on Breakout)*"
                            elif cp > eh * 1.005:
                                entry_style = " 📉 *(Buy on Weakness)*"
                            else:
                                entry_style = " 🛒 *(Market Buy)*"
                    except Exception:
                        pass

                    st.markdown(f"🎯 Entry Ideal: **{entry}** | Max: **{max_e}**{entry_style}")

                    entry_reason = pick.get("entry_reasoning", "")
                    if entry_reason:
                        st.caption(f"💡 *{entry_reason}*")

                    # Take-Profit Levels
                    tp1 = pick.get("tp1")
                    tp2 = pick.get("tp2")
                    tp3 = pick.get("tp3")
                    sl = pick.get("stop_loss")

                    # Display TP levels with position sizing
                    if tp1 and tp2 and tp3:
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
                        st.markdown(f"Target: **{t1}** | SL: **{sl if sl else 'N/A'}** | R/R: **{rr}**")

                    # ML Swing (5-Day) Prediction
                    ml_pred = pick.get("ml_prediction", {})
                    if ml_pred:
                        # Extract signal and confidence directly from ml_prediction dict
                        ml_signal = ml_pred.get("signal", "N/A")
                        ml_conf = ml_pred.get("confidence", "N/A")
                        
                        # Calculate pred_return based on day_5 prediction and current_price
                        price_pred = pick.get("price_prediction", {})
                        cp_live = get_live_price(ticker)
                        cp = cp_live if cp_live else price_pred.get('current_price', 1)
                        predictions = price_pred.get("predictions", {})
                        day_5 = predictions.get("day_5", {})
                        day_5_price = day_5.get("price", cp)
                        
                        try:
                            pred_return = ((float(day_5_price) - float(cp)) / float(cp)) * 100
                        except (ValueError, TypeError, ZeroDivisionError):
                            pred_return = 0.0

                        # Signal color
                        if ml_signal == "STRONG BUY":
                            signal_color = "🟢"
                        elif ml_signal == "BUY":
                            signal_color = "🟡"
                        elif ml_signal == "AVOID":
                            signal_color = "🔴"
                        else:
                            signal_color = "⚪"

                        st.markdown(f"🤖 **ML Forecast (T+5):** {signal_color} **{ml_signal}** | Return: **{pred_return:+.2f}%** | Confidence: {ml_conf}")

                    # Price Prediction
                    price_pred = pick.get("price_prediction", {})
                    if price_pred:
                        with st.expander("📊 **Price Prediction (1/3/5/7 hari ke depan)**", expanded=True):
                            # Current price (Live)
                            cp_live = get_live_price(ticker)
                            cp = cp_live if cp_live else price_pred.get('current_price', 'N/A')
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
                        
                    # Fundamental Fair Value (moved here for UI alignment)
                    fair_value = pick.get("fair_value", {})
                    # Add defensive check to ensure fair_value is a dict, not None
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

                    broker_true_costs = pick.get("broker_true_costs", {})
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

                    broker_distributors = pick.get("broker_distributors", {})
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

                    # Thesis
                    thesis = pick.get("thesis", "")
                    if thesis:
                        with st.expander("📝 Investment Thesis", expanded=False):
                            st.markdown(thesis)

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


    else:
        st.info("Belum ada data. Klik **Run Analysis Now** di sidebar untuk memulai.")


    with tab_konglo:
        # Get latest Konglo signals from DB
        latest_konglo_meta = query_db("""
            SELECT MAX(run_date) AS max_run_date
            FROM signals
            WHERE is_konglo = TRUE
        """)
        latest_konglo_run_date = latest_konglo_meta[0]["max_run_date"] if latest_konglo_meta else None

        if latest_konglo_run_date:
            display_konglo_lrd = str(latest_konglo_run_date)
            if isinstance(latest_konglo_run_date, datetime):
                display_konglo_lrd = (latest_konglo_run_date + timedelta(hours=7)).strftime("%d %b %Y, %H:%M WIB")
            elif isinstance(latest_konglo_run_date, str):
                try:
                    parsed = datetime.strptime(latest_konglo_run_date[:19], "%Y-%m-%d %H:%M:%S")
                    display_konglo_lrd = (parsed + timedelta(hours=7)).strftime("%d %b %Y, %H:%M WIB")
                except:
                    pass
                    
            st.caption(f"Updated: {display_konglo_lrd}")
            
            konglo_signals = query_db("""
                SELECT * FROM signals
                WHERE run_date = %s
                AND is_konglo = TRUE
                AND rank IS NOT NULL
                ORDER BY rank
            """, (latest_konglo_run_date,))
            
            if not konglo_signals:
                st.info("Belum ada data hasil analisis Konglo Play.")
            else:
                for sig in konglo_signals:
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
                                st.markdown(f"🎯 Entry: **{float(entry_l):,.0f}–{float(entry_h):,.0f}**")
                            
                            t1 = sig.get("target_1")
                            sl = sig.get("stop_loss")
                            st.markdown(
                                f"Target: **{float(t1):,.0f}** | "
                                f"SL: **{float(sl):,.0f}**"
                            )

                            thesis = sig.get("thesis", "")
                            if thesis:
                                with st.expander("📝 Investment Thesis", expanded=False):
                                    st.markdown(thesis)
                                    
                        with col3:
                            bandar_avg_1m = sig.get("bandar_avg_1m", "N/A")
                            broker_utama = sig.get("broker_utama", "N/A")
                            st.markdown(f"⚡ **Akumulasi Bandar:**")
                            st.caption(f"Broker: {broker_utama}")
                            if bandar_avg_1m and bandar_avg_1m != "N/A":
                                st.caption(f"Avg Bandar (1M): Rp {float(bandar_avg_1m):,.0f}")
        else:
            st.info("Belum ada data analisis Konglo Play. Silakan jalankan analisis dari halaman Konglo Play.")

# === PAGE: Trading Engine ===

