import os
import sys
import argparse
import pandas as pd
from datetime import datetime
import json
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.fetcher_stockbit import get_ohlcv_range
from data.ml_features import prepare_training_data
from models.multiday_predictor import MultiDayPredictor


logging.basicConfig(level=logging.INFO, format="%(message)s")

def run_ml_backtest(ticker: str, start_date: str, end_date: str, initial_capital: float, horizon: str, threshold: float):
    raw = get_ohlcv_range(ticker, "2020-01-01", end_date)
    if raw.empty:
        print(f"Empty raw for {ticker}")
        return None
    try: X, Y = prepare_training_data(raw, ticker=ticker)
    except Exception as e:
        print(f"Error prep: {e}")
        return None
    X_test = X.loc[(X.index >= start_date) & (X.index <= end_date)].copy()
    if X_test.empty:
        print(f"Empty X_test for {start_date} to {end_date}")
        return None

    checkpoints_dir = "/app/models/checkpoints"
    predictor = MultiDayPredictor(ticker=ticker.upper(), checkpoints_dir=checkpoints_dir)
    # Tweak to fallback load lower/upper case if exact doesnt match
    if not os.path.exists(predictor._get_model_path(horizon)):
        predictor.ticker = predictor.ticker.lower()
        if not os.path.exists(predictor._get_model_path(horizon)):
            predictor.ticker = ticker.upper()
    
    predictor._load_models()
    if predictor.models.get(horizon) is None:
        print(f"Model horizon {horizon} not found")
        return None

    capital = initial_capital
    position = 0
    buy_price = 0
    trades = []
    prices = raw.loc[X_test.index]
    if len(prices) != len(X_test): prices = raw.loc[raw.index.isin(X_test.index)]
    dates = X_test.index.tolist()
    
    for i in range(len(dates)):
        current_date = dates[i]
        feature_row = X_test.iloc[[i]]
        current_close = float(prices.loc[current_date, 'Close'])
        preds = predictor.predict(feature_row)
        
        # Ekstrak nilai prediksi, karena dict berisi value angka
        if isinstance(preds, dict):
            prob = preds.get(horizon, 0)
        else:
            prob = 0
            
        # Logging prob
        logging.debug(f"Date {current_date}: prob {prob}")
        
        # Eksekusi Exit Terlebih Dahulu
        if position > 0:
            open_trade = trades[-1]
            if open_trade["status"] == "OPEN" and str(current_date) >= open_trade["target_exit_date"]:
                sell_price = current_close
                revenue = open_trade["shares"] * sell_price
                capital += revenue
                pnl = revenue - (open_trade["shares"] * open_trade["buy_price"])
                pnl_pct = (sell_price - open_trade["buy_price"]) / open_trade["buy_price"] * 100
                open_trade.update({"status": "CLOSED", "sell_date": str(current_date), "sell_price": sell_price, "pnl": round(pnl, 2), "pnl_pct": round(pnl_pct, 2)})
                position = 0; buy_price = 0
                
        # Cek Sinyal Buy jika belum ada posisi
        if position == 0:
            if prob >= threshold:
                position = (capital // current_close)
                if position > 0:
                    buy_price = current_close
                    cost = position * buy_price
                    capital -= cost
                    days_to_hold = int(horizon[0])
                    exit_idx = min(i + days_to_hold, len(dates) - 1)
                    exit_date = dates[exit_idx]
                    trades.append({
                        "ticker": ticker, "buy_date": str(current_date), "buy_price": buy_price,
                        "target_exit_date": str(exit_date), "prob": round(prob * 100, 2), "shares": position,
                        "status": "OPEN", "sell_date": None, "sell_price": None, "pnl": 0
                    })
                
    if position > 0 and len(trades) > 0 and trades[-1]["status"] == "OPEN":
        last_date = dates[-1]
        last_close = float(prices.loc[last_date, 'Close'])
        open_trade = trades[-1]
        revenue = open_trade["shares"] * last_close
        capital += revenue
        pnl = revenue - (open_trade["shares"] * open_trade["buy_price"])
        pnl_pct = (last_close - open_trade["buy_price"]) / open_trade["buy_price"] * 100
        open_trade.update({"status": "CLOSED (EOP)", "sell_date": str(last_date), "sell_price": last_close, "pnl": round(pnl, 2), "pnl_pct": round(pnl_pct, 2)})
        position = 0
        
    total_trades = len(trades)
    win_trades = len([t for t in trades if t.get("pnl", 0) > 0])
    win_rate = (win_trades / total_trades * 100) if total_trades > 0 else 0
    final_pnl = capital - initial_capital
    return {
        "ticker": ticker, "initial_capital": initial_capital, "final_capital": round(capital, 2),
        "total_pnl": round(final_pnl, 2), "pnl_pct": round(final_pnl / initial_capital * 100, 2),
        "total_trades": total_trades, "win_rate_pct": round(win_rate, 2), "trades": trades
    }

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--ticker", type=str, default="BBCA")
    parser.add_argument("--start", type=str, default="2026-01-01")
    parser.add_argument("--end", type=str, default="2026-12-31")
    parser.add_argument("--capital", type=float, default=10000000)
    parser.add_argument("--horizon", type=str, default="1d")
    parser.add_argument("--threshold", type=float, default=0.50)
    args = parser.parse_args()
    
    if args.ticker.upper() == "ALL":
        from config import get_universe
        tickers = get_universe()
        logging.info(f"Running ML Backtest for ALL ({len(tickers)} tickers) | Horizon: {args.horizon} | Threshold: {args.threshold*100}%")
    else:
        tickers = [t.strip().upper() for t in args.ticker.split(',')]
        logging.info(f"Running ML Backtest for {tickers} | Horizon: {args.horizon} | Threshold: {args.threshold*100}%")
        
    if not tickers:
        print("No tickers to run")
        sys.exit(0)
    
    results = []
    
    for tk in tickers:
        try:
            res = run_ml_backtest(tk, args.start, args.end, args.capital, args.horizon, args.threshold)
            if res: results.append(res)
        except Exception as e:
            logging.error(f"Error backtesting {tk}: {e}")
            
    if not results:
        print("No valid results")
        sys.exit(0)
        
    print("\n=== MULTI-TICKER SUMMARY ===")
    
    # Calculate portfolio aggregates
    total_capital = sum(r['final_capital'] for r in results)
    total_initial = sum(r['initial_capital'] for r in results)
    port_pnl = total_capital - total_initial
    port_pct = (port_pnl / total_initial) * 100 if total_initial > 0 else 0
    total_trades_all = sum(r['total_trades'] for r in results)
    
    # Save to database
    try:
        from db import SessionLocal
        # ignore import unresolved for dynamic import
        from db.models import BacktestSession, BacktestResult # type: ignore
        db = SessionLocal()
        session_db = BacktestSession(
            horizon=args.horizon,
            threshold=args.threshold,
            start_date=datetime.strptime(args.start, "%Y-%m-%d").date(),
            end_date=datetime.strptime(args.end, "%Y-%m-%d").date(),
            initial_capital=total_initial,
            final_capital=total_capital,
            total_pnl=port_pnl,
            total_trades=total_trades_all
        )
        db.add(session_db)
        db.flush()
        
        for res in results:
            res_db = BacktestResult(
                session_id=session_db.id,
                ticker=res['ticker'],
                initial_capital=res['initial_capital'],
                final_capital=res['final_capital'],
                total_pnl=res['total_pnl'],
                win_rate=res['win_rate_pct'],
                total_trades=res['total_trades'],
                trades_json=res['trades']
            )
            db.add(res_db)
        db.commit()
        print(f"\n[INFO] Saved BacktestSession (ID: {session_db.id}) to DB.")
        db.close()
    except Exception as e:
        print(f"\n[WARN] Failed to save session to DB: {e}")
    
    print(f"Total Tickers : {len(results)}")
    print(f"Total Trades  : {total_trades_all}")
    print(f"Initial Port  : Rp {total_initial:,.2f}")
    print(f"Final Port    : Rp {total_capital:,.2f}")
    print(f"Net Port P&L  : Rp {port_pnl:,.2f} ({port_pct:.2f}%)")
    print("============================\n")
    
    for res in results:
        print(f"\n--- {res['ticker']} ---")
        print(f"Trades   : {res['total_trades']} (Win: {res['win_rate_pct']}%)")
        print(f"Net P&L  : Rp {res['total_pnl']:,.2f} ({res['pnl_pct']}%)")
        if len(res['trades']) > 0 and args.ticker.upper() != "ALL":
            df = pd.DataFrame(res['trades'])
            print(df[['buy_date', 'prob', 'buy_price', 'sell_date', 'sell_price', 'pnl_pct']].to_string(index=False))
