import re

with open('/home/hamboo/my-product/stock-agent-idx/web-backend/main.py', 'r') as f:
    content = f.read()

acc_query = """
            # Calculate Historical Accuracy
            acc_query = text('''
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
            acc_res = conn.execute(acc_query).fetchone()
            accuracy = {"total": 0, "correct": 0, "percentage": 0}
            if acc_res and acc_res[0] > 0:
                t = acc_res[0]
                c = acc_res[1]
                accuracy = {
                    "total": t,
                    "correct": c,
                    "percentage": round((c/t)*100, 1)
                }
"""

if "Calculate Historical Accuracy" not in content:
    # Inject before history query
    content = content.replace("            # 2. Fetch history", acc_query + "\n            # 2. Fetch history")
    
    # Update return statement
    content = content.replace('return {"latest": latest, "history": history}', 'return {"latest": latest, "history": history, "accuracy": accuracy}')

with open('/home/hamboo/my-product/stock-agent-idx/web-backend/main.py', 'w') as f:
    f.write(content)
