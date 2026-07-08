#!/usr/bin/env python3
"""
Evaluate ML models using profit-based metrics instead of directional accuracy.
Focuses on Sharpe ratio, drawdown, profit factor, and practical trading outcomes.
"""
import os
import sys
import argparse
import pandas as pd
import numpy as np
import joblib
from pathlib import Path
from datetime import date, timedelta
import logging

sys.path.insert(0, str(Path(__file__).parent.parent))

from db import SessionLocal
from db.models import OhlcvPrice
from data.ml_features import prepare_training_data, FEATURE_COLUMNS

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)


def calculate_profit_metrics(strategy_returns: np.ndarray, 
                            actual_returns: np.ndarray,
                            signals: np.ndarray) -> dict:
    """
    Calculate comprehensive profit-based metrics.
    
    Parameters
    ----------
    strategy_returns : np.ndarray
        Returns achieved by the strategy (0 on no-trade days)
    actual_returns : np.ndarray
        Raw market returns for the period
    signals : np.ndarray
        Boolean array of trade signals (True = trade)
    
    Returns
    -------
    dict
        Dictionary of profit metrics
    """
    if len(strategy_returns) == 0:
        return {}
    
    # Basic metrics
    total_trades = int(signals.sum())
    if total_trades == 0:
        return {}
    
    # Trade-specific returns (only on trade days)
    trade_returns = strategy_returns[signals]
    
    # Win rate (trade level)
    win_rate = (trade_returns > 0).sum() / total_trades if total_trades > 0 else 0
    
    # Average win/loss
    avg_win = trade_returns[trade_returns > 0].mean() if (trade_returns > 0).any() else 0
    avg_loss = abs(trade_returns[trade_returns < 0].mean()) if (trade_returns < 0).any() else 0
    
    # Profit factor (gross profit / gross loss)
    gross_profit = trade_returns[trade_returns > 0].sum()
    gross_loss = abs(trade_returns[trade_returns < 0].sum())
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
    
    # Cumulative returns
    cumulative_strategy = (1 + strategy_returns).prod() - 1
    cumulative_bh = (1 + actual_returns).prod() - 1  # Buy & Hold
    
    # Sharpe ratio (annualized)
    daily_mean = strategy_returns.mean()
    daily_std = strategy_returns.std()
    sharpe = daily_mean / daily_std * np.sqrt(252) if daily_std > 0 else 0
    
    # Maximum drawdown
    cumulative = (1 + strategy_returns).cumprod()
    running_max = np.maximum.accumulate(cumulative)
    drawdown = (cumulative - running_max) / running_max
    max_drawdown = drawdown.min()
    
    # Win streak / loss streak
    wins = trade_returns > 0
    max_win_streak = 0
    max_loss_streak = 0
    
    if wins.size > 0:
        # Simple streak calculation without itertools.groupby
        current_streak = 0
        for w in wins:
            if w:
                current_streak += 1
                max_win_streak = max(max_win_streak, current_streak)
            else:
                current_streak = 0
        
        current_streak = 0
        for w in (~wins):
            if w:
                current_streak += 1
                max_loss_streak = max(max_loss_streak, current_streak)
            else:
                current_streak = 0
    
    # Calmar ratio (annual return / max drawdown)
    calmar = -sharpe / max_drawdown if max_drawdown < 0 else 0
    
    # Return dictionary
    return {
        "total_trades": total_trades,
        "win_rate": win_rate,
        "avg_win_pct": avg_win * 100,
        "avg_loss_pct": avg_loss * 100,
        "profit_factor": profit_factor,
        "sharpe": sharpe,
        "calmar": calmar,
        "max_drawdown_pct": max_drawdown * 100,
        "cumulative_strategy_pct": cumulative_strategy * 100,
        "cumulative_bh_pct": cumulative_bh * 100,
        "vs_buy_hold_pct": (cumulative_strategy - cumulative_bh) * 100,
        "max_win_streak": max_win_streak,
        "max_loss_streak": max_loss_streak,
    }


def evaluate_ticker(ticker: str, 
                    model_path: Path,
                    test_start: pd.Timestamp,
                    commission: float = 0.001,  # 0.1% commission
                    threshold: float = 0.002,   # 0.2% predicted return threshold
                    ) -> dict:
    """
    Run profit-based evaluation for a single ticker.
    
    Parameters
    ----------
    ticker : str
        Stock ticker symbol
    model_path : Path
        Path to trained model (.pkl)
    test_start : pd.Timestamp
        Start date for test period
    commission : float
        Commission per trade (fraction)
    threshold : float
        Minimum predicted return to trigger trade
    
    Returns
    -------
    dict
        Evaluation results
    """
    db = SessionLocal()
    try:
        # Fetch OHLCV data (need extra history for feature calculation)
        rows = db.query(OhlcvPrice).filter(
            OhlcvPrice.ticker == ticker,
            OhlcvPrice.trade_date >= (date.today() - timedelta(days=2*365))
        ).order_by(OhlcvPrice.trade_date).all()
        
        if len(rows) < 250:
            logger.warning(f"{ticker}: insufficient data ({len(rows)} rows)")
            return {}
        
        # Prepare dataframe
        ohlcv = pd.DataFrame([{
            "Open": float(r.open or 0), "High": float(r.high or 0),
            "Low": float(r.low or 0), "Close": float(r.close or 0),
            "Volume": int(r.volume or 0)
        } for r in rows], index=pd.to_datetime([r.trade_date for r in rows]))
        
        # Prepare features
        X, y = prepare_training_data(ohlcv, ticker=ticker)
        
        # Test period only
        X_test = X[X.index >= test_start]
        y_test = y.loc[X_test.index]
        
        if len(X_test) < 50:
            logger.warning(f"{ticker}: test period too short ({len(X_test)} days)")
            return {}
        
        # Load model
        try:
            model = joblib.load(model_path)
        except Exception as e:
            logger.error(f"{ticker}: failed to load model {model_path}: {e}")
            return {}
        
        # Align features and predict
        X_aligned = X_test.reindex(columns=FEATURE_COLUMNS, fill_value=0.0).fillna(0.0)
        preds = model.predict(X_aligned)
        
        # Actual returns
        actual_returns = y_test["target_1d"].values
        
        # Trade signals
        signals = preds > threshold
        
        # Strategy returns (with commission)
        strategy_returns = np.where(signals, actual_returns - commission, 0)
        
        # Calculate metrics
        metrics = calculate_profit_metrics(strategy_returns, actual_returns, signals)
        
        if not metrics:
            return {}
        
        metrics["ticker"] = ticker
        metrics["test_days"] = len(X_test)
        metrics["threshold_pct"] = threshold * 100
        metrics["commission_pct"] = commission * 100
        
        return metrics
        
    except Exception as e:
        logger.error(f"{ticker}: evaluation error: {e}")
        return {}
    finally:
        db.close()


def evaluate_all(models_dir: str = "models/checkpoints",
                 period: str = "1y",
                 threshold: float = 0.002,
                 commission: float = 0.001) -> None:
    """
    Evaluate all models using profit-based metrics.
    
    Parameters
    ----------
    models_dir : str
        Directory containing model files
    period : str
        Test period ("1y", "6m", "3m")
    threshold : float
        Trade threshold
    commission : float
        Commission per trade
    """
    from itertools import groupby
    
    # Determine test start date
    today = date.today()
    if period == "1y":
        test_start = pd.Timestamp(today - timedelta(days=365))
    elif period == "6m":
        test_start = pd.Timestamp(today - timedelta(days=183))
    elif period == "3m":
        test_start = pd.Timestamp(today - timedelta(days=91))
    else:
        raise ValueError(f"Invalid period: {period}")
    
    model_dir = Path(models_dir)
    
    # Find models - ONLY use new format (post-prune)
    models = {}
    for fmt in ["lgbm_*_1d.pkl", "lgbm_*.pkl"]:
        for f in model_dir.glob(fmt):
            name = f.stem.replace("lgbm_", "").replace("_1d", "").upper()
            # Skip tickers that contain '_' (old format leftovers)
            if "_" not in name and len(name) >= 3:
                # Load and check feature count
                try:
                    model = joblib.load(f)
                    if hasattr(model, 'n_features_'):
                        if model.n_features_ == 66:  # Feature set baru setelah pruning
                            models[name] = f
                            continue
                        elif model.n_features_ == 43:
                            # Skip old models
                            logger.warning(f"Skipping {name}: old model (43 features)")
                            continue
                except:
                    models[name] = f  # Fallback if can't check
    
    logger.info(f"Evaluating {len(models)} models on {period} period (since {test_start.date()})")
    logger.info(f"Threshold: {threshold*100:.2f}%, Commission: {commission*100:.2f}%")
    
    # Evaluate each ticker
    results = []
    for ticker, model_path in models.items():
        logger.info(f"Evaluating {ticker}...")
        metrics = evaluate_ticker(ticker, model_path, test_start, commission, threshold)
        if metrics:
            results.append(metrics)
            logger.info(f"  {ticker}: Trades={metrics['total_trades']} Win={metrics['win_rate']*100:.1f}% Sharpe={metrics['sharpe']:.2f}")
    
    if not results:
        logger.warning("No valid evaluation results")
        return
    
    # Summary statistics
    df = pd.DataFrame(results)
    
    print("\n" + "=" * 120)
    print("PROFIT-BASED EVALUATION SUMMARY")
    print("=" * 120)
    print(f"Period: {period} (since {test_start.date()})")
    print(f"Models evaluated: {len(df)}/{len(models)}")
    print(f"Trade threshold: {threshold*100:.2f}%, Commission: {commission*100:.2f}%")
    print("-" * 120)
    
    # Display detailed results
    print("\nDETAILED RESULTS (sorted by Sharpe):")
    print("-" * 120)
    display_cols = ["ticker", "total_trades", "win_rate", "sharpe", "profit_factor", 
                    "max_drawdown_pct", "cumulative_strategy_pct", "cumulative_bh_pct", "vs_buy_hold_pct"]
    df_display = df[display_cols].copy()
    df_display["win_rate"] = (df_display["win_rate"] * 100).round(1)
    df_display = df_display.sort_values("sharpe", ascending=False)
    
    print(df_display.to_string(index=False))
    
    # Summary statistics
    print("\n" + "=" * 120)
    print("AGGREGATE STATISTICS:")
    print("-" * 120)
    
    print(f"Average Sharpe: {df['sharpe'].mean():.2f} ± {df['sharpe'].std():.2f}")
    print(f"Median Sharpe:  {df['sharpe'].median():.2f}")
    print(f"Sharpe > 0:     {(df['sharpe'] > 0).sum()}/{len(df)} ({(df['sharpe'] > 0).mean()*100:.1f}%)")
    print(f"Sharpe > 1:     {(df['sharpe'] > 1).sum()}/{len(df)}")
    print()
    print(f"Average Win Rate: {df['win_rate'].mean()*100:.1f}%")
    print(f"Average Profit Factor: {df['profit_factor'].mean():.2f}")
    print(f"Average Max Drawdown: {df['max_drawdown_pct'].mean():.1f}%")
    print()
    print(f"Strategy Return (avg): {df['cumulative_strategy_pct'].mean():.1f}%")
    print(f"Buy & Hold Return (avg): {df['cumulative_bh_pct'].mean():.1f}%")
    print(f"Outperformance (avg): {df['vs_buy_hold_pct'].mean():+.1f}%")
    
    # Save to CSV
    output_path = model_dir / f"profit_evaluation_{period}.csv"
    df.to_csv(output_path, index=False)
    print(f"\nResults saved to: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Profit-based model evaluation")
    parser.add_argument("--period", default="1y", choices=["1y", "6m", "3m"],
                       help="Test period (default: 1y)")
    parser.add_argument("--threshold", type=float, default=0.002,
                       help="Minimum predicted return to trigger trade (default: 0.002 = 0.2%%)")
    parser.add_argument("--commission", type=float, default=0.001,
                       help="Commission per trade (default: 0.001 = 0.1%%)")
    parser.add_argument("--models-dir", default="models/checkpoints",
                       help="Directory containing model files (default: models/checkpoints)")
    
    args = parser.parse_args()
    
    evaluate_all(
        models_dir=args.models_dir,
        period=args.period,
        threshold=args.threshold,
        commission=args.commission
    )


if __name__ == "__main__":
    main()