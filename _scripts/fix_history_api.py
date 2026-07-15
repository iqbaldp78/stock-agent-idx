import re

with open('/home/hamboo/my-product/stock-agent-idx/web-backend/main.py', 'r') as f:
    content = f.read()

new_hist_query = """
            # 2. Fetch historical predictions (last 20) with actual outcome calculation
            hist_query = text('''
                WITH actuals AS (
                    SELECT trade_date, close as actual_close
                    FROM ihsg_ohlcv
                )
                SELECT 
                    p.run_date, p.current_price, p.day_1_price, p.day_1_pct, p.direction, p.confidence,
                    (SELECT a.actual_close FROM actuals a WHERE a.trade_date > p.run_date::date ORDER BY a.trade_date ASC LIMIT 1) as actual_price
                FROM ihsg_predictions p
                ORDER BY p.run_date DESC
                LIMIT 20
            ''')
            hist_res = conn.execute(hist_query).fetchall()
            history = []
            for r in hist_res:
                actual_price = float(r[6]) if r[6] else None
                curr_price = float(r[1]) if r[1] else 0.0
                dir_pred = r[4]
                
                is_correct = None
                if actual_price and curr_price > 0:
                    actual_pct = ((actual_price - curr_price) / curr_price) * 100
                    if dir_pred == 'BULLISH' and actual_pct > 0:
                        is_correct = True
                    elif dir_pred == 'BEARISH' and actual_pct < 0:
                        is_correct = True
                    elif dir_pred == 'SIDEWAYS' and abs(actual_pct) < 0.5:
                        is_correct = True
                    else:
                        is_correct = False

                history.append({
                    "run_date": str(r[0]),
                    "current_price": curr_price,
                    "day_1_price": float(r[2]) if r[2] else 0.0,
                    "day_1_pct": float(r[3]) if r[3] else 0.0,
                    "direction": dir_pred,
                    "confidence": r[5],
                    "actual_price": actual_price,
                    "is_correct": is_correct
                })
"""

# Replace the old history fetching block
pattern = r"# 2\. Fetch historical predictions.*?history\.append\(\{.*?\}\)\n"
content = re.sub(pattern, new_hist_query, content, flags=re.DOTALL)

with open('/home/hamboo/my-product/stock-agent-idx/web-backend/main.py', 'w') as f:
    f.write(content)
