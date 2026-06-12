"""
Historical Signal Backtest
Simulasi rule-based signal dari OHLCV historis tanpa LLM.

Strategy default:
- BUY jika trend bullish sederhana: Close > MA20 > MA50, RSI sehat, volume tidak ekstrem
- Entry: close hari sinyal
- Exit: cek T+1..T+5 apakah menyentuh TP1/TP2/TP3 atau SL

Usage:
    python scripts/backtest_signals.py --tickers BBCA BMRI
    python scripts/backtest_signals.py --all
    python scripts/backtest_signals.py --tickers BBCA --start 2024-01-01 --end 2024-12-31
"""
import argparse
import json
import logging
import os
import sys
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def normalize_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize OHLCV columns and index."""
    if df is None or df.empty:
        return pd.DataFrame()
    out = df.copy()
    out.columns = [str(c).title() for c in out.columns]
    required = ["Open", "High", "Low", "Close", "Volume"]
    for col in required:
        if col not in out.columns:
            return pd.DataFrame()
        out[col] = pd.to_numeric(out[col], errors="coerce")
    out = out.dropna(subset=["Open", "High", "Low", "Close"])
    out = out.sort_index()
    return out


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Add simple technical indicators for backtest signal generation."""
    out = df.copy()
    close = out["Close"]

    out["ma20"] = close.rolling(20).mean()
    out["ma50"] = close.rolling(50).mean()
    out["ret_5d"] = close.pct_change(5)
    out["vol_ma20"] = out["Volume"].rolling(20).mean()
    out["volume_ratio"] = out["Volume"] / out["vol_ma20"]

    delta = close.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan)
    out["rsi"] = 100 - (100 / (1 + rs))
    out["rsi"] = out["rsi"].fillna(50)

    return out.dropna()


def generate_signal(row: pd.Series) -> str:
    """
    Rule-based BUY signal.
    Conservative supaya backtest tidak overtrade.
    """
    close = row["Close"]
    bullish_trend = close > row["ma20"] > row["ma50"]
    healthy_rsi = 45 <= row["rsi"] <= 72
    momentum_ok = row["ret_5d"] > -0.03
    volume_ok = 0.7 <= row.get("volume_ratio", 1.0) <= 3.0

    if bullish_trend and healthy_rsi and momentum_ok and volume_ok:
        return "BUY"
    return "HOLD"


def simulate_trade(
    df: pd.DataFrame,
    entry_idx: int,
    holding_days: int = 5,
    tp1_pct: float = 0.03,
    tp2_pct: float = 0.05,
    tp3_pct: float = 0.08,
    sl_pct: float = -0.03,
) -> dict:
    """Simulate exit after signal using next N candles."""
    entry_row = df.iloc[entry_idx]
    entry_price = float(entry_row["Close"])
    entry_date = str(df.index[entry_idx].date() if hasattr(df.index[entry_idx], "date") else df.index[entry_idx])

    tp1 = entry_price * (1 + tp1_pct)
    tp2 = entry_price * (1 + tp2_pct)
    tp3 = entry_price * (1 + tp3_pct)
    sl = entry_price * (1 + sl_pct)

    max_i = min(entry_idx + holding_days, len(df) - 1)
    exit_price = float(df.iloc[max_i]["Close"])
    exit_date = str(df.index[max_i].date() if hasattr(df.index[max_i], "date") else df.index[max_i])
    result = "TIME_EXIT"

    for i in range(entry_idx + 1, max_i + 1):
        row = df.iloc[i]
        high = float(row["High"])
        low = float(row["Low"])
        date_str = str(df.index[i].date() if hasattr(df.index[i], "date") else df.index[i])

        # Conservative order: SL first if both SL and TP touched in same candle.
        if low <= sl:
            exit_price = sl
            exit_date = date_str
            result = "HIT_SL"
            break
        if high >= tp3:
            exit_price = tp3
            exit_date = date_str
            result = "HIT_TP3"
            break
        if high >= tp2:
            exit_price = tp2
            exit_date = date_str
            result = "HIT_TP2"
            break
        if high >= tp1:
            exit_price = tp1
            exit_date = date_str
            result = "HIT_TP1"
            break

    return_pct = (exit_price - entry_price) / entry_price * 100
    return {
        "entry_date": entry_date,
        "exit_date": exit_date,
        "entry_price": round(entry_price, 2),
        "exit_price": round(exit_price, 2),
        "result": result,
        "return_pct": round(return_pct, 2),
        "holding_days": max(1, max_i - entry_idx),
    }


def max_drawdown(returns_pct: list[float]) -> float:
    if not returns_pct:
        return 0.0
    equity = np.cumprod([1 + r / 100 for r in returns_pct])
    peak = np.maximum.accumulate(equity)
    dd = (equity - peak) / peak
    return float(dd.min() * 100)


def summarize_trades(trades: list[dict]) -> dict:
    if not trades:
        return {
            "trades": 0,
            "win_rate": 0.0,
            "avg_return_pct": 0.0,
            "profit_factor": 0.0,
            "max_drawdown_pct": 0.0,
        }

    returns = [float(t["return_pct"]) for t in trades]
    wins = [r for r in returns if r > 0]
    losses = [r for r in returns if r <= 0]
    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else gross_profit

    return {
        "trades": len(trades),
        "win_rate": round(len(wins) / len(trades) * 100, 2),
        "avg_return_pct": round(float(np.mean(returns)), 2),
        "median_return_pct": round(float(np.median(returns)), 2),
        "profit_factor": round(float(profit_factor), 2),
        "max_drawdown_pct": round(max_drawdown(returns), 2),
        "best_trade_pct": round(max(returns), 2),
        "worst_trade_pct": round(min(returns), 2),
    }


def get_universe_tickers() -> list[str]:
    try:
        from db import SessionLocal
        from db.models import Universe
        db = SessionLocal()
        rows = db.query(Universe.ticker).filter(Universe.active == True).all()
        db.close()
        tickers = [r.ticker for r in rows]
        if tickers:
            return tickers
    except Exception as e:
        logger.warning(f"Tidak bisa ambil universe dari DB: {e}")
    return ["BBCA", "BBRI", "BMRI", "TLKM", "ASII", "UNVR", "ICBP", "KLBF", "ANTM", "INDF"]


def fetch_ohlcv(ticker: str, period: str, start: str | None, end: str | None) -> pd.DataFrame:
    try:
        from data.fetcher_stockbit import get_ohlcv, get_ohlcv_range
        if start and end:
            return get_ohlcv_range(ticker, start, end)
        return get_ohlcv(ticker, period=period)
    except Exception as e:
        logger.warning(f"Stockbit OHLCV failed for {ticker}: {e}")

    try:
        import yfinance as yf
        if start and end:
            return yf.download(f"{ticker}.JK", start=start, end=end, auto_adjust=True, progress=False)
        return yf.download(f"{ticker}.JK", period=period, auto_adjust=True, progress=False)
    except Exception as e:
        logger.warning(f"yfinance fallback failed for {ticker}: {e}")
    return pd.DataFrame()


def backtest_ticker(
    ticker: str,
    period: str = "1y",
    start: str | None = None,
    end: str | None = None,
    holding_days: int = 5,
) -> dict:
    raw = fetch_ohlcv(ticker, period, start, end)
    df = normalize_ohlcv(raw)
    if df.empty or len(df) < 80:
        return {"ticker": ticker, "error": f"OHLCV tidak cukup ({len(df)} rows)"}

    df = add_indicators(df)
    trades = []

    # Leave room for holding_days at the end.
    for i in range(0, len(df) - holding_days - 1):
        row = df.iloc[i]
        signal = generate_signal(row)
        if signal != "BUY":
            continue

        trade = simulate_trade(df, i, holding_days=holding_days)
        trade["ticker"] = ticker
        trade["signal"] = signal
        trade["rsi"] = round(float(row["rsi"]), 2)
        trade["ma20"] = round(float(row["ma20"]), 2)
        trade["ma50"] = round(float(row["ma50"]), 2)
        trades.append(trade)

    return {
        "ticker": ticker,
        "rows": len(df),
        "summary": summarize_trades(trades),
        "trades": trades,
    }


def main():
    parser = argparse.ArgumentParser(description="Historical rule-based signal backtest")
    grp = parser.add_mutually_exclusive_group(required=True)
    grp.add_argument("--tickers", nargs="+", help="Ticker(s), e.g. BBCA BMRI")
    grp.add_argument("--all", action="store_true", help="Semua ticker di universe")
    parser.add_argument("--period", default="1y", help="Period OHLCV jika start/end tidak diisi (default: 1y)")
    parser.add_argument("--start", help="Start date YYYY-MM-DD")
    parser.add_argument("--end", help="End date YYYY-MM-DD")
    parser.add_argument("--holding-days", type=int, default=5, help="Max holding days (default: 5)")
    parser.add_argument("--output", default="backtest_result.json", help="Output JSON file")
    args = parser.parse_args()

    tickers = get_universe_tickers() if args.all else args.tickers
    logger.info(f"Backtesting {len(tickers)} ticker(s): {', '.join(tickers)}")

    results = {}
    all_trades = []
    summary_rows = []

    for ticker in tickers:
        logger.info(f"📊 {ticker} — loading OHLCV...")
        res = backtest_ticker(
            ticker,
            period=args.period,
            start=args.start,
            end=args.end,
            holding_days=args.holding_days,
        )
        results[ticker] = res

        if "error" in res:
            logger.warning(f"  ⚠️  {ticker}: {res['error']}")
            continue

        summary = res["summary"]
        summary_rows.append({"ticker": ticker, **summary})
        all_trades.extend(res["trades"])
        logger.info(
            f"  Trades={summary['trades']} WinRate={summary['win_rate']:.1f}% "
            f"AvgRet={summary['avg_return_pct']:+.2f}% PF={summary['profit_factor']:.2f}"
        )

    aggregate = summarize_trades(all_trades)

    print()
    print("=" * 84)
    print("  HISTORICAL SIGNAL BACKTEST SUMMARY")
    print("=" * 84)
    if summary_rows:
        print(f"{'Ticker':<8} {'Trades':>7} {'WinRate':>9} {'AvgRet':>9} {'PF':>7} {'MaxDD':>9} {'Best':>8} {'Worst':>8}")
        print("-" * 84)
        for r in sorted(summary_rows, key=lambda x: -x["avg_return_pct"]):
            print(
                f"{r['ticker']:<8} {r['trades']:>7} {r['win_rate']:>8.1f}% "
                f"{r['avg_return_pct']:>+8.2f}% {r['profit_factor']:>7.2f} "
                f"{r['max_drawdown_pct']:>+8.2f}% {r['best_trade_pct']:>+7.2f}% {r['worst_trade_pct']:>+7.2f}%"
            )
        print("-" * 84)
        print(
            f"{'ALL':<8} {aggregate['trades']:>7} {aggregate['win_rate']:>8.1f}% "
            f"{aggregate['avg_return_pct']:>+8.2f}% {aggregate['profit_factor']:>7.2f} "
            f"{aggregate['max_drawdown_pct']:>+8.2f}% {aggregate.get('best_trade_pct', 0):>+7.2f}% {aggregate.get('worst_trade_pct', 0):>+7.2f}%"
        )
    else:
        print("  Tidak ada trade yang ter-generate.")
    print("=" * 84)

    output = {
        "run_date": datetime.now().isoformat(),
        "config": {
            "period": args.period,
            "start": args.start,
            "end": args.end,
            "holding_days": args.holding_days,
            "strategy": "close_gt_ma20_gt_ma50_rsi45_72_ret5d_gt_minus3_vol07_3",
        },
        "aggregate": aggregate,
        "tickers": results,
    }
    with open(args.output, "w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"\n✅ Hasil disimpan ke: {args.output}")


if __name__ == "__main__":
    main()
