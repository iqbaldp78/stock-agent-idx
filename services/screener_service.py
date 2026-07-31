import os
import json
import logging
from datetime import date, datetime
import pandas as pd
from config import get_universe
from db import SessionLocal
from db.models import Universe, CandlestickSignal, AgentScore, BrokerAccumulation
from data.fetcher_stockbit import get_ohlcv
from agents.candlestick_patterns import detect_candlestick_patterns
from data.fetcher_tradingview import get_technical_analysis

logger = logging.getLogger(__name__)

CACHE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "dashboard", "output"))

def _get_tickers_by_universe(universe_type: str = "ALL") -> list[str]:
    """Retrieve ticker list based on selected universe type."""
    db = SessionLocal()
    try:
        if universe_type == "LQ45":
            rows = db.query(Universe.ticker).filter(Universe.is_lq45 == True, Universe.active == True).all()
            return [r[0] for r in rows]
        elif universe_type == "KONGLO":
            rows = db.query(Universe.ticker).filter(Universe.is_konglo == True, Universe.active == True).all()
            return [r[0] for r in rows]
        elif universe_type == "CUSTOM":
            rows = db.query(Universe.ticker).filter(Universe.is_custom == True, Universe.active == True).all()
            return [r[0] for r in rows]
        else:
            rows = db.query(Universe.ticker).filter(Universe.active == True).all()
            if rows:
                return [r[0] for r in rows]
            return get_universe()
    except Exception as e:
        logger.error(f"Error getting universe tickers for {universe_type}: {e}")
        return get_universe()
    finally:
        db.close()


def _normalize_df(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize DataFrame columns to lower case."""
    if df is not None and not df.empty:
        df.columns = [str(c).lower() for c in df.columns]
    return df


def scan_candlestick_patterns(universe_tickers: list[str]) -> list[dict]:
    """Scan Candlestick Patterns with win-rate BEI context."""
    results = []
    for ticker in universe_tickers:
        try:
            df = _normalize_df(get_ohlcv(ticker, period="1mo"))
            if df is None or df.empty or len(df) < 5 or 'close' not in df.columns:
                continue
            patterns = detect_candlestick_patterns(df)
            last_close = float(df['close'].iloc[-1])
            prev_close = float(df['close'].iloc[-2]) if len(df) > 1 else last_close
            change_pct = ((last_close - prev_close) / prev_close) * 100
            
            if patterns:
                for p in patterns:
                    sig = p.get("signal", "NEUTRAL")
                    results.append({
                        "ticker": ticker,
                        "pattern": p.get("name", "Unknown"),
                        "signal": sig,
                        "win_rate": float(p.get("win_rate_bei", 0.50) * 100),
                        "context": p.get("best_context", "-"),
                        "price": last_close,
                        "change_pct": round(change_pct, 2)
                    })
        except Exception as e:
            logger.debug(f"Error scanning candlestick for {ticker}: {e}")
    
    # Sort by win-rate descending
    results.sort(key=lambda x: x["win_rate"], reverse=True)
    return results


def scan_haka_volume_spike(universe_tickers: list[str]) -> list[dict]:
    """Scan stocks experiencing HAKA (Aggressive Buying Volume Spike vs 20MA)."""
    results = []
    for ticker in universe_tickers:
        try:
            df = _normalize_df(get_ohlcv(ticker, period="1mo"))
            if df is None or df.empty or len(df) < 20 or 'close' not in df.columns or 'volume' not in df.columns:
                continue
            vol = df['volume']
            close = df['close']
            ma20_vol = vol.rolling(20).mean()
            
            curr_vol = float(vol.iloc[-1])
            avg_vol = float(ma20_vol.iloc[-1]) if pd.notnull(ma20_vol.iloc[-1]) and ma20_vol.iloc[-1] > 0 else 1.0
            vol_multiplier = round(curr_vol / avg_vol, 2)
            
            curr_price = float(close.iloc[-1])
            prev_price = float(close.iloc[-2])
            change_pct = ((curr_price - prev_price) / prev_price) * 100
            
            # HAKA Criteria: Price up (> 1%) & Volume > 1.5x 20-day MA
            if change_pct > 0.5 and vol_multiplier >= 1.3:
                status = "🚀 SUPER HAKA" if (vol_multiplier >= 2.5 and change_pct >= 3.0) else "⚡ HAKA"
                results.append({
                    "ticker": ticker,
                    "price": curr_price,
                    "change_pct": round(change_pct, 2),
                    "volume_multiplier": vol_multiplier,
                    "status": status,
                    "volume": int(curr_vol),
                    "avg_volume_20d": int(avg_vol)
                })
        except Exception as e:
            logger.debug(f"Error scanning HAKA for {ticker}: {e}")
            
    results.sort(key=lambda x: (x["volume_multiplier"], x["change_pct"]), reverse=True)
    return results


def scan_broker_dominance(universe_tickers: list[str]) -> list[dict]:
    """Scan stocks with strong Broker Accumulation / Foreign Net Buy Dominance."""
    results = []
    db = SessionLocal()
    try:
        for ticker in universe_tickers:
            try:
                # Query recent broker accumulation for last 7 days
                records = db.query(BrokerAccumulation).filter(BrokerAccumulation.ticker == ticker).order_by(BrokerAccumulation.trade_date.desc()).limit(14).all()
                if not records:
                    continue
                
                tot_buy_val = sum(r.buy_value for r in records if r.buy_value)
                tot_sell_val = sum(r.sell_value for r in records if r.sell_value)
                tot_foreign_net = sum(r.foreign_net for r in records if r.foreign_net)
                
                net_acc_val = tot_buy_val - tot_sell_val
                
                if tot_buy_val > 0 or tot_foreign_net > 0:
                    acc_label = "ACCUMULATION" if net_acc_val > 0 else "DISTRIBUTION"
                    foreign_label = "NET BUY" if tot_foreign_net > 0 else "NET SELL"
                    
                    # Fetch current price safely
                    df = _normalize_df(get_ohlcv(ticker, period="5d"))
                    curr_price = 0.0
                    change_pct = 0.0
                    if df is not None and not df.empty and 'close' in df.columns:
                        curr_price = float(df['close'].iloc[-1])
                        if len(df) > 1:
                            prev_price = float(df['close'].iloc[-2])
                            if prev_price > 0:
                                change_pct = round(((curr_price - prev_price) / prev_price) * 100, 2)
                    
                    results.append({
                        "ticker": ticker,
                        "price": curr_price,
                        "change_pct": change_pct,
                        "accumulation_status": acc_label,
                        "net_value_idr": net_acc_val,
                        "foreign_flow": foreign_label,
                        "foreign_net_val": tot_foreign_net
                    })
            except Exception as item_err:
                logger.debug(f"Error scanning broker dominance for {ticker}: {item_err}")
    except Exception as e:
        logger.error(f"Error scanning broker dominance DB query: {e}")
    finally:
        db.close()
        
    results.sort(key=lambda x: x["net_value_idr"], reverse=True)
    return results


def scan_technical_breakout(universe_tickers: list[str]) -> list[dict]:
    """Scan stocks with Technical Breakout / TradingView TA Strong Buy Sinyal."""
    results = []
    for ticker in universe_tickers:
        try:
            ta = get_technical_analysis(ticker)
            if not ta or "error" in ta or "summary" not in ta:
                continue
            
            summary = ta.get("summary", {})
            recommendation = summary.get("RECOMMENDATION", "NEUTRAL")
            buy_count = summary.get("BUY", 0)
            sell_count = summary.get("SELL", 0)
            neutral_count = summary.get("NEUTRAL", 0)
            
            indicators = ta.get("indicators", {})
            rsi = indicators.get("RSI", 50.0)
            macd = indicators.get("MACD.macd", 0.0)
            macd_signal = indicators.get("MACD.signal", 0.0)
            
            close_price = indicators.get("close", 0.0)
            sma20 = indicators.get("SMA20", 0.0)
            sma50 = indicators.get("SMA50", 0.0)
            
            is_breakout = (close_price > sma20 > sma50) if (sma20 and sma50) else False
            
            if recommendation in ["STRONG_BUY", "BUY"] or is_breakout:
                results.append({
                    "ticker": ticker,
                    "price": round(close_price, 2),
                    "recommendation": recommendation,
                    "buy_signals": buy_count,
                    "sell_signals": sell_count,
                    "rsi_14": round(rsi, 2) if rsi else 50.0,
                    "macd_bullish": (macd > macd_signal) if (macd and macd_signal) else False,
                    "ma_alignment": "MA20 > MA50 Bullish" if is_breakout else "Neutral"
                })
        except Exception as e:
            logger.debug(f"Error scanning technical breakout for {ticker}: {e}")
            
    results.sort(key=lambda x: (x["recommendation"] == "STRONG_BUY", x["buy_signals"]), reverse=True)
    return results


def scan_deep_undervalued(universe_tickers: list[str]) -> list[dict]:
    """Scan stocks with Deep Undervalued Margin of Safety."""
    results = []
    # Check latest debate_result.json or backtest_result.json in workspace
    json_path = os.path.join(os.path.dirname(__file__), "..", "debate_result.json")
    if not os.path.exists(json_path):
        json_path = os.path.join(os.path.dirname(__file__), "..", "last_analysis_result.json")
        
    if os.path.exists(json_path):
        try:
            with open(json_path, 'r') as f:
                data = json.load(f)
                picks = data.get("top_picks", [])
                for pick in picks:
                    ticker = pick.get("ticker")
                    if ticker in universe_tickers or not universe_tickers:
                        fv = pick.get("fair_value", {})
                        mos = fv.get("margin_of_safety_pct", 0.0)
                        upside = fv.get("upside_pct", 0.0)
                        label = fv.get("valuation_label", "N/A")
                        results.append({
                            "ticker": ticker,
                            "price": fv.get("current_price", 0.0),
                            "fair_value_base": fv.get("fair_value_base", 0.0),
                            "margin_of_safety_pct": round(mos, 2),
                            "upside_pct": round(upside, 2),
                            "valuation_label": label,
                            "conviction": pick.get("conviction", "MEDIUM")
                        })
        except Exception as e:
            logger.error(f"Error scanning deep undervalued: {e}")
            
    results.sort(key=lambda x: x["margin_of_safety_pct"], reverse=True)
    return results


def scan_konglo_momentum(universe_tickers: list[str]) -> list[dict]:
    """Scan momentum on Konglo group tickers."""
    from services.konglo_screener import run_konglo_screen
    try:
        res = run_konglo_screen()
        if isinstance(res, dict) and "picks" in res:
            return res.get("picks", [])
        elif isinstance(res, list):
            return res
        return []
    except Exception as e:
        logger.error(f"Error scanning konglo momentum: {e}")
        return []


def scan_oversold_bounce(universe_tickers: list[str]) -> list[dict]:
    """Scan stocks with RSI < 35 (Oversold Bounce setup)."""
    results = []
    for ticker in universe_tickers:
        try:
            ta = get_technical_analysis(ticker)
            if not ta or "indicators" not in ta:
                continue
            indicators = ta.get("indicators", {})
            rsi = indicators.get("RSI", 50.0)
            close = indicators.get("close", 0.0)
            
            if rsi and rsi < 35.0:
                results.append({
                    "ticker": ticker,
                    "price": round(close, 2),
                    "rsi": round(rsi, 2),
                    "status": "🎯 EXTREME OVERSOLD" if rsi < 25 else "⚡ OVERSOLD",
                    "recommendation": ta.get("summary", {}).get("RECOMMENDATION", "NEUTRAL")
                })
        except Exception as e:
            logger.debug(f"Error scanning oversold bounce for {ticker}: {e}")
            
    results.sort(key=lambda x: x["rsi"])
    return results


def get_screener_data(screener_type: str, universe_type: str = "ALL", force_scan: bool = False) -> list[dict]:
    """Main entry point to get screener results, supporting caching & fast load."""
    import re
    os.makedirs(CACHE_DIR, exist_ok=True)
    clean_type = re.sub(r'[^a-zA-Z0-9_]', '', screener_type.lower().replace(' ', '_'))
    cache_file = os.path.join(CACHE_DIR, f"screener_{clean_type}_{universe_type.lower()}.json")
    
    # Return cache if valid & not force_scan
    if not force_scan and os.path.exists(cache_file):
        try:
            mtime = os.path.getmtime(cache_file)
            # 6 hours cache
            if (datetime.now().timestamp() - mtime) < 21600:
                with open(cache_file, 'r') as f:
                    return json.load(f)
        except Exception:
            pass
            
    tickers = _get_tickers_by_universe(universe_type)
    
    if "candlestick" in screener_type.lower():
        data = scan_candlestick_patterns(tickers)
    elif "haka" in screener_type.lower():
        data = scan_haka_volume_spike(tickers)
    elif "broker" in screener_type.lower() or "dominance" in screener_type.lower():
        data = scan_broker_dominance(tickers)
    elif "technical" in screener_type.lower() or "breakout" in screener_type.lower():
        data = scan_technical_breakout(tickers)
    elif "undervalued" in screener_type.lower() or "deep" in screener_type.lower():
        data = scan_deep_undervalued(tickers)
    elif "konglo" in screener_type.lower():
        data = scan_konglo_momentum(tickers)
    elif "oversold" in screener_type.lower():
        data = scan_oversold_bounce(tickers)
    else:
        data = scan_candlestick_patterns(tickers)
        
    try:
        with open(cache_file, 'w') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        logger.error(f"Failed writing screener cache: {e}")
        
    return data
