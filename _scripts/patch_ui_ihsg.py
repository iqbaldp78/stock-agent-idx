import re

with open('/home/hamboo/my-product/stock-agent-idx/ui/app.py', 'r') as f:
    content = f.read()

# Add accuracy score to IHSG tab display
accuracy_snippet = """
        # Performance accuracy info if available
        acc = query_db(\"\"\"
            SELECT 
                COUNT(*) as total_predictions,
                SUM(CASE 
                    WHEN p.direction = 'BULLISH' AND (a.close - p.current_price) > 0 THEN 1
                    WHEN p.direction = 'BEARISH' AND (a.close - p.current_price) < 0 THEN 1
                    WHEN p.direction = 'SIDEWAYS' AND abs(a.close - p.current_price)/p.current_price*100 < 0.5 THEN 1
                    ELSE 0 
                END) as correct_direction
            FROM ihsg_predictions p
            JOIN ihsg_ohlcv a ON a.trade_date = p.run_date::date + INTERVAL '1 day'
        \"\"\")
        
        st.subheader("🤖 AI Reasoning (IM Persona)")
"""

if "AI Reasoning (IM Persona)" not in content:
    content = content.replace("st.subheader(\"AI Reasoning\")", accuracy_snippet)
    
# Or let's just grep the actual code first to see how it's structured currently
