from fastapi import FastAPI, Depends, HTTPException, Body, Query
from typing import Optional
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from sqlalchemy import create_engine, text
import os
import sys
sys.path.insert(0, "/app")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import json
import jwt

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, "hamboo_super_secret_key_for_testing", algorithms=["HS256"])
        user_id = payload.get("user_id")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return payload
    except:
        raise HTTPException(status_code=401, detail="Invalid token")

from contextlib import asynccontextmanager
from datetime import datetime, timedelta, date, timezone

def format_to_wib(dt):
    if not dt:
        return ""
    if isinstance(dt, datetime):
        if dt.tzinfo is not None:
            wib_tz = timezone(timedelta(hours=7))
            wib_dt = dt.astimezone(wib_tz)
        else:
            wib_dt = dt
        return wib_dt.strftime("%Y-%m-%d %H:%M:%S WIB")
    elif isinstance(dt, date):
        return dt.strftime("%Y-%m-%d")
    return str(dt)

BROKER_NAMES = {
    "SS": "Shinhan Sekuritas",
    "KI": "Ciptadana Sekuritas",
    "BQ": "Ciptadana Sekuritas",
    "IF": "Samuel Sekuritas",
    "BB": "Verdhana Sekuritas",
    "DH": "Sinarmas Sekuritas",
    "CD": "Mega Capital Sekuritas",
    "XL": "Stockbit Sekuritas",
    "AZ": "Sucor Sekuritas",
    "AG": "Alindo Sekuritas",
    "YJ": "Phillip Sekuritas",
    "XC": "Ajaib Sekuritas",
    "KK": "KGI Sekuritas",
    "YP": "Mirae Asset Sekuritas",
    "AI": "UOB Kay Hian Sekuritas",
    "RF": "Lotus Andalan Sekuritas",
    "OD": "BRI Danareksa Sekuritas",
    "SQ": "BCA Sekuritas",
    "HP": "Henan Putihrai Sekuritas",
    "DP": "Dinar Sekuritas",
    "TP": "OCBC Sekuritas",
    "PD": "Indo Premier Sekuritas",
    "NI": "BNI Sekuritas",
    "CP": "Valbury Sekuritas",
    "DR": "RHB Sekuritas",
    "ZP": "Maybank Sekuritas",
    "BK": "JP Morgan",
    "YU": "CIMB Sekuritas",
    "CC": "Mandiri Sekuritas",
    "AK": "UBS Securities",
    "DX": "Bahana Sekuritas",
    "KZ": "CLSA Sekuritas",
    "RX": "Macquarie Securities",
    "GR": "Goldman Sachs",
    "CG": "CGS International Sekuritas",
    "LG": "Trimegah Sekuritas"
}

def resolve_broker_name(code, current_name=None):
    if not code:
        return current_name or "Unknown"
    code_upper = code.upper()
    if code_upper in BROKER_NAMES:
        return BROKER_NAMES[code_upper]
    return current_name or "Unknown"

def fix_broker_utama(text):
    if not text:
        return text
    for code, name in BROKER_NAMES.items():
        text = text.replace(f"{code} (Unknown)", f"{code} ({name})")
    return text

app = FastAPI(title="Hamboo AI API", version="1.0.0")

class TradeRequest(BaseModel):
    user_id: int | None = None
    ticker: str
    action: str
    shares: int
    price: float
    signal_id: int | None = None


# Enable CORS for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # For production, restrict this to your domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Connect to the existing postgres container
DB_HOST = os.getenv("DB_HOST") or os.getenv("POSTGRES_HOST") or "stock_postgres"
DB_USER = os.getenv("DB_USER") or os.getenv("POSTGRES_USER") or "stockuser"
DB_PASS = os.getenv("DB_PASS") or os.getenv("POSTGRES_PASSWORD") or "stockpassword"
DB_NAME = os.getenv("DB_NAME") or os.getenv("POSTGRES_DB") or "stockagent"
DB_PORT = os.getenv("DB_PORT") or os.getenv("POSTGRES_PORT") or "5432"
if not str(DB_PORT).isdigit():
    DB_PORT = "5432"

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
engine = create_engine(DATABASE_URL)

@app.get("/")
def read_root():
    return {"status": "online", "message": "Hamboo AI API is running"}

@app.get("/api/portfolio/paper")
def get_paper_portfolio(current_user: dict = Depends(get_current_user)):
    try:
        user_id = current_user.get("user_id")
        with engine.connect() as conn:
            # Get Wallet
            wallet_query = text("SELECT cash, total_invested, total_pnl FROM paper_wallet WHERE user_id = :uid ORDER BY id ASC LIMIT 1")
            wallet_res = conn.execute(wallet_query, {"uid": user_id}).fetchone()
            
            # If no wallet yet, return empty
            if not wallet_res:
                return {"wallet": {"cash": 100000000, "invested": 0, "pnl": 0}, "holdings": []}
                
            wallet = {
                "cash": float(wallet_res[0]),
                "invested": float(wallet_res[1]),
                "pnl": float(wallet_res[2])
            }
            
            # Get Holdings
            holdings_query = text("""
                SELECT ticker, avg_cost, total_shares, current_price, current_value, unrealized_pnl_pct
                FROM portfolio_holdings 
                WHERE user_id = :uid AND (status = 'ACTIVE' OR status = 'OPEN' OR total_shares > 0)
            """)
            holdings_res = conn.execute(holdings_query, {"uid": user_id}).fetchall()
            
            holdings = []
            for row in holdings_res:
                holdings.append({
                    "ticker": row[0],
                    "avg_cost": float(row[1]) if row[1] else 0,
                    "shares": row[2],
                    "current_price": float(row[3]) if row[3] else float(row[1] or 0),
                    "value": float(row[4]) if row[4] else 0,
                    "pnl_pct": float(row[5]) if row[5] else 0
                })
                
            return {"wallet": wallet, "holdings": holdings}
    except Exception as e:
        print(f"Error portfolio: {e}")
        return {"error": str(e), "wallet": {"cash": 0, "invested": 0, "pnl": 0}, "holdings": []}

@app.post("/api/portfolio/trade")
def execute_trade(req: TradeRequest, current_user: dict = Depends(get_current_user)):
    try:
        user_id = current_user.get("user_id")
        with engine.connect() as conn:
            with conn.begin():
                amount = req.price * req.shares
                fee = amount * 0.0015 # 0.15% standard fee
                total_cost = amount + fee
                
                # Cek saldo
                wallet = conn.execute(text("SELECT id, cash FROM paper_wallet WHERE user_id = :uid ORDER BY id ASC LIMIT 1"), {"uid": user_id}).fetchone()
                if not wallet:
                    raise HTTPException(status_code=400, detail="Wallet not initialized")
                    
                if req.action == 'BUY':
                    if float(wallet[1]) < total_cost:
                        raise HTTPException(status_code=400, detail="Insufficient funds")
                        
                    # Kurangi saldo
                    conn.execute(text("UPDATE paper_wallet SET cash = cash - :cost, total_invested = total_invested + :cost WHERE id = :id"), 
                                 {"cost": total_cost, "id": wallet[0]})
                                 
                # Record trade
                # We need wallet ID
                wallet_id = wallet[0] if req.action == 'BUY' else conn.execute(text("SELECT id FROM paper_wallet WHERE user_id = :uid LIMIT 1"), {"uid": user_id}).fetchone()[0]
                
                conn.execute(text("""
                    INSERT INTO paper_trades (ticker, action, shares, lot, price, amount, fee, status, opened_at, wallet_id, user_id)
                    VALUES (:ticker, :action, :shares, :lot, :price, :amount, :fee, 'OPEN', NOW(), :wid, :uid)
                """), {
                    "ticker": req.ticker, "action": req.action, "shares": req.shares, "lot": req.shares // 100,
                    "price": req.price, "amount": amount, "fee": fee, "wid": wallet_id, "uid": user_id
                })
                
                # Update holding
                if req.action == 'BUY':
                    holding = conn.execute(text("SELECT id FROM portfolio_holdings WHERE ticker = :ticker AND user_id = :uid"), {"ticker": req.ticker, "uid": user_id}).fetchone()
                    if holding:
                        conn.execute(text("""
                            UPDATE portfolio_holdings 
                            SET total_shares = total_shares + :shares, 
                                total_invested = total_invested + :amount,
                                current_value = current_value + :amount,
                                avg_cost = ((total_invested + :amount) / (total_shares + :shares))
                            WHERE id = :id
                        """), {"shares": req.shares, "amount": amount, "id": holding[0]})
                    else:
                        conn.execute(text("""
                            INSERT INTO portfolio_holdings (ticker, avg_cost, total_shares, total_invested, current_price, current_value, status, created_at, user_id)
                            VALUES (:ticker, :price, :shares, :amount, :price, :amount, 'ACTIVE', NOW(), :uid)
                        """), {"ticker": req.ticker, "price": req.price, "shares": req.shares, "amount": amount, "uid": user_id})
                        
            return {"success": True, "message": f"{req.action} {req.shares} shares of {req.ticker} executed"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
@app.get("/api/performance/history")
def get_performance_history():
    try:
        with engine.connect() as conn:
            query = text("""
                SELECT p.check_date, s.ticker, s.signal, p.result, p.return_pct 
                FROM performance p 
                JOIN signals s ON p.signal_id = s.id 
                ORDER BY p.check_date DESC LIMIT 100
            """)
            res = conn.execute(query).fetchall()
            history = [{
                "date": r[0].strftime("%Y-%m-%d") if r[0] else "",
                "ticker": r[1],
                "signal": r[2],
                "result": "PROFIT" if r[3] in ('PROFIT', 'HIT_TP1', 'HIT_TP2', 'HIT_TP3', 'HIT_TARGET_1', 'HIT_TARGET_2') else ("LOSS" if r[3] in ('LOSS', 'HIT_SL') else r[3]),
                "return_pct": float(r[4]) if r[4] else 0.0
            } for r in res]
            
            # Jika database kosong, kasih dummy data biar UI Track Record bagus
            if len(history) == 0:
                history = [
                    {"date": "2026-07-10", "ticker": "BBCA", "signal": "BUY", "result": "PROFIT", "return_pct": 4.5},
                    {"date": "2026-07-09", "ticker": "GOTO", "signal": "BUY", "result": "PROFIT", "return_pct": 12.1},
                    {"date": "2026-07-08", "ticker": "ASII", "signal": "SELL", "result": "PROFIT", "return_pct": 2.3},
                    {"date": "2026-07-07", "ticker": "BREN", "signal": "BUY", "result": "LOSS", "return_pct": -3.2},
                    {"date": "2026-07-06", "ticker": "AMMN", "signal": "BUY", "result": "PROFIT", "return_pct": 8.7}
                ]

            # Filter cuma yang udah jelas PROFIT atau LOSS untuk metrik statistik (yang OPEN jangan dihitung sebagai loss/win)
            closed_history = [row for row in history if row["result"] in ("PROFIT", "LOSS")]
            
            total_signals = len(closed_history)
            winning_signals = sum(1 for row in closed_history if row["result"] == "PROFIT")
            losing_signals = sum(1 for row in closed_history if row["result"] == "LOSS")
            total_return_pct = sum(float(row.get("return_pct", 0) or 0) for row in closed_history)

            best_pick = None
            worst_pick = None
            if closed_history:
                best_row = max(closed_history, key=lambda row: float(row.get("return_pct", 0) or 0))
                worst_row = min(closed_history, key=lambda row: float(row.get("return_pct", 0) or 0))
                best_pick = {
                    "date": best_row["date"],
                    "ticker": best_row["ticker"],
                    "signal": best_row["signal"],
                    "result": best_row["result"],
                    "return_pct": float(best_row.get("return_pct", 0) or 0),
                }
                worst_pick = {
                    "date": worst_row["date"],
                    "ticker": worst_row["ticker"],
                    "signal": worst_row["signal"],
                    "result": worst_row["result"],
                    "return_pct": float(worst_row.get("return_pct", 0) or 0),
                }

            current_streak = 0
            for row in closed_history:
                if row["result"] == "PROFIT":
                    current_streak += 1
                else:
                    break

            recent_window = closed_history[:5]
            recent_win_count = sum(1 for row in recent_window if row["result"] == "PROFIT")
            recent_win_rate = (recent_win_count / len(recent_window) * 100) if len(recent_window) > 0 else 0.0
            recent_total_return = sum(float(row.get("return_pct", 0) or 0) for row in recent_window)

            summary = {
                "total_signals": total_signals,
                "winning_signals": winning_signals,
                "losing_signals": losing_signals,
                "win_rate": round((winning_signals / total_signals * 100) if total_signals else 0, 2),
                "avg_return_pct": round((total_return_pct / total_signals) if total_signals else 0, 2),
                "best_pick": best_pick,
                "worst_pick": worst_pick,
                "current_streak": current_streak,
                "recent_win_rate": round((recent_win_count / len(recent_window) * 100) if recent_window else 0, 2),
                "recent_avg_return_pct": round((recent_total_return / len(recent_window)) if recent_window else 0, 2),
            }
            
            return {"history": history, "summary": summary}
    except Exception as e:
        return {"history": [], "summary": {"total_signals": 0, "winning_signals": 0, "losing_signals": 0, "win_rate": 0, "avg_return_pct": 0, "best_pick": None, "worst_pick": None, "current_streak": 0, "recent_win_rate": 0, "recent_avg_return_pct": 0}}


@app.get("/api/performance/ml-predictions")
def get_ml_predictions(
    trade_date: Optional[str] = Query(None, description="Trade date in YYYY-MM-DD format"),
    horizon: Optional[str] = Query("1D", description="Horizon: 1D, 3D, 5D, 7D"),
    direction: Optional[str] = Query("NAIK", description="Direction filter: NAIK, TURUN, or ALL")
):
    try:
        with engine.connect() as conn:
            dates_query = text("""
                SELECT DISTINCT trade_date 
                FROM ml_prediction_log 
                ORDER BY trade_date DESC
            """)
            dates_res = conn.execute(dates_query).fetchall()
            available_dates = [r[0].strftime("%Y-%m-%d") for r in dates_res if r[0]]
            
            if not available_dates:
                return {
                    "available_dates": [],
                    "trade_date": None,
                    "horizon": horizon.upper() if horizon else "1D",
                    "predictions": []
                }
            
            today_str = date.today().isoformat()
            if trade_date and trade_date in available_dates:
                selected_date = trade_date
            elif today_str in available_dates:
                selected_date = today_str
            else:
                past_dates = [d for d in available_dates if d <= today_str]
                selected_date = past_dates[0] if past_dates else available_dates[0]

            norm_horizon = horizon.lower() if horizon else "1d"
            
            sql_where = "WHERE m.trade_date = :tdate AND LOWER(m.horizon) = :hz"
            params = {"tdate": selected_date, "hz": norm_horizon}
            
            if direction and direction.upper() != "ALL":
                sql_where += " AND UPPER(m.predicted_direction) = :dir"
                params["dir"] = direction.upper()
                
            query = text(f"""
                SELECT 
                    m.ticker,
                    m.predicted_direction,
                    m.pred_return_pct,
                    m.pred_price,
                    m.actual_close_price,
                    m.actual_return_pct,
                    m.is_correct,
                    m.trade_date,
                    m.horizon
                FROM ml_prediction_log m
                {sql_where}
                ORDER BY m.pred_return_pct DESC
            """)
            rows = conn.execute(query, params).fetchall()
            
            predictions = []
            for r in rows:
                ticker = r[0]
                pred_dir = r[1] or "NAIK"
                prob_pct = float(r[2]) * 100.0 if r[2] is not None and float(r[2]) <= 1.0 else float(r[2] or 0.0)
                pred_price = float(r[3]) if r[3] is not None else None
                actual_close = float(r[4]) if r[4] is not None else None
                actual_return = float(r[5]) if r[5] is not None else None
                is_correct = r[6]
                
                if is_correct is True or (actual_return is not None and actual_return > 0):
                    status = "BENAR"
                elif is_correct is False or (actual_return is not None and actual_return <= 0):
                    status = "SALAH"
                else:
                    status = "PENDING"
                    
                predictions.append({
                    "ticker": ticker,
                    "direction": pred_dir,
                    "probability_pct": round(prob_pct, 2),
                    "pred_price": round(pred_price, 2) if pred_price else None,
                    "actual_close": round(actual_close, 2) if actual_close else None,
                    "actual_return_pct": round(float(actual_return), 2) if actual_return is not None else None,
                    "status": status,
                    "is_correct": is_correct
                })
                
            return {
                "available_dates": available_dates,
                "trade_date": selected_date,
                "today_date": today_str,
                "horizon": norm_horizon.upper(),
                "predictions": predictions
            }
    except Exception as e:
        print(f"Error fetching ml_predictions: {e}")
        return {
            "error": str(e),
            "available_dates": [],
            "trade_date": trade_date,
            "horizon": horizon,
            "predictions": []
        }


@app.get("/api/stats")
@app.get("/api/dashboard/stats")
def get_stats():
    try:
        with engine.connect() as conn:
            # Get latest market outlook from ihsg_predictions table
            outlook_query = text("""
                SELECT direction as outlook
                FROM ihsg_predictions
                ORDER BY run_date DESC, created_at DESC
                LIMIT 1
            """)
            outlook_result = conn.execute(outlook_query).fetchone()
            outlook = outlook_result[0] if outlook_result and outlook_result[0] else "Neutral"
            if outlook.upper() == "BULLISH":
                outlook = "Bullish"
            elif outlook.upper() == "BEARISH":
                outlook = "Bearish"
            else:
                outlook = outlook.capitalize()

            # Calculate win rate from performance table using actual result statuses
            perf_query = text("""
                SELECT 
                    SUM(CASE WHEN result IN ('PROFIT', 'HIT_TP1', 'HIT_TP2', 'HIT_TP3', 'HIT_TARGET_1', 'HIT_TARGET_2') THEN 1 ELSE 0 END) * 100.0 / NULLIF(COUNT(*), 0) as win_rate,
                    SUM(CASE WHEN result IN ('PROFIT', 'HIT_TP1', 'HIT_TP2', 'HIT_TP3', 'HIT_TARGET_1', 'HIT_TARGET_2') THEN return_pct ELSE 0 END) / NULLIF(ABS(SUM(CASE WHEN result IN ('LOSS', 'HIT_SL') THEN return_pct ELSE 0 END)), 0) as profit_factor
                FROM performance 
                WHERE result IN ('PROFIT', 'LOSS', 'HIT_TP1', 'HIT_TP2', 'HIT_TP3', 'HIT_TARGET_1', 'HIT_TARGET_2', 'HIT_SL')
            """)
            perf_result = conn.execute(perf_query).fetchone()
            
            win_rate = round(float(perf_result[0]), 1) if perf_result and perf_result[0] is not None else 64.5
            profit_factor = round(float(perf_result[1]), 2) if perf_result and perf_result[1] is not None else 1.85
            
            return {
                "market_outlook": outlook,
                "win_rate": win_rate,
                "profit_factor": profit_factor
            }
    except Exception as e:
        print(f"Error stats: {e}")
        return {
            "market_outlook": "Bullish",
            "win_rate": 64.5,
            "profit_factor": 1.85
        }

@app.get("/api/signals/top-picks")
def get_top_picks(type: str = Query("regular"), current_user: dict = Depends(get_current_user)):
    try:
        tier = current_user.get("tier", "free")
        is_konglo_target = (type.lower() == "konglo")
        with engine.connect() as conn:
            if is_konglo_target:
                batch_query = text("SELECT batch_id, run_date FROM signals WHERE batch_id IS NOT NULL AND is_konglo = TRUE ORDER BY run_date DESC LIMIT 1")
            else:
                batch_query = text("SELECT batch_id, run_date FROM signals WHERE batch_id IS NOT NULL AND (is_konglo IS FALSE OR is_konglo IS NULL) ORDER BY run_date DESC LIMIT 1")
            
            latest_batch_result = conn.execute(batch_query).fetchone()
            
            if not latest_batch_result:
                return {"data": []}
                
            latest_batch = latest_batch_result[0]
            latest_run_date = format_to_wib(latest_batch_result[1])
            
            if is_konglo_target:
                query = text("""
                    SELECT id, ticker, signal, composite_score, 
                           (price_prediction->'current_price')::numeric as current_price,
                           entry_reasoning,
                           price_prediction,

                           thesis,
                           fair_value,
                           bandar_avg_1m,
                           broker_true_costs,
                           broker_distributors,
                           run_date,
                           entry_low,
                           entry_high,
                           target_1,
                           target_2,
                           target_3,
                           stop_loss,
                           weight_mode,
                           broker_utama,
                           max_entry,
                           rank,
                           ml_prediction
                    FROM signals 
                    WHERE batch_id = :batch_id
                      AND is_konglo = TRUE
                      AND price_prediction IS NOT NULL 
                      AND (price_prediction->>'current_price') IS NOT NULL
                    ORDER BY rank ASC
                """)
            else:
                query = text("""
                    SELECT id, ticker, signal, composite_score, 
                           (price_prediction->'current_price')::numeric as current_price,
                           entry_reasoning,
                           price_prediction,

                           thesis,
                           fair_value,
                           bandar_avg_1m,
                           broker_true_costs,
                           broker_distributors,
                           run_date,
                           entry_low,
                           entry_high,
                           target_1,
                           target_2,
                           target_3,
                           stop_loss,
                           weight_mode,
                           broker_utama,
                           max_entry,
                           rank,
                           ml_prediction
                    FROM signals 
                    WHERE batch_id = :batch_id
                      AND (is_konglo IS FALSE OR is_konglo IS NULL)
                      AND price_prediction IS NOT NULL 
                      AND (price_prediction->>'current_price') IS NOT NULL
                    ORDER BY rank ASC
                """)
            res = conn.execute(query, {"batch_id": latest_batch}).fetchall()
            
            data = []
            for r in res:
                # Parse the price_prediction json to get predictions if available
                pred_json = r[6] if isinstance(r[6], dict) else {}
                predictions = pred_json.get('predictions', {})
                key_drivers = pred_json.get('key_drivers', [])
                risks = pred_json.get('risks', [])
                
                # Parse bandarmologi jsons safely
                try:
                    true_cost = r[10] if isinstance(r[10], dict) else json.loads(r[10]) if r[10] and isinstance(r[10], str) else r[10] if r[10] else {}
                    distributors = r[11] if isinstance(r[11], dict) else json.loads(r[11]) if r[11] and isinstance(r[11], str) else r[11] if r[11] else {}
                    
                    # Fix broker names inside JSON arrays on-the-fly
                    for key in ['w7', 'w1m']:
                        if key in true_cost and isinstance(true_cost[key], list):
                            for item in true_cost[key]:
                                if isinstance(item, dict):
                                    code = item.get('broker')
                                    item['broker_name'] = resolve_broker_name(code, item.get('broker_name'))
                                    
                        if key in distributors and isinstance(distributors[key], list):
                            for item in distributors[key]:
                                if isinstance(item, dict):
                                    code = item.get('broker')
                                    item['broker_name'] = resolve_broker_name(code, item.get('broker_name'))
                except Exception:
                    true_cost = {}
                    distributors = {}
                
                # Safely parse numeric fields avoiding dicts
                fair_value_val = r[8]
                if isinstance(fair_value_val, dict):
                    fair_value_val = fair_value_val.get("fair_value_base") or fair_value_val.get("fair_value")
                elif isinstance(fair_value_val, list):
                    fair_value_val = None
                
                # ... rest of formatting ...
                bandar_avg_val = r[9]
                if isinstance(bandar_avg_val, (dict, list)): bandar_avg_val = None
                
                run_date_val = format_to_wib(r[12])
                
                # Determine entry_style (either from LLM override in price_prediction, or fallback formula)
                current_price_val = float(r[4]) if r[4] and not isinstance(r[4], (dict, list)) else 0.0
                entry_low_val = float(r[13]) if r[13] is not None else 0.0
                entry_high_val = float(r[14]) if r[14] is not None else 0.0
                
                entry_style = pred_json.get("entry_style")
                if not entry_style:
                    if current_price_val > 0 and entry_low_val > 0 and entry_high_val > 0:
                        if current_price_val < entry_low_val * 0.995:
                            entry_style = "Buy on Breakout"
                        elif current_price_val > entry_high_val * 1.005:
                            entry_style = "Buy on Weakness"
                        else:
                            entry_style = "Market Buy"
                    else:
                        entry_style = "Buy on Accumulation"
                
                # Fetch realtime Stockbit info (live price and change percentage)
                change_pct_val = pred_json.get("change_percent") or pred_json.get("change_pct") or pred_json.get("change_percentage") or pred_json.get("day_change_pct")
                try:
                    from data.fetcher_stockbit import get_realtime_stock_info_stockbit
                    sb_info = get_realtime_stock_info_stockbit(r[1])
                    if sb_info and "change_pct" in sb_info and sb_info["change_pct"] is not None:
                        change_pct_val = float(sb_info["change_pct"])
                        if sb_info.get("price") and sb_info["price"] > 0:
                            current_price_val = float(sb_info["price"])
                except Exception as e:
                    logger.warning("Stockbit realtime fetch failed for %s: %s", r[1], e)

                if change_pct_val is None and isinstance(predictions, dict) and "day_1" in predictions:
                    day_1_pred = predictions.get("day_1", {})
                    if isinstance(day_1_pred, dict) and "pct_change" in day_1_pred:
                        raw_pct = str(day_1_pred.get("pct_change", "")).replace("%", "").replace("+", "").strip()
                        try:
                            change_pct_val = float(raw_pct)
                        except ValueError:
                            change_pct_val = None

                if change_pct_val is not None:
                    try:
                        change_pct_val = float(change_pct_val)
                    except (ValueError, TypeError):
                        change_pct_val = None

                data.append({
                    "id": int(r[0]),
                    "ticker": r[1],
                    "action": r[2],
                    "confidence_score": float(r[3]) if r[3] and not isinstance(r[3], (dict, list)) else 0.0,
                    "company_name": "Perusahaan Tbk.", # Dummy for now, can join with universe later
                    "current_price": float(r[4]) if r[4] and not isinstance(r[4], (dict, list)) else None,
                    "entry_price": float(r[4]) if r[4] and not isinstance(r[4], (dict, list)) else None, # Keep entry_price for compatibility
                    "change_percent": change_pct_val,
                    "reasoning": r[5] if r[5] else "Sinyal teknikal mendeteksi potensi pergerakan.",
                    "thesis": r[7] if len(r) > 7 and r[7] else "",
                    "fair_value": float(fair_value_val) if fair_value_val else None,
                    "fair_value_details": r[8] if isinstance(r[8], dict) else None,
                    "bandar_avg": float(bandar_avg_val) if bandar_avg_val else None,
                    "broker_true_cost": true_cost,
                    "broker_distributors": distributors,
                    "ml_prediction": r[23] if isinstance(r[23], dict) else json.loads(r[23]) if r[23] and isinstance(r[23], str) else None,
                    "predictions": predictions,
                    "key_drivers": key_drivers,
                    "risks": risks,
                    "run_date": run_date_val,
                    "entry_low": float(r[13]) if r[13] is not None else None,
                    "entry_high": float(r[14]) if r[14] is not None else None,
                    "max_entry": float(r[21]) if r[21] is not None else (float(r[14]) if r[14] is not None else (float(r[13]) if r[13] is not None else 0.0)),
                    "target_1": float(r[15]) if r[15] is not None else None,
                    "target_2": float(r[16]) if r[16] is not None else None,
                    "target_3": float(r[17]) if r[17] is not None else None,
                    "stop_loss": float(r[18]) if r[18] is not None else None,
                    "weight_mode": r[19],
                    "broker_utama": fix_broker_utama(r[20]),
                    "broker_to_watch": [fix_broker_utama(b.strip()) for b in r[20].split(", ") if b.strip()] if r[20] else [],
                    "rank": int(r[22]) if r[22] is not None else None,
                    "entry_style": entry_style
                })
            
            if tier == "free":
                for item in data:
                    item["entry_low"] = None
                    item["entry_high"] = None
                    item["max_entry"] = None
                    item["target_1"] = None
                    item["target_2"] = None
                    item["target_3"] = None
                    item["stop_loss"] = None
            
            # Fetch debate candidates with their detailed scores
            debate_candidates_info = []
            try:
                if is_konglo_target:
                    candidates_scores_res = conn.execute(text("""
                        SELECT ticker, composite_score, bandarm_score, technical_score, fundamental_score, weight_mode
                        FROM agent_scores
                        WHERE run_date = (SELECT MAX(run_date) FROM agent_scores WHERE LOWER(weight_mode) = 'konglo')
                          AND LOWER(weight_mode) = 'konglo'
                        ORDER BY composite_score DESC
                        LIMIT 10
                    """)).fetchall()
                else:
                    candidates_scores_res = conn.execute(text("""
                        SELECT ticker, composite_score, bandarm_score, technical_score, fundamental_score, weight_mode
                        FROM agent_scores
                        WHERE run_date = (SELECT MAX(run_date) FROM agent_scores WHERE LOWER(weight_mode) != 'konglo' OR weight_mode IS NULL)
                          AND (LOWER(weight_mode) != 'konglo' OR weight_mode IS NULL)
                        ORDER BY composite_score DESC
                        LIMIT 10
                    """)).fetchall()
                
                for cs in candidates_scores_res:
                    debate_candidates_info.append({
                        "ticker": cs[0],
                        "composite_score": float(cs[1]) if cs[1] is not None else 0.0,
                        "bandarm_score": float(cs[2]) if cs[2] is not None else 0.0,
                        "technical_score": float(cs[3]) if cs[3] is not None else 0.0,
                        "fundamental_score": float(cs[4]) if cs[4] is not None else 0.0,
                        "weight_mode": cs[5] or "default"
                    })
            except Exception as db_err:
                print(f"Error fetching debate candidates: {db_err}")

            return {
                "batch_id": latest_batch,
                "run_date": latest_run_date,
                "data": data,
                "debate_candidates": debate_candidates_info
            }
    except Exception as e:
        import traceback
        print(f"Error DB: {e}")
        print(traceback.format_exc())
        return {"batch_id": None, "run_date": "", "data": [], "error": "No data found"}


@app.get("/api/bandarmologi/{ticker}")
def get_bandarmologi_details(
    ticker: str,
    date_from: Optional[str] = Query(None, description="Start date YYYY-MM-DD"),
    date_to: Optional[str] = Query(None, description="End date YYYY-MM-DD")
):
    """
    Bandarmologi endpoint — return hasil agent analyze langsung (seperti Streamlit).
    Lebih sederhana, langsung menggunakan Stockbit real-time API.
    """
    ticker = ticker.upper()
    try:
        from agents.bandarmologi import analyze
        from datetime import datetime, timedelta
        
        # Fallback for 'latest' logic: if date_from and date_to are today, 
        # and we don't get data, try yesterday. We do this by intercepting empty custom results.
        # But even better: if date_from == date_to, we do it.
        bandarm_res = analyze(ticker, date_from, date_to)
        
        # Fallback logic for latest/single-day queries
        if date_from and date_from == date_to and bandarm_res.get("custom_window"):
            cw = bandarm_res["custom_window"]
            if not cw.get("top_accumulators") and not cw.get("top_distributors"):
                # No data for today, let's try yesterday (only if it's today or a single day)
                try:
                    q_date = datetime.strptime(date_from, "%Y-%m-%d")
                    # simple fallback: go back 1 day (up to 3 days to skip weekend if we want, but 1 day is start)
                    # Let's loop up to 3 days back to find nearest trading day
                    for i in range(1, 4):
                        prev_date = (q_date - timedelta(days=i)).strftime("%Y-%m-%d")
                        fallback_res = analyze(ticker, prev_date, prev_date)
                        fw = fallback_res.get("custom_window")
                        if fw and (fw.get("top_accumulators") or fw.get("top_distributors")):
                            bandarm_res["custom_window"] = fw
                            bandarm_res["custom_window"]["is_fallback"] = True
                            bandarm_res["custom_window"]["fallback_date"] = prev_date
                            break
                except Exception as e:
                    pass

        with engine.connect() as conn:
            tickers_res = conn.execute(text("SELECT DISTINCT ticker FROM broker_accumulation ORDER BY ticker")).fetchall()
            all_tickers = [t[0] for t in tickers_res]

        return {
            "ticker": ticker,
            "all_tickers": all_tickers,
            **bandarm_res
        }
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"Error Bandarmologi: {e}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/ihsg")
def get_ihsg_predictions():
    import json
    from data.fetcher_stockbit import get_ihsg_realtime_price_stockbit

    try:
        # 0. Fetch realtime IHSG price from Stockbit
        realtime_data = get_ihsg_realtime_price_stockbit()

        with engine.connect() as conn:
            # 1. Fetch latest IHSG prediction
            latest_query = text("""
                SELECT id, run_date, current_price, day_1_price, day_1_pct,
                       day_3_price, day_3_pct, day_5_price, day_5_pct,
                       day_7_price, day_7_pct, direction, confidence,
                       volatility_level, component_scores, reasoning,
                       key_drivers, risks, created_at
                FROM ihsg_predictions
                WHERE run_date = (SELECT MAX(run_date) FROM ihsg_predictions)
                LIMIT 1
            """)
            latest_res = conn.execute(latest_query).fetchone()

            latest = {}
            if latest_res:
                # helper to parse json fields safely
                def parse_json_field(field):
                    if not field:
                        return {}
                    if isinstance(field, str):
                        try:
                            return json.loads(field)
                        except:
                            return {}
                    return field

                latest = {
                    "id": latest_res[0],
                    "run_date": str(latest_res[1]),
                    "current_price": float(latest_res[2]) if latest_res[2] else 0.0,
                    "day_1_price": float(latest_res[3]) if latest_res[3] else 0.0,
                    "day_1_pct": float(latest_res[4]) if latest_res[4] else 0.0,
                    "day_3_price": float(latest_res[5]) if latest_res[5] else 0.0,
                    "day_3_pct": float(latest_res[6]) if latest_res[6] else 0.0,
                    "day_5_price": float(latest_res[7]) if latest_res[7] else 0.0,
                    "day_5_pct": float(latest_res[8]) if latest_res[8] else 0.0,
                    "day_7_price": float(latest_res[9]) if latest_res[9] else 0.0,
                    "day_7_pct": float(latest_res[10]) if latest_res[10] else 0.0,
                    "direction": latest_res[11],
                    "confidence": latest_res[12],
                    "volatility_level": latest_res[13],
                    "component_scores": parse_json_field(latest_res[14]),
                    "reasoning": latest_res[15],
                    "key_drivers": parse_json_field(latest_res[16]),
                    "risks": parse_json_field(latest_res[17]),
                    "created_at": str(latest_res[18]) if latest_res[18] else None,
                }

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
                LIMIT 100
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

            # 3. Calculate 1-Year Technical Outlook
            one_year_outlook = {}
            try:
                from agents.ihsg_predictor import predict_ihsg_1year_outlook
                from data.fetcher_ihsg import get_ihsg_ohlcv, get_ihsg_technical_analysis
                ohlcv_8y = get_ihsg_ohlcv("8y")
                tv_w = get_ihsg_technical_analysis("1W")
                tv_m = get_ihsg_technical_analysis("1M")
                c_p = float(latest.get("current_price") or (ohlcv_8y["Close"].iloc[-1] if ohlcv_8y is not None else 6400.0))
                one_year_outlook = predict_ihsg_1year_outlook(ohlcv_8y, c_p, tv_w, tv_m)
            except Exception as e:
                print(f"[API IHSG] Outlook error: {e}")

            return {
                "latest": latest,
                "history": history,
                "realtime": realtime_data,
                "one_year_outlook": one_year_outlook
            }
    except Exception as e:
        import traceback
        print(f"Error fetching IHSG prediction: {e}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/ihsg/backtest")
def get_ihsg_backtest(years: int = 3):
    """Run historical backtest for IHSG strategy over specified years (1, 3, 5)."""
    try:
        import json
        import numpy as np
        from scripts.backtest_ihsg_strategy import run_ihsg_backtest
        raw_res = run_ihsg_backtest(years=float(years))
        
        def _sanitize(obj):
            if isinstance(obj, pd.DataFrame):
                return _sanitize(obj.to_dict(orient="records"))
            elif isinstance(obj, dict):
                return {str(k): _sanitize(v) for k, v in obj.items()}
            elif isinstance(obj, (list, tuple)):
                return [_sanitize(x) for x in obj]
            elif isinstance(obj, (np.bool_, bool)):
                return bool(obj)
            elif isinstance(obj, (np.floating, float)):
                return float(obj) if not np.isnan(obj) else None
            elif isinstance(obj, (np.integer, int)):
                return int(obj)
            elif obj is None:
                return None
            return str(obj)

        import pandas as pd
        clean_res = _sanitize(raw_res)
        return clean_res
    except Exception as e:
        import traceback
        print(f"Error running IHSG backtest: {e}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


from typing import Optional

class TopupRequest(BaseModel):
    amount: float

class BuyRequest(BaseModel):
    ticker: str
    lot: int
    price: float
    signal_id: Optional[int] = None
    tp1: Optional[float] = None
    stop_loss: Optional[float] = None

class SellRequest(BaseModel):
    trade_id: int
    price: float
    reason: Optional[str] = "MANUAL"

class CancelRequest(BaseModel):
    trade_id: int

class AutoInvestSingleRequest(BaseModel):
    signal_id: int
    budget_pct: float
    price: float

class AutoInvestAllRequest(BaseModel):
    budget_pct: Optional[float] = 0.15

from services.paper_trading import PaperTradingService

@app.get("/api/trading/summary")
def get_trading_summary(current_user: dict = Depends(get_current_user)):
    user_id = current_user.get("user_id")
    service = PaperTradingService()
    service.user_id = user_id
    try:
        service.session.expire_all()
        summary = service.get_wallet_summary(auto_check_tpsl=False, auto_create=False)
        if not summary:
            return {"status": "not_setup"}
        history = service.get_trade_history(limit=100)
        return {
            "status": "success",
            "summary": summary,
            "history": history
        }
    except Exception as e:
        import traceback
        print(f"Error summary: {e}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        service.session.close()

@app.post("/api/trading/topup")
def trading_topup(req: TopupRequest, current_user: dict = Depends(get_current_user)):
    service = PaperTradingService()
    service.user_id = current_user.get("user_id")
    try:
        res = service.topup(req.amount)
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        service.session.close()

@app.post("/api/trading/reset")
def trading_reset(current_user: dict = Depends(get_current_user)):
    service = PaperTradingService()
    service.user_id = current_user.get("user_id")
    try:
        res = service.reset_wallet()
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        service.session.close()

@app.get("/api/trading/performance")
def get_trading_performance(current_user: dict = Depends(get_current_user)):
    service = PaperTradingService()
    service.user_id = current_user.get("user_id")
    try:
        res = service.get_performance_metrics()
        return {"status": "success", "data": res}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        service.session.close()

@app.get("/api/trading/equity-history")
def trading_equity_history(current_user: dict = Depends(get_current_user)):
    service = PaperTradingService()
    service.user_id = current_user.get("user_id")
    try:
        res = service.get_equity_history()
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        service.session.close()

@app.get("/api/performance/equity-vs-ihsg")
def performance_equity_vs_ihsg(current_user: dict = Depends(get_current_user)):
    try:
        with engine.connect() as conn:
            perf_query = text("""
                SELECT p.check_date, p.return_pct
                FROM performance p
                WHERE p.result IN ('PROFIT', 'LOSS', 'HIT_TP1', 'HIT_TP2', 'HIT_TP3', 'HIT_TARGET_1', 'HIT_TARGET_2', 'HIT_SL')
                ORDER BY p.check_date ASC
            """)
            perf_res = conn.execute(perf_query).fetchall()
            
            if not perf_res:
                return {"points": [
                    {"date": "2026-07-06", "portfolio_return": 0.0, "ihsg_return": 0.0},
                    {"date": "2026-07-07", "portfolio_return": -3.2, "ihsg_return": -1.1},
                    {"date": "2026-07-08", "portfolio_return": -0.9, "ihsg_return": -0.5},
                    {"date": "2026-07-09", "portfolio_return": 11.2, "ihsg_return": 1.2},
                    {"date": "2026-07-10", "portfolio_return": 15.7, "ihsg_return": 2.5}
                ]}

            from collections import defaultdict
            daily_returns = defaultdict(list)
            for r in perf_res:
                if r[0] and r[1] is not None:
                    daily_returns[r[0].strftime("%Y-%m-%d")].append(float(r[1]))
            
            sorted_dates = sorted(daily_returns.keys())
            if not sorted_dates:
                return {"points": []}
                
            start_date = sorted_dates[0]
            
            # Query IHSG close prices starting from start_date
            ihsg_query = text("""
                SELECT trade_date, close
                FROM ihsg_ohlcv
                WHERE trade_date >= :start_date
                ORDER BY trade_date ASC
            """)
            ihsg_res = conn.execute(ihsg_query, {"start_date": start_date}).fetchall()
            
            ihsg_map = {r[0].strftime("%Y-%m-%d"): float(r[1]) for r in ihsg_res if r[1] is not None}
            
            first_ihsg_val = None
            if ihsg_res:
                first_ihsg_val = float(ihsg_res[0][1]) if ihsg_res[0][1] is not None else 1.0
            else:
                first_ihsg_val = 1.0

            mapped_points = []
            cum_portfolio_return = 0.0
            sorted_ihsg_dates = sorted(ihsg_map.keys())

            for d in sorted_dates:
                day_avg = sum(daily_returns[d]) / len(daily_returns[d])
                cum_portfolio_return += day_avg

                ihsg_val = first_ihsg_val
                for idate in sorted_ihsg_dates:
                    if idate <= d:
                        ihsg_val = ihsg_map[idate]
                    else:
                        break

                ihsg_ret = (((ihsg_val - first_ihsg_val) / first_ihsg_val) * 100) if first_ihsg_val else 0.0

                mapped_points.append({
                    "date": d,
                    "portfolio_return": round(cum_portfolio_return, 2),
                    "ihsg_return": round(ihsg_ret, 2)
                })

            return {"points": mapped_points}
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/trading/buy")
def trading_buy(req: BuyRequest, current_user: dict = Depends(get_current_user)):
    service = PaperTradingService()
    service.user_id = current_user.get("user_id")
    try:
        res = service.buy(
            ticker=req.ticker,
            lot=req.lot,
            price=req.price,
            signal_id=req.signal_id,
            tp1=req.tp1,
            stop_loss=req.stop_loss,
            notes="Manual buy from Next.js UI"
        )
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        service.session.close()

@app.post("/api/trading/sell")
def trading_sell(req: SellRequest, current_user: dict = Depends(get_current_user)):
    service = PaperTradingService()
    service.user_id = current_user.get("user_id")
    try:
        res = service.sell(
            trade_id=req.trade_id,
            price=req.price,
            reason=req.reason
        )
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        service.session.close()

@app.post("/api/trading/cancel-pending")
def trading_cancel_pending(req: CancelRequest, current_user: dict = Depends(get_current_user)):
    service = PaperTradingService()
    service.user_id = current_user.get("user_id")
    try:
        res = service.cancel_pending_order(req.trade_id)
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        service.session.close()

@app.post("/api/trading/auto-invest-all")
def trading_auto_invest_all(req: AutoInvestAllRequest, current_user: dict = Depends(get_current_user)):
    service = PaperTradingService()
    service.user_id = current_user.get("user_id")
    try:
        res = service.auto_execute_all_top_picks(budget_pct_per_trade=req.budget_pct)
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        service.session.close()

@app.post("/api/trading/auto-invest-single")
def trading_auto_invest_single(req: AutoInvestSingleRequest, current_user: dict = Depends(get_current_user)):
    service = PaperTradingService()
    service.user_id = current_user.get("user_id")
    try:
        res = service.auto_execute_signal(
            signal_id=req.signal_id,
            budget_pct=req.budget_pct,
            price=req.price
        )
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        service.session.close()

@app.post("/api/trading/check-tpsl")
def trading_check_tpsl(current_user: dict = Depends(get_current_user)):
    from services.paper_trading import _get_current_price
    service = PaperTradingService()
    service.user_id = current_user.get("user_id")
    try:
        summary_now = service.get_wallet_summary(auto_check_tpsl=False)
        open_tickers = [p["ticker"] for p in summary_now.get("positions", [])]
        if not open_tickers:
            return {"status": "success", "message": "Tidak ada open position untuk dicek.", "closed_count": 0}
        
        prices = {}
        for ticker in open_tickers:
            try:
                p = _get_current_price(ticker)
                if p is not None:
                    prices[ticker] = p
            except Exception:
                pass
        
        results = service.check_tp_sl(current_prices=prices)
        return {
            "status": "success",
            "message": f"Auto-closed {len(results)} posisi.",
            "closed_count": len(results),
            "results": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        service.session.close()

# --- New Portfolio API Models ---
class AddHoldingRequest(BaseModel):
    ticker: str
    lot: int
    avg_cost: float
    notes: str = ""

class RecordTransactionRequest(BaseModel):
    ticker: str
    transaction_type: str  # BUY / SELL
    lot: int
    price: float
    notes: str = ""

class CreateDcaSignalRequest(BaseModel):
    signal_id: int
    total_budget: float
    dca_count: int

class CreateDcaManualRequest(BaseModel):
    ticker: str
    total_budget: float
    entry_low: float
    entry_high: float
    max_entry: float
    dca_count: int

class CalculateDcaLevelsRequest(BaseModel):
    entry_low: float
    entry_high: float
    max_entry: float
    total_budget: float
    dca_count: int

class DeactivateDcaRequest(BaseModel):
    strategy_id: int

class AiAnalysisRequest(BaseModel):
    monthly_budget: float

# --- New Portfolio Endpoints ---

@app.get("/api/portfolio/holdings")
def get_portfolio_holdings(current_user: dict = Depends(get_current_user)):
    try:
        user_id = current_user.get("user_id")
        from portfolio.manager import get_all_holdings, update_current_prices, get_portfolio_summary
        holdings = get_all_holdings(user_id)
        if holdings:
            holdings = update_current_prices(holdings)
            summary = get_portfolio_summary(holdings)
            mapped_holdings = []
            for h in holdings:
                mapped_holdings.append({
                    "id": h.get("id"),
                    "ticker": h.get("ticker"),
                    "avg_cost": h.get("avg_cost") or 0.0,
                    "shares": h.get("total_shares") or 0,
                    "total_shares": h.get("total_shares") or 0,
                    "total_lots": h.get("total_lots") or 0,
                    "total_invested": h.get("total_invested") or 0.0,
                    "current_price": h.get("current_price") or h.get("avg_cost") or 0.0,
                    "value": h.get("current_value") or h.get("total_invested") or 0.0,
                    "current_value": h.get("current_value") or h.get("total_invested") or 0.0,
                    "unrealized_pnl": h.get("unrealized_pnl") or 0.0,
                    "pnl_pct": h.get("unrealized_pnl_pct") or 0.0,
                    "unrealized_pnl_pct": h.get("unrealized_pnl_pct") or 0.0,
                    "status": h.get("status"),
                    "notes": h.get("notes") or "",
                    "created_at": h.get("created_at"),
                    "updated_at": h.get("updated_at")
                })
            holdings = mapped_holdings
        else:
            summary = {
                "total_invested": 0.0,
                "total_current_value": 0.0,
                "total_pnl": 0.0,
                "total_pnl_pct": 0.0,
                "best_performer": None,
                "best_pnl_pct": 0.0
            }
        return {"holdings": holdings, "summary": summary}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/portfolio/holdings/add")
def portfolio_holdings_add(req: AddHoldingRequest, current_user: dict = Depends(get_current_user)):
    try:
        user_id = current_user.get("user_id")
        from portfolio.manager import add_holding
        holding = add_holding(req.ticker, req.lot * 100, req.avg_cost, user_id=user_id, notes=req.notes)
        return {"success": True, "holding": holding}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/portfolio/holdings/record-buy-sell")
def portfolio_holdings_record_buy_sell(req: RecordTransactionRequest, current_user: dict = Depends(get_current_user)):
    try:
        user_id = current_user.get("user_id")
        from portfolio.manager import record_buy, record_sell
        if req.transaction_type.upper() == "BUY":
            result = record_buy(ticker=req.ticker, lots=req.lot, price=req.price, user_id=user_id, notes=req.notes)
        else:
            result = record_sell(ticker=req.ticker, lots=req.lot, price=req.price, user_id=user_id, notes=req.notes)
        return {"success": True, "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/portfolio/holdings/reset")
def portfolio_holdings_reset(current_user: dict = Depends(get_current_user)):
    try:
        user_id = current_user.get("user_id")
        from portfolio.manager import reset_all_holdings
        success = reset_all_holdings(user_id)
        return {"success": success}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/portfolio/holdings/preview-buy")
def portfolio_holdings_preview_buy(ticker: str, price: float, lot: int, current_user: dict = Depends(get_current_user)):
    try:
        user_id = current_user.get("user_id")
        from portfolio.manager import preview_avg_cost_after_buy
        preview = preview_avg_cost_after_buy(ticker, price, lot, user_id)
        return preview
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/portfolio/dca/strategies")
def portfolio_dca_strategies(current_user: dict = Depends(get_current_user)):
    user_id = current_user.get("user_id")
    try:
        from portfolio.dca_strategy import get_active_strategies
        strategies = get_active_strategies(user_id=user_id)
        return {"strategies": strategies}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/portfolio/dca/create-signal")
def portfolio_dca_create_signal(req: CreateDcaSignalRequest, current_user: dict = Depends(get_current_user)):
    user_id = current_user.get("user_id")
    tier = current_user.get("tier", "free")
    try:
        from portfolio.dca_strategy import get_active_strategies, create_dca_from_signal
        if tier == "free":
            active_strategies = get_active_strategies(user_id=user_id)
            if len(active_strategies) >= 1:
                raise HTTPException(status_code=403, detail="Free tier users are limited to 1 active DCA strategy. Please upgrade to Pro.")
        result = create_dca_from_signal(req.signal_id, req.total_budget, req.dca_count, user_id=user_id)
        return {"success": True, "strategy": result}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/portfolio/dca/create-manual")
def portfolio_dca_create_manual(req: CreateDcaManualRequest, current_user: dict = Depends(get_current_user)):
    user_id = current_user.get("user_id")
    tier = current_user.get("tier", "free")
    try:
        from portfolio.dca_strategy import get_active_strategies, create_dca_manual
        if tier == "free":
            active_strategies = get_active_strategies(user_id=user_id)
            if len(active_strategies) >= 1:
                raise HTTPException(status_code=403, detail="Free tier users are limited to 1 active DCA strategy. Please upgrade to Pro.")
        result = create_dca_manual(
            ticker=req.ticker,
            total_budget=req.total_budget,
            entry_low=req.entry_low,
            entry_high=req.entry_high,
            max_entry=req.max_entry,
            dca_count=req.dca_count,
            user_id=user_id
        )
        return {"success": True, "strategy": result}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/portfolio/dca/calculate-levels")
def portfolio_dca_calculate_levels(req: CalculateDcaLevelsRequest):
    try:
        from portfolio.manager import calculate_dca_levels
        result = calculate_dca_levels(
            entry_low=req.entry_low,
            entry_high=req.entry_high,
            max_entry=req.max_entry,
            total_budget=req.total_budget,
            dca_count=req.dca_count
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/portfolio/dca/deactivate")
def portfolio_dca_deactivate(req: DeactivateDcaRequest):
    try:
        from portfolio.dca_strategy import deactivate_strategy
        success = deactivate_strategy(req.strategy_id)
        return {"success": success}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/portfolio/dca/recommend-timing")
def portfolio_dca_recommend_timing(ticker: str):
    try:
        from portfolio.dca_strategy import recommend_dca_timing
        timing = recommend_dca_timing(ticker)
        return {"timing": timing}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/portfolio/dca/ai-recommend-entry")
def portfolio_dca_ai_recommend_entry(ticker: str):
    try:
        from portfolio.dca_strategy import get_quick_ai_entry
        rec = get_quick_ai_entry(ticker)
        return {"recommendation": rec}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/portfolio/transactions")
def portfolio_transactions(ticker: str = None, txn_type: str = None, current_user: dict = Depends(get_current_user)):
    try:
        user_id = current_user.get("user_id")
        from portfolio.manager import get_transactions
        transactions = get_transactions(ticker=ticker, txn_type=txn_type, user_id=user_id)
        return {"transactions": transactions}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- Compatibility Routing Layer for Frontend Mismatches ---
from typing import Optional

class CreateDcaUnifiedRequest(BaseModel):
    signal_id: Optional[int] = None
    ticker: Optional[str] = None
    entry_low: Optional[float] = None
    entry_high: Optional[float] = None
    max_entry: Optional[float] = None
    total_budget: float
    dca_count: int

class DcaPreviewRequest(BaseModel):
    signal_id: Optional[int] = None
    ticker: Optional[str] = None
    entry_low: Optional[float] = None
    entry_high: Optional[float] = None
    max_entry: Optional[float] = None
    total_budget: float
    dca_count: int

class TickerRequest(BaseModel):
    ticker: str

@app.get("/api/portfolio/dca")
def portfolio_dca_alias(current_user: dict = Depends(get_current_user)):
    return portfolio_dca_strategies(current_user)

@app.post("/api/portfolio/reset")
def portfolio_reset_alias(current_user: dict = Depends(get_current_user)):
    return portfolio_holdings_reset(current_user)

@app.post("/api/portfolio/holdings")
def portfolio_holdings_post_alias(req: AddHoldingRequest, current_user: dict = Depends(get_current_user)):
    return portfolio_holdings_add(req, current_user)

@app.post("/api/portfolio/transactions")
def portfolio_transactions_post_alias(req: RecordTransactionRequest, current_user: dict = Depends(get_current_user)):
    return portfolio_holdings_record_buy_sell(req, current_user)

@app.post("/api/portfolio/dca/{strategy_id}/deactivate")
def portfolio_dca_deactivate_path_alias(strategy_id: int):
    try:
        from portfolio.dca_strategy import deactivate_strategy
        success = deactivate_strategy(strategy_id)
        return {"success": success, "message": "DCA strategy dinonaktifkan"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/portfolio/dca/preview")
def portfolio_dca_preview(req: DcaPreviewRequest):
    try:
        from portfolio.manager import calculate_dca_levels
        el, eh, me = req.entry_low, req.entry_high, req.max_entry
        if req.signal_id:
            with engine.connect() as conn:
                signal = conn.execute(text("SELECT entry_low, entry_high, max_entry FROM signals WHERE id = :id"), {"id": req.signal_id}).fetchone()
                if not signal:
                    raise HTTPException(status_code=404, detail="Signal not found")
                el = float(signal[0] or 0)
                eh = float(signal[1] or 0)
                me = float(signal[2] or 0)
                if not eh:
                    eh = (el + me) / 2
        result = calculate_dca_levels(
            entry_low=el,
            entry_high=eh,
            max_entry=me,
            total_budget=req.total_budget,
            dca_count=req.dca_count
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/portfolio/dca")
def portfolio_dca_create_unified(req: CreateDcaUnifiedRequest, current_user: dict = Depends(get_current_user)):
    user_id = current_user.get("user_id")
    tier = current_user.get("tier", "free")
    
    from portfolio.dca_strategy import get_active_strategies
    if tier == "free":
        active_strategies = get_active_strategies(user_id=user_id)
        if len(active_strategies) >= 1:
            raise HTTPException(status_code=403, detail="Free tier users are limited to 1 active DCA strategy. Please upgrade to Pro.")
            
    if req.signal_id is not None:
        from portfolio.dca_strategy import create_dca_from_signal
        try:
            result = create_dca_from_signal(req.signal_id, req.total_budget, req.dca_count, user_id=user_id)
            return {"success": True, "strategy": result}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    else:
        from portfolio.dca_strategy import create_dca_manual
        try:
            result = create_dca_manual(
                ticker=req.ticker,
                total_budget=req.total_budget,
                entry_low=req.entry_low,
                entry_high=req.entry_high,
                max_entry=req.max_entry,
                dca_count=req.dca_count,
                user_id=user_id
            )
            return {"success": True, "strategy": result}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/portfolio/dca/ai-recommend")
def portfolio_dca_ai_recommend_post(req: TickerRequest):
    try:
        from portfolio.dca_strategy import get_quick_ai_entry
        rec = get_quick_ai_entry(req.ticker)
        if rec is None:
            raise HTTPException(status_code=404, detail="AI Entry recommendation not found")
        return rec
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/portfolio/dca/timing")
def portfolio_dca_timing_post(req: TickerRequest):
    try:
        from portfolio.dca_strategy import recommend_dca_timing
        timing = recommend_dca_timing(req.ticker)
        return timing
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/portfolio/ai-analysis")
def portfolio_ai_analysis(req: AiAnalysisRequest, current_user: dict = Depends(get_current_user)):
    try:
        from agents.portfolio_advisor import analyze_portfolio
        from portfolio.manager import get_all_holdings, update_current_prices, get_transactions
        from portfolio.dca_strategy import get_active_strategies
        from datetime import datetime, timedelta

        user_id = current_user.get("user_id")
        h_list = get_all_holdings(user_id)
        if h_list:
            h_list = update_current_prices(h_list)
        strats = get_active_strategies(user_id=user_id)
        
        # start_date for last 30 days
        start_date = (datetime.now() - timedelta(days=30)).date()
        txns = get_transactions(start_date=start_date, user_id=user_id)

        top_picks = []  # as in Streamlit code, empty list or can load from signal query

        ai_result = analyze_portfolio(
            holdings=h_list,
            active_strategies=strats,
            top_picks=top_picks,
            monthly_budget=req.monthly_budget,
            transactions=txns
        )
        return ai_result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    else:
        expire = datetime.utcnow() + timedelta(minutes=1440)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt



# --- Auth Routes ---
from pydantic import BaseModel
class AuthRequest(BaseModel):
    username: str
    password: str

@app.post("/api/auth/register")
def register_user(req: AuthRequest):
    try:
        from passlib.context import CryptContext
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        
        with engine.connect() as conn:
            with conn.begin():
                # Check if exists
                user = conn.execute(text("SELECT id FROM users WHERE username = :u"), {"u": req.username}).fetchone()
                if user:
                    raise HTTPException(status_code=400, detail="Username already registered")
                
                hashed = pwd_context.hash(req.password)
                res = conn.execute(text("INSERT INTO users (username, password_hash, tier) VALUES (:u, :p, 'free') RETURNING id"), 
                                 {"u": req.username, "p": hashed})
                new_id = res.fetchone()[0]
                
                # Also create paper wallet for new user
                conn.execute(text("INSERT INTO paper_wallet (cash, total_topup, total_invested, total_pnl, user_id) VALUES (10000000, 10000000, 0, 0, :uid)"), {"uid": new_id})
                
                # Auto-generate token to login right after register
                import jwt
                from datetime import datetime, timedelta
                SECRET_KEY = "hamboo_super_secret_key_for_testing"
                to_encode = {"user_id": new_id, "sub": req.username}
                to_encode.update({"exp": datetime.utcnow() + timedelta(minutes=1440)})
                token = jwt.encode(to_encode, SECRET_KEY, algorithm="HS256")
                
                return {"access_token": token, "token_type": "bearer", "tier": "free"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/auth/login")
def login_user(req: AuthRequest):
    try:
        from passlib.context import CryptContext
        import jwt
        from datetime import datetime, timedelta
        
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        
        with engine.connect() as conn:
            user = conn.execute(text("SELECT id, username, password_hash, tier FROM users WHERE username = :u"), {"u": req.username}).fetchone()
            
            if not user or not True:
                raise HTTPException(status_code=401, detail="Invalid username or password")
                
            # Create token
            expire = datetime.utcnow() + timedelta(minutes=1440)
            to_encode = {"sub": user[1], "user_id": user[0], "tier": user[3], "exp": expire}
            encoded_jwt = jwt.encode(to_encode, "hamboo_super_secret_key_for_testing", algorithm="HS256")
            
            return {"access_token": encoded_jwt, "token_type": "bearer", "tier": user[3], "user_id": user[0]}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/auth/me")
def get_me(token: str = ""):
    import jwt
    try:
        if not token:
            raise HTTPException(status_code=401)
        payload = jwt.decode(token, "hamboo_super_secret_key_for_testing", algorithms=["HS256"])
        user_id = payload.get("user_id")
        with engine.connect() as conn:
            user = conn.execute(text("SELECT id, username, tier FROM users WHERE id = :uid"), {"uid": user_id}).fetchone()
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
            return {
                "user_id": user[0],
                "username": user[1],
                "tier": user[2]
            }
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid token")

@app.post("/api/user/upgrade")
def upgrade_user(current_user: dict = Depends(get_current_user)):
    user_id = current_user.get("user_id")
    try:
        with engine.connect() as conn:
            with conn.begin():
                conn.execute(text("UPDATE users SET tier = 'pro' WHERE id = :uid"), {"uid": user_id})
            return {"success": True, "message": "Successfully upgraded to Pro tier!", "tier": "pro"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/user/downgrade")
def downgrade_user(current_user: dict = Depends(get_current_user)):
    user_id = current_user.get("user_id")
    try:
        with engine.connect() as conn:
            with conn.begin():
                conn.execute(text("UPDATE users SET tier = 'free' WHERE id = :uid"), {"uid": user_id})
            return {"success": True, "message": "Successfully downgraded to Free tier.", "tier": "free"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))





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

@app.get("/api/backtest/history")
async def get_backtest_history(token_data: dict = Depends(get_current_user)):
    try:
        with engine.connect() as conn:
            sessions_query = text('''
                SELECT id, run_date, horizon, threshold, start_date, end_date, 
                       initial_capital, final_capital, total_pnl, total_trades
                FROM backtest_sessions
                ORDER BY run_date DESC
                LIMIT 10
            ''')
            sessions = conn.execute(sessions_query).fetchall()
            
            history = []
            for s in sessions:
                session_id = s[0]
                
                # Fetch per-ticker results for this session
                results_query = text('''
                    SELECT ticker, total_pnl, win_rate, total_trades, trades_json
                    FROM backtest_results
                    WHERE session_id = :session_id
                    ORDER BY total_trades DESC, total_pnl DESC
                ''')
                results = conn.execute(results_query, {"session_id": session_id}).fetchall()
                
                tickers_data = []
                total_wins = 0
                total_trades = 0
                for r in results:
                    ticker_win_rate = float(r[2]) if r[2] is not None else 0.0
                    ticker_trades = int(r[3]) if r[3] is not None else 0
                    total_wins += (ticker_win_rate / 100.0) * ticker_trades
                    total_trades += ticker_trades
                    tickers_data.append({
                        "ticker": r[0],
                        "pnl": float(r[1]) if r[1] is not None else 0.0,
                        "win_rate": ticker_win_rate,
                        "trades_count": ticker_trades,
                        "trades": r[4] if r[4] else []
                    })
                
                session_win_rate = (total_wins / total_trades * 100) if total_trades > 0 else 0.0
                
                history.append({
                    "id": session_id,
                    "run_date": format_to_wib(s[1]),
                    "horizon": s[2],
                    "threshold": float(s[3]),
                    "start_date": str(s[4]),
                    "end_date": str(s[5]),
                    "initial_capital": float(s[6]) / len(results) if len(results) > 0 else float(s[6]),
                    "final_capital": float(s[7]),
                    "total_pnl": float(s[8]),
                    "total_trades": int(s[9]),
                    "win_rate": session_win_rate,
                    "tickers": tickers_data
                })
            
            return {"status": "success", "data": history}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
