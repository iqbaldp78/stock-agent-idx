"""
Paper Trading Analytics — Backtest validation, performance attribution, reports.

Features:
1. Backtest signals vs actual returns (historical)
2. Performance attribution — factor analysis
3. Trade history reports (PDF/CSV export)
4. Closed positions analysis
"""

import logging
from datetime import datetime, timedelta, date
from typing import List, Dict, Optional, Tuple
import pandas as pd
import numpy as np
from decimal import Decimal
from sqlalchemy.orm import Session

from db import SessionLocal
from db.models import PaperTrade, PaperWallet, Signal
from services.paper_trading import PaperTradingService

logger = logging.getLogger(__name__)


class PaperAnalytics:
    def __init__(self, session: Optional[Session] = None):
        self.session = session or SessionLocal()
        self.trading_service = PaperTradingService(session=self.session)

    # ======================== BACKTEST VALIDATION ========================

    def backtest_signals_vs_actual(
        self, 
        lookback_days: int = 30,
        max_signals: int = 20
    ) -> Dict:
        """
        Backtest historical signals vs actual market returns.
        
        Args:
            lookback_days: Berapa hari ke belakang untuk analisis
            max_signals: Maksimal signals untuk di-proses
        
        Returns:
            Dict dengan hasil backtest:
            - hypothetical_portfolio: jika follow semua signals
            - actual_paper_trades: hasil paper trading aktual
            - comparison: hypothetical vs actual
        """
        end_date = datetime.utcnow().date()
        start_date = end_date - timedelta(days=lookback_days)
        
        # 1. Get historical signals dalam period ini
        signals = self.session.query(Signal).filter(
            Signal.run_date >= start_date,
            Signal.run_date <= end_date,
            Signal.rank.isnot(None)
        ).order_by(
            Signal.run_date.desc()
        ).limit(max_signals).all()
        
        if not signals:
            return {
                "status": "info",
                "message": f"No signals found in last {lookback_days} days",
                "hypothetical": {},
                "actual": {},
                "comparison": {}
            }
        
        # 2. Calculate hypothetical returns jika follow signals
        hypothetical_results = []
        for signal in signals:
            ticker = signal.ticker
            signal_date = signal.run_date
            entry_price = signal.entry_low or 0
            tp1 = signal.target_1
            stop_loss = signal.stop_loss
            
            # Calculate price movement dari signal_date hingga today
            actual_return = self._calculate_actual_return(ticker, signal_date, end_date)
            
            hypothetical_results.append({
                "ticker": ticker,
                "signal_date": signal_date.isoformat(),
                "rank": signal.rank,
                "entry_price": float(entry_price),
                "tp1": float(tp1) if tp1 else None,
                "stop_loss": float(stop_loss) if stop_loss else None,
                "actual_return_pct": actual_return["return_pct"],
                "actual_return_days": actual_return["days"],
                "outcome": self._classify_outcome(actual_return["return_pct"], tp1, stop_loss),
                "hit_tp": tp1 and actual_return["final_price"] >= tp1,
                "hit_sl": stop_loss and actual_return["final_price"] <= stop_loss,
            })
        
        # 3. Get actual paper trading results dalam period yang sama
        actual_trades = self.session.query(PaperTrade).filter(
            PaperTrade.opened_at >= datetime.combine(start_date, datetime.min.time()),
            PaperTrade.opened_at <= datetime.combine(end_date, datetime.max.time())
        ).all()
        
        actual_results = []
        for trade in actual_trades:
            if trade.status == "CLOSED":
                actual_results.append({
                    "ticker": trade.ticker,
                    "action": trade.action,
                    "opened_at": trade.opened_at.isoformat() if trade.opened_at else None,
                    "closed_at": trade.closed_at.isoformat() if trade.closed_at else None,
                    "buy_price": float(trade.price),
                    "sell_price": float(trade.amount / trade.shares) if trade.shares > 0 else float(trade.price),
                    "realized_pnl": float(trade.realized_pnl),
                    "realized_pnl_pct": float(trade.realized_pnl / trade.amount * 100) if trade.amount > 0 else 0,
                    "reason": trade.notes or "N/A"
                })
        
        # 4. Compare hypothetical vs actual
        comparison = self._compare_hypothetical_vs_actual(hypothetical_results, actual_results)
        
        return {
            "status": "success",
            "message": f"Backtest completed: {len(signals)} signals, {len(actual_trades)} paper trades",
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "lookback_days": lookback_days
            },
            "hypothetical": {
                "total_signals": len(hypothetical_results),
                "signals": hypothetical_results,
                "summary": self._summarize_hypothetical(hypothetical_results)
            },
            "actual": {
                "total_trades": len(actual_results),
                "trades": actual_results,
                "summary": self._summarize_actual(actual_results)
            },
            "comparison": comparison
        }
    
    def _calculate_actual_return(self, ticker: str, start_date: date, end_date: date) -> Dict:
        """Calculate actual price movement antara dua dates."""
        try:
            from db.cache import get_cached_ohlcv
            
            # Format dates sebagai string untuk query
            start_str = start_date.isoformat()
            end_str = end_date.isoformat()
            
            # Get OHLCV data dari cache
            df = get_cached_ohlcv(ticker, start_str, end_str)
            
            if df is None or df.empty:
                return {"return_pct": 0.0, "days": 0, "final_price": 0.0}
            
            if "close" in df.columns:
                # Find price at start_date atau setelahnya
                start_price = None
                for idx in range(len(df)):
                    if df.index[idx].date() >= start_date:
                        start_price = float(df["close"].iloc[idx])
                        break
                
                # Final price (latest available)
                final_price = float(df["close"].iloc[-1])
                
                if start_price and start_price > 0:
                    return_pct = ((final_price - start_price) / start_price) * 100
                    days = (df.index[-1].date() - start_date).days
                    return {
                        "return_pct": return_pct,
                        "days": max(days, 1),
                        "final_price": final_price,
                        "start_price": start_price
                    }
        except Exception as e:
            logger.warning(f"[analytics] calculate_actual_return failed for {ticker}: {e}")
        
        return {"return_pct": 0.0, "days": 0, "final_price": 0.0}
    
    def _classify_outcome(self, return_pct: float, tp1: Optional[float], stop_loss: Optional[float]) -> str:
        """Classify signal outcome berdasarkan return vs TP/SL."""
        if tp1 and return_pct >= 5.0:  # TP1 biasanya ~5%+
            return "TP_HIT"
        elif stop_loss and return_pct <= -3.0:  # SL biasanya ~-3%
            return "SL_HIT"
        elif return_pct > 0:
            return "PROFIT"
        elif return_pct < 0:
            return "LOSS"
        else:
            return "FLAT"
    
    def _summarize_hypothetical(self, hypothetical_results: List[Dict]) -> Dict:
        """Generate summary statistics untuk hypothetical portfolio."""
        if not hypothetical_results:
            return {}
        
        returns = [r["actual_return_pct"] for r in hypothetical_results]
        outcomes = [r["outcome"] for r in hypothetical_results]
        
        return {
            "avg_return_pct": float(np.mean(returns)) if returns else 0.0,
            "median_return_pct": float(np.median(returns)) if returns else 0.0,
            "win_rate": (sum(1 for o in outcomes if o in ["TP_HIT", "PROFIT"]) / len(outcomes) * 100) if outcomes else 0.0,
            "tp_hit_rate": (sum(1 for o in outcomes if o == "TP_HIT") / len(outcomes) * 100) if outcomes else 0.0,
            "sl_hit_rate": (sum(1 for o in outcomes if o == "SL_HIT") / len(outcomes) * 100) if outcomes else 0.0,
            "best_ticker": max(hypothetical_results, key=lambda x: x["actual_return_pct"])["ticker"] if hypothetical_results else None,
            "worst_ticker": min(hypothetical_results, key=lambda x: x["actual_return_pct"])["ticker"] if hypothetical_results else None,
        }
    
    def _summarize_actual(self, actual_results: List[Dict]) -> Dict:
        """Generate summary statistics untuk actual paper trades."""
        if not actual_results:
            return {}
        
        pnls = [r["realized_pnl"] for r in actual_results]
        pnl_pcts = [r["realized_pnl_pct"] for r in actual_results]
        
        winning_trades = [r for r in actual_results if r["realized_pnl"] > 0]
        losing_trades = [r for r in actual_results if r["realized_pnl"] < 0]
        
        return {
            "total_trades": len(actual_results),
            "winning_trades": len(winning_trades),
            "losing_trades": len(losing_trades),
            "win_rate": (len(winning_trades) / len(actual_results) * 100) if actual_results else 0.0,
            "avg_pnl": float(np.mean(pnls)) if pnls else 0.0,
            "avg_pnl_pct": float(np.mean(pnl_pcts)) if pnl_pcts else 0.0,
            "total_pnl": float(sum(pnls)),
            "profit_factor": (
                abs(sum(w["realized_pnl"] for w in winning_trades) / sum(l["realized_pnl"] for l in losing_trades))
                if winning_trades and losing_trades else 0.0
            ),
            "best_trade": max(actual_results, key=lambda x: x["realized_pnl"]) if actual_results else None,
            "worst_trade": min(actual_results, key=lambda x: x["realized_pnl"]) if actual_results else None,
        }
    
    def _compare_hypothetical_vs_actual(
        self, 
        hypothetical: List[Dict], 
        actual: List[Dict]
    ) -> Dict:
        """Compare hypothetical signals performance vs actual paper trades."""
        if not hypothetical or not actual:
            return {"message": "Not enough data for comparison"}
        
        hyp_summary = self._summarize_hypothetical(hypothetical)
        act_summary = self._summarize_actual(actual)
        
        # Calculate performance difference
        win_rate_diff = act_summary.get("win_rate", 0.0) - hyp_summary.get("win_rate", 0.0)
        avg_return_diff = act_summary.get("avg_pnl_pct", 0.0) - hyp_summary.get("avg_return_pct", 0.0)
        
        return {
            "performance_comparison": {
                "win_rate_diff": win_rate_diff,
                "avg_return_diff": avg_return_diff,
                "hypothetical_better": win_rate_diff < 0,  # Jika negative, hypothetical lebih baik
                "actual_better": win_rate_diff > 0,
            },
            "interpretation": self._interpret_comparison(win_rate_diff, avg_return_diff),
            "recommendations": self._generate_recommendations(hyp_summary, act_summary)
        }
    
    def _interpret_comparison(self, win_rate_diff: float, avg_return_diff: float) -> str:
        """Interpret performance comparison results."""
        if abs(win_rate_diff) < 5.0 and abs(avg_return_diff) < 2.0:
            return "Paper trading performance matches hypothetical signals well."
        elif win_rate_diff > 5.0:
            return "Paper trading outperforms hypothetical signals (better selection/execution)."
        elif win_rate_diff < -5.0:
            return "Hypothetical signals perform better than paper trading (execution gap)."
        else:
            return "Performance differences are within acceptable range."
    
    def _generate_recommendations(self, hyp_summary: Dict, act_summary: Dict) -> List[str]:
        """Generate actionable recommendations dari comparison."""
        recommendations = []
        
        if act_summary.get("win_rate", 0.0) < 50.0:
            recommendations.append("Win rate < 50% — consider more selective stock picking.")
        
        if act_summary.get("profit_factor", 0.0) < 1.0:
            recommendations.append("Profit factor < 1.0 — losses outweigh gains.")
        
        if act_summary.get("avg_pnl_pct", 0.0) < 1.0:
            recommendations.append("Average return < 1% — review entry/exit strategy.")
        
        if hyp_summary.get("tp_hit_rate", 0.0) > 30.0:
            recommendations.append(f"High TP hit rate ({hyp_summary['tp_hit_rate']:.1f}%) — consider holding longer for bigger gains.")
        
        if not recommendations:
            recommendations.append("Performance is solid. Continue current strategy.")
        
        return recommendations

    # ======================== PERFORMANCE ATTRIBUTION ========================

    def get_performance_attribution(self) -> Dict:
        """
        Analyze performance attribution — which factors contribute most to returns.
        
        Returns:
            Dict dengan attribution analysis:
            - by_ticker: performance per stock
            - by_signal_rank: performance vs signal ranking
            - by_time_horizon: performance vs holding period
            - by_market_condition
        """
        all_trades = self.session.query(PaperTrade).filter(
            PaperTrade.status == "CLOSED"
        ).all()
        
        if not all_trades:
            return {"status": "info", "message": "No closed trades for attribution analysis"}
        
        attribution_results = {
            "by_ticker": {},
            "by_signal_rank": {},
            "by_holding_period": {},
        }
        
        for trade in all_trades:
            ticker = trade.ticker
            holding_days = 0
            if trade.opened_at and trade.closed_at:
                holding_days = (trade.closed_at - trade.opened_at).days
            
            pnl_pct = float(trade.realized_pnl / trade.amount * 100) if trade.amount > 0 else 0
            
            # By ticker
            if ticker not in attribution_results["by_ticker"]:
                attribution_results["by_ticker"][ticker] = {
                    "total_trades": 0,
                    "total_pnl": 0.0,
                    "total_pnl_pct": 0.0,
                    "winning_trades": 0,
                    "losing_trades": 0,
                }
            
            ticker_stats = attribution_results["by_ticker"][ticker]
            ticker_stats["total_trades"] += 1
            ticker_stats["total_pnl"] += float(trade.realized_pnl)
            ticker_stats["total_pnl_pct"] += pnl_pct
            if trade.realized_pnl > 0:
                ticker_stats["winning_trades"] += 1
            else:
                ticker_stats["losing_trades"] += 1
            
            # By holding period category
            holding_category = "SHORT" if holding_days <= 3 else "MEDIUM" if holding_days <= 10 else "LONG"
            if holding_category not in attribution_results["by_holding_period"]:
                attribution_results["by_holding_period"][holding_category] = {
                    "total_trades": 0,
                    "total_pnl": 0.0,
                    "avg_pnl_pct": 0.0,
                }
            
            period_stats = attribution_results["by_holding_period"][holding_category]
            period_stats["total_trades"] += 1
            period_stats["total_pnl"] += float(trade.realized_pnl)
            period_stats["avg_pnl_pct"] = (period_stats["total_pnl"] / trade.amount * 100) if trade.amount > 0 else 0
        
        # Calculate averages
        for ticker, stats in attribution_results["by_ticker"].items():
            if stats["total_trades"] > 0:
                stats["avg_pnl_pct"] = stats["total_pnl_pct"] / stats["total_trades"]
                stats["win_rate"] = (stats["winning_trades"] / stats["total_trades"] * 100)
        
        return {
            "status": "success",
            "message": f"Performance attribution for {len(all_trades)} closed trades",
            "attribution": attribution_results,
            "best_performing_ticker": max(
                attribution_results["by_ticker"].items(), 
                key=lambda x: x[1]["total_pnl"]
            )[0] if attribution_results["by_ticker"] else None,
            "worst_performing_ticker": min(
                attribution_results["by_ticker"].items(), 
                key=lambda x: x[1]["total_pnl"]
            )[0] if attribution_results["by_ticker"] else None,
        }

    # ======================== EXPORT REPORTS ========================

    def export_trade_history_csv(self) -> str:
        """Export semua paper trades ke CSV format string."""
        all_trades = self.session.query(PaperTrade).order_by(PaperTrade.opened_at).all()
        
        if not all_trades:
            return "No trades to export"
        
        # Create CSV string
        csv_lines = [
            "Date,Ticker,Action,Lot,Price,Amount,Fee,Status,Realized P&L,P&L %,Reason"
        ]
        
        for trade in all_trades:
            date_str = trade.opened_at.strftime("%Y-%m-%d %H:%M") if trade.opened_at else "N/A"
            pnl_pct = (trade.realized_pnl / trade.amount * 100) if trade.amount > 0 else 0
            
            csv_lines.append(
                f"{date_str},"
                f"{trade.ticker},"
                f"{trade.action},"
                f"{trade.lot},"
                f"{trade.price},"
                f"{trade.amount},"
                f"{trade.fee},"
                f"{trade.status},"
                f"{trade.realized_pnl},"
                f"{pnl_pct:.2f},"
                f"\"{trade.notes or ''}\""
            )
        
        return "\n".join(csv_lines)
    
    def export_performance_summary_markdown(self) -> str:
        """Export performance summary dalam format markdown."""
        wallet = self.trading_service.get_or_create_wallet()
        summary = self.trading_service.get_wallet_summary(auto_check_tpsl=False)
        
        markdown = f"""# Paper Trading Performance Summary
Generated: {datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")}

## Portfolio Overview
- **Total Topup**: Rp {wallet.total_topup:,.0f}
- **Current Equity**: Rp {summary['total_equity']:,.0f}
- **Total Return**: {summary['total_return_pct']:+.2f}%
- **Cash Balance**: Rp {summary['cash']:,.0f}
- **Invested Amount**: Rp {summary['total_invested']:,.0f}
- **Realized P&L**: Rp {summary['realized_pnl']:+,.0f}
- **Unrealized P&L**: Rp {summary['unrealized_pnl']:+,.0f}

## Open Positions
{len(summary['positions'])} positions open
"""
        
        for pos in summary['positions']:
            markdown += f"- **{pos['ticker']}**: {pos['lot']} lot @ Rp {pos['buy_price']:,.0f} → Now Rp {pos['current_price']:,.0f} ({pos['unrealized_pnl_pct']:+.2f}%)\n"
        
        # Add attribution analysis jika ada closed trades
        attribution = self.get_performance_attribution()
        if attribution['status'] == 'success':
            markdown += f"\n## Performance Attribution\n"
            
            by_ticker = attribution['attribution']['by_ticker']
            if by_ticker:
                markdown += "### By Ticker\n"
                for ticker, stats in sorted(by_ticker.items(), key=lambda x: x[1]['total_pnl'], reverse=True):
                    markdown += f"- **{ticker}**: {stats['total_trades']} trades, P&L Rp {stats['total_pnl']:+,.0f}, Win Rate {stats['win_rate']:.1f}%\n"
        
        return markdown

    # ======================== CLOSED POSITIONS ANALYSIS ========================

    def analyze_closed_positions(self) -> Dict:
        """
        Detailed analysis of closed positions.
        
        Returns:
            Dict dengan detailed analysis:
            - pnl_distribution: histogram buckets
            - holding_period_stats: days vs returns
            - win_loss_patterns: sequential wins/losses
            - best_worst_trades: extreme cases
        """
        closed_trades = self.session.query(PaperTrade).filter(
            PaperTrade.status == "CLOSED"
        ).all()
        
        if not closed_trades:
            return {"status": "info", "message": "No closed positions to analyze"}
        
        analysis = {
            "pnl_distribution": {
                "large_loss": 0,     # < -5%
                "small_loss": 0,     # -5% to 0%
                "small_profit": 0,   # 0% to 5%
                "medium_profit": 0,  # 5% to 10%
                "large_profit": 0,   # > 10%
            },
            "holding_period_stats": {
                "short_term": {"count": 0, "total_pnl": 0.0, "avg_pnl_pct": 0.0},
                "medium_term": {"count": 0, "total_pnl": 0.0, "avg_pnl_pct": 0.0},
                "long_term": {"count": 0, "total_pnl": 0.0, "avg_pnl_pct": 0.0},
            },
            "best_trades": [],
            "worst_trades": [],
            "win_streak": 0,
            "loss_streak": 0,
        }
        
        for trade in closed_trades:
            pnl_pct = float(trade.realized_pnl / trade.amount * 100) if trade.amount > 0 else 0
            holding_days = 0
            if trade.opened_at and trade.closed_at:
                holding_days = (trade.closed_at - trade.opened_at).days
            
            # P&L distribution
            if pnl_pct < -5:
                analysis["pnl_distribution"]["large_loss"] += 1
            elif pnl_pct < 0:
                analysis["pnl_distribution"]["small_loss"] += 1
            elif pnl_pct < 5:
                analysis["pnl_distribution"]["small_profit"] += 1
            elif pnl_pct < 10:
                analysis["pnl_distribution"]["medium_profit"] += 1
            else:
                analysis["pnl_distribution"]["large_profit"] += 1
            
            # Holding period stats
            if holding_days <= 3:
                category = "short_term"
            elif holding_days <= 10:
                category = "medium_term"
            else:
                category = "long_term"
            
            stats = analysis["holding_period_stats"][category]
            stats["count"] += 1
            stats["total_pnl"] += float(trade.realized_pnl)
            stats["avg_pnl_pct"] = stats["total_pnl_pct"] / stats["count"] if stats["count"] > 0 else 0
        
        # Find best/worst trades
        sorted_trades = sorted(
            closed_trades, 
            key=lambda t: float(t.realized_pnl / t.amount) if t.amount > 0 else 0,
            reverse=True
        )
        
        analysis["best_trades"] = [
            {
                "ticker": t.ticker,
                "pnl": float(t.realized_pnl),
                "pnl_pct": float(t.realized_pnl / t.amount * 100) if t.amount > 0 else 0,
                "holding_days": (t.closed_at - t.opened_at).days if t.opened_at and t.closed_at else 0,
                "reason": t.notes or "N/A"
            }
            for t in sorted_trades[:3]
        ]
        
        analysis["worst_trades"] = [
            {
                "ticker": t.ticker,
                "pnl": float(t.realized_pnl),
                "pnl_pct": float(t.realized_pnl / t.amount * 100) if t.amount > 0 else 0,
                "holding_days": (t.closed_at - t.opened_at).days if t.opened_at and t.closed_at else 0,
                "reason": t.notes or "N/A"
            }
            for t in sorted_trades[-3:]
        ]
        
        return {
            "status": "success",
            "message": f"Analysis of {len(closed_trades)} closed positions",
            "analysis": analysis,
        }