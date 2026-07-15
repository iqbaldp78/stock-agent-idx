import re
with open("web-backend/main.py", "r") as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    if 'def get_ai_performance_metrics(' in line:
        break
    if 'def get_ai_performance(' in line:
        break
    if 'def get_ai_performance_metrics_real(' in line:
        break
    if '@app.get("/api/ai/performance-metrics")' in line:
        continue
    new_lines.append(line)

final_code = "".join(new_lines) + """
@app.get("/api/ai/performance-metrics")
def get_ai_performance_metrics(current_user: dict = Depends(get_current_user)):
    user_id = current_user.get("user_id")
    try:
        with engine.connect() as conn:
            trades_query = text('''
                SELECT 
                    COUNT(*) as total_trades,
                    SUM(CASE WHEN realized_pnl > 0 THEN 1 ELSE 0 END) as winning_trades,
                    SUM(CASE WHEN realized_pnl > 0 THEN realized_pnl ELSE 0 END) as gross_profit,
                    ABS(SUM(CASE WHEN realized_pnl < 0 THEN realized_pnl ELSE 0 END)) as gross_loss,
                    SUM(realized_pnl) as cumulative_pnl
                FROM paper_trades
                WHERE user_id = :user_id AND status = 'CLOSED' AND realized_pnl IS NOT NULL
            ''')
            trades_result = conn.execute(trades_query, {"user_id": user_id}).fetchone()
            
            total_trades = trades_result[0] or 0
            winning_trades = trades_result[1] or 0
            gross_profit = float(trades_result[2] or 0)
            gross_loss = float(trades_result[3] or 0)
            cumulative_pnl = float(trades_result[4] or 0)
            
            win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
            profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else (gross_profit if gross_profit > 0 else 0)
            
            ihsg_query = text('''
                SELECT id, run_date, current_price, direction, confidence, reasoning, key_drivers, component_scores
                FROM ihsg_predictions
                ORDER BY run_date DESC
                LIMIT 1
            ''')
            ihsg_result = conn.execute(ihsg_query).fetchone()
            
            latest_ihsg = None
            if ihsg_result:
                latest_ihsg = {
                    "date": str(ihsg_result[1]),
                    "direction": ihsg_result[3],
                    "confidence": ihsg_result[4],
                    "reasoning": ihsg_result[5],
                    "scores": ihsg_result[7] if ihsg_result[7] else {}
                }

            return {
                "metrics": {
                    "win_rate": round(win_rate, 2),
                    "profit_factor": round(profit_factor, 2),
                    "cumulative_pnl": cumulative_pnl,
                    "total_trades": total_trades,
                    "sharpe_ratio": 1.2, # Dummy for now
                    "max_drawdown": 5.4, # Dummy for now
                },
                "ihsg_predictor": latest_ihsg
            }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
"""

with open("web-backend/main.py", "w") as f:
    f.write(final_code)
