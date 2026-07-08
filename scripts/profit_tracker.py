#!/usr/bin/env python3
"""
Simple profit tracker - evaluate ML predictions on profit metrics.
Focus on Sharpe, drawdown, profit factor rather than directional accuracy.
"""
import pandas as pd
import numpy as np
from datetime import date, timedelta
import matplotlib.pyplot as plt

def simulate_trading(predictions, actual_returns, threshold=0.002, commission=0.001):
    """
    Simulate trading based on predictions.
    
    Parameters
    ----------
    predictions : array-like
        Model predictions (continuous)
    actual_returns : array-like
        Actual market returns (1d returns)
    threshold : float
        Minimum prediction to trigger trade (default 0.2%)
    commission : float
        Commission per trade (default 0.1%)
    
    Returns
    -------
    dict
        Dictionary of profit metrics
    """
    # Trade signals
    signals = predictions > threshold
    
    # Strategy returns (with commission)
    strategy_returns = np.where(signals, actual_returns - commission, 0)
    
    total_trades = signals.sum()
    if total_trades == 0:
        return {}
    
    # Trade-specific returns
    trade_returns = strategy_returns[signals]
    
    # Basic metrics
    win_rate = (trade_returns > 0).sum() / total_trades
    avg_win = trade_returns[trade_returns > 0].mean() if (trade_returns > 0).any() else 0
    avg_loss = abs(trade_returns[trade_returns < 0].mean()) if (trade_returns < 0).any() else 0
    
    # Profit factor
    gross_profit = trade_returns[trade_returns > 0].sum()
    gross_loss = abs(trade_returns[trade_returns < 0].sum())
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
    
    # Cumulative returns
    cumulative_strategy = (1 + strategy_returns).prod() - 1
    cumulative_bh = (1 + actual_returns).prod() - 1
    
    # Sharpe ratio (annualized)
    daily_mean = strategy_returns.mean()
    daily_std = strategy_returns.std()
    sharpe = daily_mean / daily_std * np.sqrt(252) if daily_std > 0 else 0
    
    # Maximum drawdown
    cumulative = (1 + strategy_returns).cumprod()
    running_max = np.maximum.accumulate(cumulative)
    drawdown = (cumulative - running_max) / running_max
    max_drawdown = drawdown.min()
    
    # Calmar ratio (return / max drawdown)
    calmar = -sharpe / max_drawdown if max_drawdown < 0 else 0
    
    # Sortino ratio (only downside deviation)
    downside_returns = strategy_returns[strategy_returns < 0]
    downside_std = downside_returns.std() if len(downside_returns) > 0 else 0
    sortino = daily_mean / downside_std * np.sqrt(252) if downside_std > 0 else 0
    
    return {
        "total_trades": int(total_trades),
        "win_rate": win_rate,
        "avg_win_pct": avg_win * 100,
        "avg_loss_pct": avg_loss * 100,
        "profit_factor": profit_factor,
        "cumulative_strategy_pct": cumulative_strategy * 100,
        "cumulative_bh_pct": cumulative_bh * 100,
        "vs_bh_pct": (cumulative_strategy - cumulative_bh) * 100,
        "sharpe": sharpe,
        "sortino": sortino,
        "calmar": calmar,
        "max_drawdown_pct": max_drawdown * 100,
    }


def analyze_threshold_sensitivity(predictions, actual_returns, thresholds=None):
    """
    Analyze how profit metrics change with different trading thresholds.
    
    Parameters
    ----------
    predictions : array-like
        Model predictions
    actual_returns : array-like
        Actual returns
    thresholds : list
        List of threshold values to test
    
    Returns
    -------
    pd.DataFrame
        Metrics for each threshold
    """
    if thresholds is None:
        thresholds = [0.001, 0.0015, 0.002, 0.0025, 0.003]
    
    results = []
    for thresh in thresholds:
        metrics = simulate_trading(predictions, actual_returns, threshold=thresh)
        if metrics:
            metrics["threshold_pct"] = thresh * 100
            results.append(metrics)
    
    return pd.DataFrame(results)


def print_metrics_table(metrics):
    """
    Print metrics in a nice formatted table.
    """
    print("\n" + "=" * 80)
    print("PROFIT METRICS SUMMARY")
    print("=" * 80)
    
    print(f"{'Metric':<25} {'Value':>15}")
    print("-" * 40)
    
    fmt_map = {
        "total_trades": lambda x: f"{x:>15.0f}",
        "win_rate": lambda x: f"{x*100:>14.1f}%",
        "avg_win_pct": lambda x: f"{x:>14.3f}%",
        "avg_loss_pct": lambda x: f"{x:>14.3f}%",
        "profit_factor": lambda x: f"{x:>14.2f}" if x < 100 else "∞".rjust(15),
        "cumulative_strategy_pct": lambda x: f"{x:>14.2f}%",
        "cumulative_bh_pct": lambda x: f"{x:>14.2f}%",
        "vs_bh_pct": lambda x: f"{x:>+14.2f}%",
        "sharpe": lambda x: f"{x:>14.2f}",
        "sortino": lambda x: f"{x:>14.2f}",
        "calmar": lambda x: f"{x:>14.2f}",
        "max_drawdown_pct": lambda x: f"{x:>14.2f}%",
    }
    
    for key, value in metrics.items():
        if key in fmt_map:
            print(f"{key.replace('_', ' ').title():<25}{fmt_map[key](value)}")
    
    print("=" * 80)


if __name__ == "__main__":
    # Example usage
    print("Profit Tracker - ML Model Evaluation")
    print("Focus on Sharpe, profit factor, drawdown instead of directional accuracy.")
    print()
    print("Expected metrics for IDX daily with 51% DirAcc:")
    print("- Win rate: 51%")
    print("- Sharpe: 0.1-0.3")
    print("- Profit factor: 1.05-1.15")
    print("- vs B&H: ±0-2%")
    print()
    print("To use: Import simulate_trading() with your predictions and actual returns.")