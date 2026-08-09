#!/usr/bin/env python3
"""
Backtest IHSG Predictor Strategy
Backtests the binary directional classification and ATR-calibrated targets
against historical IHSG OHLCV data over 1-5 years.
Usage: python scripts/backtest_ihsg_strategy.py --years 3
"""
import sys
import argparse
import pandas as pd
import numpy as np
import logging
from datetime import datetime

import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, "/app")

from data.fetcher_ihsg import get_ihsg_ohlcv
from agents.ihsg_predictor import _calculate_rsi, _calculate_macd, _calculate_atr

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


def run_ihsg_backtest(years: float = 3.0):
    logger.info("=" * 65)
    logger.info(f"📊 HISTORICAL BACKTEST: IHSG PREDICTOR STRATEGY ({years} Years)")
    logger.info("=" * 65)

    ohlcv = get_ihsg_ohlcv(period="8y")

    if ohlcv is None or ohlcv.empty or len(ohlcv) < 200:
        logger.error("❌ Not enough OHLCV data to perform backtest")
        return

    # Filter to requested backtest window
    cutoff_date = pd.Timestamp.now() - pd.Timedelta(days=int(years * 365))
    df = ohlcv.copy()
    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index)
    
    # Sort index ascending
    df = df.sort_index()

    # Pre-calculate indicator series over full history to avoid lookahead bias
    close = df['Close'].astype(float)
    high = df['High'].astype(float)
    low = df['Low'].astype(float)

    # Rolling indicators
    ma20 = close.rolling(20).mean()
    ma50 = close.rolling(50).mean()
    ma200 = close.rolling(200).mean()

    # RSI & MACD
    delta = close.diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss.replace(0, 1e-10)
    rsi_series = 100 - (100 / (1 + rs))

    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    macd_series = ema12 - ema26
    macd_sig_series = macd_series.ewm(span=9, adjust=False).mean()

    # ATR
    prev_close = close.shift(1)
    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr_series = tr.rolling(14).mean()

    start_idx = 200  # Warmup for MA200
    sub_df = df.iloc[start_idx:]
    sub_df = sub_df[sub_df.index >= cutoff_date]

    if sub_df.empty:
        logger.error(f"❌ No data found after cutoff date {cutoff_date.date()}")
        return

    results = []
    
    # Rolling simulation day by day
    for i in range(len(sub_df) - 1):
        idx_pos = df.index.get_loc(sub_df.index[i])
        current_date = df.index[idx_pos]
        
        c_price = close.iloc[idx_pos]
        next_price = close.iloc[idx_pos + 1]
        actual_return_d1 = (next_price - c_price) / c_price * 100

        # Multi-day actual returns
        actual_return_d3 = (close.iloc[min(idx_pos + 3, len(df)-1)] - c_price) / c_price * 100 if idx_pos + 3 < len(df) else None
        actual_return_d5 = (close.iloc[min(idx_pos + 5, len(df)-1)] - c_price) / c_price * 100 if idx_pos + 5 < len(df) else None
        actual_return_d7 = (close.iloc[min(idx_pos + 7, len(df)-1)] - c_price) / c_price * 100 if idx_pos + 7 < len(df) else None

        # 1. Momentum score component
        rsi_val = rsi_series.iloc[idx_pos]
        rsi_norm = max(0.0, min(1.0, (rsi_val - 30) / 40)) if not pd.isna(rsi_val) else 0.5
        
        macd_val = macd_series.iloc[idx_pos]
        sig_val = macd_sig_series.iloc[idx_pos]
        macd_score = 0.10 if macd_val > sig_val and macd_val > 0 else (0.05 if macd_val > sig_val else -0.05)

        m20 = ma20.iloc[idx_pos]
        m50 = ma50.iloc[idx_pos]
        m200 = ma200.iloc[idx_pos]
        above_mas = sum([c_price > m for m in [m20, m50, m200] if not pd.isna(m)])
        ma_score = (above_mas / 3 - 0.5) * 0.15

        mom_score = max(0.0, min(1.0, 0.5 + (rsi_norm - 0.5) * 0.25 + macd_score + ma_score))

        # 2. Trend & Macro score component
        ihsg_vs_ma20_pct = ((c_price - m20) / m20 * 100) if not pd.isna(m20) and m20 > 0 else 0.0
        macro_score = max(0.0, min(1.0, 0.5 + max(-0.15, min(0.15, (ihsg_vs_ma20_pct / 2.0) * 0.15))))

        # 3. Breadth score component (proxy from 20-day trend strength)
        ret_5d = (c_price - close.iloc[idx_pos - 5]) / close.iloc[idx_pos - 5] * 100 if idx_pos >= 5 else 0.0
        breadth_score = max(0.0, min(1.0, 0.5 + max(-0.25, min(0.25, ret_5d * 0.05))))

        # 4. Sector proxy score component
        sector_score = max(0.0, min(1.0, 0.5 + (ret_5d * 0.02)))

        # Dynamic regime weighting matching live predictor
        if abs(ihsg_vs_ma20_pct) > 2.0:
            regime = "TRENDING"
            weights = {"momentum": 0.30, "breadth": 0.25, "sectors": 0.15, "macro": 0.15, "news": 0.15}
        elif abs(ret_5d) > 3.0:
            regime = "VOLATILE"
            weights = {"macro": 0.35, "breadth": 0.25, "momentum": 0.15, "sectors": 0.10, "news": 0.15}
        else:
            regime = "CONSOLIDATION"
            weights = {"breadth": 0.35, "sectors": 0.20, "momentum": 0.15, "macro": 0.15, "news": 0.15}

        news_score = 0.50  # Historical neutral baseline for news sentiment
        combined_score = (
            mom_score * weights["momentum"] +
            breadth_score * weights["breadth"] +
            macro_score * weights["macro"] +
            sector_score * weights["sectors"] +
            news_score * weights["news"]
        )

        # Binary Direction Determination
        predicted_dir = "BULLISH" if combined_score >= 0.50 else "BEARISH"
        is_correct_d1 = (predicted_dir == "BULLISH" and actual_return_d1 >= 0) or \
                        (predicted_dir == "BEARISH" and actual_return_d1 < 0)

        # ATR-based target move prediction
        atr_val = atr_series.iloc[idx_pos]
        atr_pct = (atr_val / c_price * 100) if not pd.isna(atr_val) and c_price > 0 else 1.0
        pred_d1_pct = (combined_score - 0.50) * 2.0 * atr_pct
        mae_d1 = abs(pred_d1_pct - actual_return_d1)

        # Strategy return (Long if BULLISH, Short/Cash if BEARISH)
        strategy_return_long_only = actual_return_d1 if predicted_dir == "BULLISH" else 0.0
        strategy_return_long_short = actual_return_d1 if predicted_dir == "BULLISH" else -actual_return_d1

        results.append({
            "date": current_date,
            "close": c_price,
            "combined_score": combined_score,
            "predicted_dir": predicted_dir,
            "actual_return_d1": actual_return_d1,
            "is_correct_d1": is_correct_d1,
            "pred_d1_pct": pred_d1_pct,
            "mae_d1": mae_d1,
            "strat_long_only": strategy_return_long_only,
            "strat_long_short": strategy_return_long_short,
            "actual_return_d3": actual_return_d3,
            "actual_return_d5": actual_return_d5,
            "actual_return_d7": actual_return_d7,
        })

    res_df = pd.DataFrame(results)

    # Compute Aggregate Performance Metrics
    total_days = len(res_df)
    win_count = res_df["is_correct_d1"].sum()
    win_rate = (win_count / total_days * 100) if total_days > 0 else 0.0
    mae_avg = res_df["mae_d1"].mean()

    # Cumulative Returns
    cum_bench = (1 + res_df["actual_return_d1"] / 100).prod() - 1
    cum_strat_long = (1 + res_df["strat_long_only"] / 100).prod() - 1
    cum_strat_ls = (1 + res_df["strat_long_short"] / 100).prod() - 1

    # Multi-day direction accuracy (evaluating both BULLISH and BEARISH predictions)
    res_df["is_correct_d3"] = res_df.apply(
        lambda r: ((r["predicted_dir"] == "BULLISH" and r["actual_return_d3"] >= 0) or
                   (r["predicted_dir"] == "BEARISH" and r["actual_return_d3"] < 0))
        if r["actual_return_d3"] is not None else None, axis=1
    )
    res_df["is_correct_d5"] = res_df.apply(
        lambda r: ((r["predicted_dir"] == "BULLISH" and r["actual_return_d5"] >= 0) or
                   (r["predicted_dir"] == "BEARISH" and r["actual_return_d5"] < 0))
        if r["actual_return_d5"] is not None else None, axis=1
    )
    
    win_rate_d3 = res_df["is_correct_d3"].dropna().mean() * 100
    win_rate_d5 = res_df["is_correct_d5"].dropna().mean() * 100

    logger.info("-----------------------------------------------------------------")
    logger.info(f"Periode Evaluasi          : {sub_df.index[0].date()} s/d {sub_df.index[-1].date()} ({total_days} Trading Days)")
    logger.info(f"D+1 Direction Win Rate    : {win_count} / {total_days} ({win_rate:.2f}%)")
    logger.info(f"D+3 Horizon Win Rate      : {win_rate_d3:.2f}%")
    logger.info(f"D+5 Horizon Win Rate      : {win_rate_d5:.2f}%")
    logger.info(f"Mean Absolute Error (MAE) : {mae_avg:.2f}%")
    logger.info("-----------------------------------------------------------------")
    logger.info("📈 CUMULATIVE STRATEGY PERFORMANCE:")
    logger.info(f"Buy & Hold IHSG (Benchmark) : {cum_bench * 100:+.2f}%")
    logger.info(f"Strategy (Long-Only)        : {cum_strat_long * 100:+.2f}%")
    logger.info(f"Strategy (Long-Short)       : {cum_strat_ls * 100:+.2f}%")
    logger.info("=" * 65)

    return {
        "start_date": str(sub_df.index[0].date()),
        "end_date": str(sub_df.index[-1].date()),
        "total_days": total_days,
        "win_count": int(win_count),
        "win_rate": float(win_rate),
        "win_rate_d3": float(win_rate_d3),
        "win_rate_d5": float(win_rate_d5),
        "mae_avg": float(mae_avg),
        "cum_bench_pct": float(cum_bench * 100),
        "cum_strat_long_pct": float(cum_strat_long * 100),
        "cum_strat_ls_pct": float(cum_strat_ls * 100),
        "df": res_df
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Backtest IHSG Predictor Strategy")
    parser.add_argument("--years", type=float, default=3.0, help="Backtest period in years (default: 3.0)")
    args = parser.parse_args()
    
    run_ihsg_backtest(years=args.years)
