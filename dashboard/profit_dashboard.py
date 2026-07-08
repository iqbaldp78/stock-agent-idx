#!/usr/bin/env python3
"""
Profit Tracking Dashboard for Stock-Agent-IDX
Track Sharpe ratio, drawdown, profit factor, and other relevant metrics.
"""
import os
import sys
import pandas as pd
import numpy as np
from datetime import date, timedelta, datetime
from pathlib import Path
import json
from typing import Dict, List, Optional, Tuple
import logging

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from db import SessionLocal
from db.models import OhlcvPrice
from data.ml_features import prepare_training_data

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


class ProfitTracker:
    """Track profit-based metrics for ML trading strategy."""
    
    def __init__(self, commission: float = 0.001, threshold: float = 0.002):
        """
        Initialize profit tracker.
        
        Parameters
        ----------
        commission : float
            Commission per trade (default: 0.1%)
        threshold : float
            Minimum predicted return to trigger trade (default: 0.2%)
        """
        self.commission = commission
        self.threshold = threshold
        self.metrics_history = []
        self.db = SessionLocal()
        
    def calculate_trade_metrics(self, strategy_returns: np.ndarray, 
                               actual_returns: np.ndarray,
                               signals: np.ndarray) -> Dict:
        """
        Calculate comprehensive profit metrics from trade data.
        
        Parameters
        ----------
        strategy_returns : np.ndarray
            Daily strategy returns (0 on non-trade days)
        actual_returns : np.ndarray
            Daily market returns
        signals : np.ndarray
            Boolean array of trade signals
        
        Returns
        -------
        dict
            Dictionary of profit metrics
        """
        if len(strategy_returns) == 0:
            return {}
        
        total_trades = int(signals.sum())
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
        
        # Sortino ratio (downside deviation only)
        downside_returns = strategy_returns[strategy_returns < 0]
        downside_std = downside_returns.std() if len(downside_returns) > 0 else 0
        sortino = daily_mean / downside_std * np.sqrt(252) if downside_std > 0 else 0
        
        # Calmar ratio
        calmar = -sharpe / max_drawdown if max_drawdown < 0 else 0
        
        # Win streak / loss streak
        wins = trade_returns > 0
        max_win_streak = 0
        max_loss_streak = 0
        
        if wins.size > 0:
            # Win streak
            current = 0
            for w in wins:
                if w:
                    current += 1
                    max_win_streak = max(max_win_streak, current)
                else:
                    current = 0
            
            # Loss streak
            current = 0
            for w in (~wins):
                if w:
                    current += 1
                    max_loss_streak = max(max_loss_streak, current)
                else:
                    current = 0
        
        return {
            "total_trades": total_trades,
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
            "max_win_streak": max_win_streak,
            "max_loss_streak": max_loss_streak,
        }
    
    def evaluate_ticker(self, ticker: str, model_path: Path, 
                       test_days: int = 365) -> Optional[Dict]:
        """
        Evaluate a single ticker's model on test period.
        
        Parameters
        ----------
        ticker : str
            Stock ticker symbol
        model_path : Path
            Path to trained model
        test_days : int
            Number of days for test period (default: 365)
        
        Returns
        -------
        dict or None
            Evaluation results, or None if failed
        """
        try:
            import joblib
            
            # Fetch data
            cutoff = date.today() - timedelta(days=test_days + 365)  # Extra for feature calculation
            rows = self.db.query(OhlcvPrice).filter(
                OhlcvPrice.ticker == ticker,
                OhlcvPrice.trade_date >= cutoff
            ).order_by(OhlcvPrice.trade_date).all()
            
            if len(rows) < 250:
                logger.warning(f"{ticker}: insufficient data")
                return None
            
            # Prepare dataframe
            ohlcv = pd.DataFrame([{
                "Open": float(r.open or 0), "High": float(r.high or 0),
                "Low": float(r.low or 0), "Close": float(r.close or 0),
                "Volume": int(r.volume or 0)
            } for r in rows], index=pd.to_datetime([r.trade_date for r in rows]))
            
            # Prepare features
            X, y = prepare_training_data(ohlcv, ticker=ticker)
            
            # Test period
            test_start = pd.Timestamp(date.today() - timedelta(days=test_days))
            X_test = X[X.index >= test_start]
            y_test = y.loc[X_test.index]
            
            if len(X_test) < 50:
                logger.warning(f"{ticker}: test period too short")
                return None
            
            # Load model and predict
            model = joblib.load(model_path)
            X_aligned = X_test.reindex(columns=X.columns, fill_value=0.0).fillna(0.0)
            preds = model.predict(X_aligned)
            
            actual_returns = y_test["target_1d"].values
            
            # Trade signals
            signals = preds > self.threshold
            strategy_returns = np.where(signals, actual_returns - self.commission, 0)
            
            # Calculate metrics
            metrics = self.calculate_trade_metrics(strategy_returns, actual_returns, signals)
            
            if not metrics:
                return None
            
            metrics["ticker"] = ticker
            metrics["test_days"] = len(X_test)
            metrics["evaluation_date"] = date.today().isoformat()
            
            return metrics
            
        except Exception as e:
            logger.error(f"{ticker}: evaluation error - {e}")
            return None
    
    def run_daily_evaluation(self, models_dir: str = "models/checkpoints",
                           tickers: Optional[List[str]] = None) -> pd.DataFrame:
        """
        Run daily profit evaluation for all models.
        
        Parameters
        ----------
        models_dir : str
            Directory containing model files
        tickers : list, optional
            List of tickers to evaluate (if None, evaluate all)
        
        Returns
        -------
        pd.DataFrame
            DataFrame of evaluation results
        """
        model_dir = Path(models_dir)
        
        # Find models (try new format first)
        models = {}
        for fmt in ["lgbm_*_1d.pkl", "lgbm_*.pkl"]:
            for f in model_dir.glob(fmt):
                name = f.stem.replace("lgbm_", "").replace("_1d", "").upper()
                if "_" not in name and len(name) >= 3:
                    models[name] = f
        
        if tickers:
            models = {k: v for k, v in models.items() if k in tickers}
        
        logger.info(f"Evaluating {len(models)} models")
        
        results = []
        for ticker, model_path in models.items():
            logger.info(f"Evaluating {ticker}...")
            metrics = self.evaluate_ticker(ticker, model_path)
            if metrics:
                results.append(metrics)
                logger.info(f"  {ticker}: Trades={metrics['total_trades']} Win={metrics['win_rate']*100:.1f}% Sharpe={metrics['sharpe']:.2f}")
        
        if not results:
            logger.warning("No valid evaluation results")
            return pd.DataFrame()
        
        df = pd.DataFrame(results)
        
        # Save to CSV
        output_dir = Path("dashboard/output")
        output_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = output_dir / f"profit_evaluation_{timestamp}.csv"
        df.to_csv(output_path, index=False)
        
        # Save summary
        summary_path = output_dir / "latest_summary.json"
        summary = {
            "evaluation_date": date.today().isoformat(),
            "total_tickers": len(df),
            "avg_sharpe": float(df["sharpe"].mean()),
            "avg_win_rate": float(df["win_rate"].mean()),
            "avg_profit_factor": float(df["profit_factor"].mean()),
            "avg_vs_bh": float(df["vs_bh_pct"].mean()),
            "sharpe_positive": int((df["sharpe"] > 0).sum()),
            "sharpe_negative": int((df["sharpe"] <= 0).sum()),
            "best_ticker": df.loc[df["sharpe"].idxmax(), "ticker"] if not df.empty else None,
            "worst_ticker": df.loc[df["sharpe"].idxmin(), "ticker"] if not df.empty else None,
        }
        
        with open(summary_path, "w") as f:
            json.dump(summary, f, indent=2)
        
        logger.info(f"Results saved to {output_path}")
        logger.info(f"Summary saved to {summary_path}")
        
        return df
    
    def print_summary_report(self, df: pd.DataFrame):
        """Print a formatted summary report."""
        if df.empty:
            print("No evaluation results available.")
            return
        
        print("\n" + "=" * 100)
        print("PROFIT TRACKING DASHBOARD - SUMMARY REPORT")
        print("=" * 100)
        print(f"Evaluation Date: {date.today().isoformat()}")
        print(f"Models Evaluated: {len(df)} tickers")
        print(f"Trade Threshold: {self.threshold*100:.2f}%")
        print(f"Commission: {self.commission*100:.2f}%")
        print("-" * 100)
        
        # Top performers by Sharpe
        top_sharpe = df.nlargest(5, "sharpe")[["ticker", "sharpe", "win_rate", "profit_factor", "cumulative_strategy_pct"]]
        print("\nTOP 5 PERFORMERS (by Sharpe ratio):")
        print("-" * 60)
        print(f"{'Ticker':<8} {'Sharpe':>8} {'Win%':>6} {'Profit Factor':>13} {'Return%':>9}")
        print("-" * 60)
        for _, row in top_sharpe.iterrows():
            print(f"{row['ticker']:<8} {row['sharpe']:>8.2f} {row['win_rate']*100:>5.1f}% {row['profit_factor']:>12.2f} {row['cumulative_strategy_pct']:>8.2f}%")
        
        # Summary statistics
        print("\n" + "=" * 100)
        print("AGGREGATE STATISTICS:")
        print("-" * 100)
        
        stats = {
            "Average Sharpe": f"{df['sharpe'].mean():.3f}",
            "Median Sharpe": f"{df['sharpe'].median():.3f}",
            "Sharpe > 0": f"{(df['sharpe'] > 0).sum()}/{len(df)} ({(df['sharpe'] > 0).mean()*100:.1f}%)",
            "Sharpe > 0.5": f"{(df['sharpe'] > 0.5).sum()}/{len(df)}",
            "Average Win Rate": f"{df['win_rate'].mean()*100:.1f}%",
            "Average Profit Factor": f"{df['profit_factor'].mean():.2f}",
            "Average Strategy Return": f"{df['cumulative_strategy_pct'].mean():.2f}%",
            "Average Buy & Hold Return": f"{df['cumulative_bh_pct'].mean():.2f}%",
            "Average Outperformance": f"{df['vs_bh_pct'].mean():+.2f}%",
            "Average Max Drawdown": f"{df['max_drawdown_pct'].mean():.2f}%",
        }
        
        for key, value in stats.items():
            print(f"{key:<30} {value:>20}")
        
        # Risk assessment
        print("\n" + "=" * 100)
        print("RISK ASSESSMENT:")
        print("-" * 100)
        
        # Sharpe distribution
        sharpe_q25 = df["sharpe"].quantile(0.25)
        sharpe_q75 = df["sharpe"].quantile(0.75)
        
        # Drawdown analysis
        high_drawdown = (df["max_drawdown_pct"] < -5).sum()
        
        print(f"Sharpe distribution: Q1={sharpe_q25:.2f}, Median={df['sharpe'].median():.2f}, Q3={sharpe_q75:.2f}")
        print(f"Tickers with >5% drawdown: {high_drawdown}/{len(df)}")
        print(f"Consistency (win rate > 50%): {(df['win_rate'] > 0.5).sum()}/{len(df)}")
        
        print("\n" + "=" * 100)
        print("RECOMMENDATIONS:")
        print("-" * 100)
        
        # Generate recommendations based on metrics
        avg_sharpe = df["sharpe"].mean()
        avg_win_rate = df["win_rate"].mean()
        avg_profit_factor = df["profit_factor"].mean()
        
        recommendations = []
        
        if avg_sharpe < 0.2:
            recommendations.append("Consider increasing trade threshold to reduce noise")
        
        if avg_win_rate < 0.5:
            recommendations.append("Model may not be beating random selection")
        
        if avg_profit_factor < 1.1:
            recommendations.append("Profit margin is thin; consider tighter stop-loss")
        
        if len(df) < 20:
            recommendations.append("Consider evaluating more tickers for better diversification")
        
        if recommendations:
            for i, rec in enumerate(recommendations, 1):
                print(f"{i}. {rec}")
        else:
            print("Metrics look good! Current strategy appears effective.")
        
        print("=" * 100)
    
    def close(self):
        """Close database connection."""
        if self.db:
            self.db.close()


def main():
    """Main function to run profit dashboard."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Profit Tracking Dashboard")
    parser.add_argument("--tickers", nargs="+", help="Specific tickers to evaluate")
    parser.add_argument("--threshold", type=float, default=0.002,
                       help="Trade threshold (default: 0.002 = 0.2%%)")
    parser.add_argument("--commission", type=float, default=0.001,
                       help="Commission per trade (default: 0.001 = 0.1%%)")
    parser.add_argument("--test-days", type=int, default=365,
                       help="Test period in days (default: 365)")
    parser.add_argument("--models-dir", default="models/checkpoints",
                       help="Directory containing model files")
    
    args = parser.parse_args()
    
    tracker = ProfitTracker(commission=args.commission, threshold=args.threshold)
    
    try:
        df = tracker.run_daily_evaluation(
            models_dir=args.models_dir,
            tickers=args.tickers
        )
        
        if not df.empty:
            tracker.print_summary_report(df)
        else:
            print("No valid evaluation results obtained.")
            
    finally:
        tracker.close()


if __name__ == "__main__":
    main()