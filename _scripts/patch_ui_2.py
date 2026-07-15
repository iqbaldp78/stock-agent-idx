import re

with open('/home/hamboo/my-product/stock-agent-idx/ui/app.py', 'r') as f:
    content = f.read()

acc_snippet = """
        # --- PERFORMA IHSG ---
        st.subheader("📊 Track Record Akurasi")
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
                        WHEN direction = 'BULLISH' AND actual_pct > 0 THEN 1
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
                st.info(f"**Akurasi Arah Historis:** {pct:.1f}% ({c}/{t} hari)")
        except:
            pass
            
        st.subheader("📝 Analysis (LLM Manager)")
"""

if "Track Record Akurasi" not in content:
    content = content.replace('st.subheader("📝 Analysis")', acc_snippet)

with open('/home/hamboo/my-product/stock-agent-idx/ui/app.py', 'w') as f:
    f.write(content)
