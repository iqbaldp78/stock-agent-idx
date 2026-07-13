"""
Stock Agent IDX — Scheduler
APScheduler: end-of-day analysis + performance check.
"""
import logging
import datetime
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def run_daily_analysis():
    """End-of-day analysis: full pipeline + save to DB."""
    logger.info("=== DAILY ANALYSIS START ===")
    try:
        from graph.workflow import run_full_analysis
        from db.tracker import save_full_result

        result = run_full_analysis()
        save_full_result(result)

        top_picks = result.get("top_picks", [])
        logger.info(f"Analysis complete: {len(top_picks)} top picks")
        for p in top_picks:
            logger.info(f"  #{p.get('rank')} {p.get('ticker')} — {p.get('conviction', 'N/A')}")

    except Exception as e:
        logger.exception(f"Daily analysis failed: {e}")

    logger.info("=== DAILY ANALYSIS END ===")


def run_performance_check():
    """Check yesterday's signals: hit target or hit SL?"""
    logger.info("=== PERFORMANCE CHECK START ===")
    try:
        from datetime import datetime, timedelta
        from sqlalchemy.orm import Session
        from db import SessionLocal
        from db.models import Signal, Performance
        from data.fetcher_stockbit import get_stock_info

        db: Session = SessionLocal()
        today = datetime.now()

        # Get open signals (no performance record with final result)
        open_signals = db.query(Signal).filter(
            Signal.run_date <= today - timedelta(days=1),
            ~Signal.id.in_(
                db.query(Performance.signal_id).filter(
                    Performance.result.in_([
                        "HIT_TARGET_1", "HIT_TARGET_2",
                        "HIT_TP1", "HIT_TP2", "HIT_TP3",
                        "HIT_SL",
                    ])
                )
            ),
        ).all()

        logger.info(f"Checking {len(open_signals)} open signals")

        for signal in open_signals:
            try:
                info = get_stock_info(signal.ticker)
                current_price = info.get("current_price")

                if not current_price:
                    continue

                # Determine result - check TP levels sequentially (highest to lowest)
                result = "OPEN"
                return_pct = 0

                entry_price = float(signal.entry_high or signal.entry_low or 0)
                if entry_price == 0:
                    continue

                return_pct = (current_price - entry_price) / entry_price * 100

                # Check new TP1/TP2/TP3 levels first (multi-level profit taking)
                if signal.target_3 and current_price >= float(signal.target_3):
                    result = "HIT_TP3"
                elif signal.target_2 and current_price >= float(signal.target_2):
                    result = "HIT_TP2"
                elif signal.target_1 and current_price >= float(signal.target_1):
                    result = "HIT_TP1"
                # Fallback to legacy target levels if TP levels not available
                elif signal.target_1 and current_price >= float(signal.target_1):
                    result = "HIT_TARGET_1"
                elif signal.target_2 and current_price >= float(signal.target_2):
                    result = "HIT_TARGET_2"
                # Check stop loss
                elif signal.stop_loss and current_price <= float(signal.stop_loss):
                    result = "HIT_SL"

                # Save performance record
                perf = Performance(
                    signal_id=signal.id,
                    check_date=today,
                    actual_price=current_price,
                    result=result,
                    return_pct=round(return_pct, 2),
                )
                db.add(perf)

                logger.info(
                    f"  {signal.ticker}: {result} | price={current_price} | "
                    f"return={return_pct:+.1f}%"
                )

            except Exception as e:
                logger.warning(f"  {signal.ticker}: check failed — {e}")
                continue

        db.commit()
        db.close()

    except Exception as e:
        logger.exception(f"Performance check failed: {e}")

    logger.info("=== PERFORMANCE CHECK END ===")


def run_news_ingester():
    """Fetch real-time news from Stockbit and populate Vector DB."""
    logger.info("=== NEWS INGESTER START ===")
    try:
        import subprocess
        result = subprocess.run(["python", "scripts/news_ingester.py"], capture_output=True, text=True)
        if result.returncode != 0:
            logger.error(f"News Ingester failed: {result.stderr}")
        else:
            logger.info("News Ingester completed successfully")
    except Exception as e:
        logger.error(f"News Ingester error: {e}")

def run_dca_check():
    """Check DCA triggers harian — notify only, no auto-execute."""
    logger.info("=== DCA TRIGGER CHECK START ===")
    try:
        from portfolio.dca_strategy import check_all_dca_triggers

        triggered = check_all_dca_triggers()

        if triggered:
            logger.info(f"Found {len(triggered)} DCA triggers:")
            for t in triggered:
                ticker = t.get("ticker")
                current = t.get("current_price")
                target = t.get("next_buy_price")
                remaining = t.get("remaining_budget")
                logger.info(
                    f"  🎯 {ticker}: Current {current:,.0f} <= Target {target:,.0f} "
                    f"| Budget remaining: Rp {remaining:,.0f}"
                )
        else:
            logger.info("No DCA triggers today.")

    except Exception as e:
        logger.exception(f"DCA check failed: {e}")

    logger.info("=== DCA TRIGGER CHECK END ===")


def run_portfolio_analysis():
    """AI Portfolio analysis harian — rebalancing, DCA priority, risk, performance."""
    logger.info("=== PORTFOLIO AI ANALYSIS START ===")
    try:
        from portfolio.manager import get_all_holdings, get_transactions
        from portfolio.dca_strategy import get_active_strategies
        from db import SessionLocal
        from db.models import Signal
        from datetime import datetime, timedelta
        from agents.portfolio_advisor import analyze_portfolio

        # Get data
        holdings = get_all_holdings()
        if not holdings:
            logger.info("No holdings, skip portfolio analysis.")
            return

        strategies = get_active_strategies()

        # Get latest TOP PICKS from DB
        db = SessionLocal()
        try:
            top_picks_rows = db.query(Signal).filter(
                Signal.run_date == db.query(Signal.run_date).order_by(Signal.run_date.desc()).limit(1).scalar_subquery()
            ).order_by(Signal.rank).limit(10).all()

            top_picks = [
                {
                    "ticker": s.ticker,
                    "entry_low": float(s.entry_low) if s.entry_low else None,
                    "entry_high": float(s.entry_high) if s.entry_high else None,
                    "max_entry": float(s.max_entry) if s.max_entry else None,
                    "conviction": s.conviction,
                    "thesis": s.thesis,
                    "bandar_avg_1m": float(s.bandar_avg_1m) if s.bandar_avg_1m else None,
                }
                for s in top_picks_rows
            ]
        finally:
            db.close()

        transactions = get_transactions(start_date=datetime.date.today() - datetime.timedelta(days=30))

        # Run AI analysis
        result = analyze_portfolio(
            holdings=holdings,
            active_strategies=strategies,
            top_picks=top_picks,
            monthly_budget=2000000,  # TODO: make this configurable
            transactions=transactions,
        )

        # Log summary
        logger.info(f"Analysis: {result.get('summary', 'N/A')}")

        # Log key findings
        rebalancing = result.get("rebalancing", {})
        if rebalancing.get("needed"):
            logger.info(f"  ⚖️ Rebalancing needed:")
            for action in rebalancing.get("actions", [])[:3]:
                logger.info(f"    - {action.get('ticker')}: {action.get('action')} — {action.get('reason')}")

        dca_priority = result.get("dca_priority", [])
        if dca_priority:
            logger.info(f"  💰 DCA Priority this month:")
            for p in dca_priority[:3]:
                logger.info(
                    f"    #{p.get('rank')} {p.get('ticker')}: "
                    f"Rp {p.get('allocation', 0):,.0f} | {p.get('timing_status')} | {p.get('conviction')}"
                )

        risk = result.get("risk_analysis", {})
        risk_level = risk.get("risk_level", "N/A")
        div_score = risk.get("diversification_score", 0)
        logger.info(f"  ⚠️ Risk: {risk_level} | Diversification: {div_score}/10")

        # Notify if action needed
        if rebalancing.get("needed") or risk_level == "HIGH":
            logger.warning("🚨 Portfolio action recommended — check UI for details")

    except Exception as e:
        logger.exception(f"Portfolio analysis failed: {e}")

    logger.info("=== PORTFOLIO AI ANALYSIS END ===")


def main():
    logger.info("Stock Agent IDX — Scheduler started")
    logger.info("Jobs: news_ingester@every 30 mins")

    scheduler = BlockingScheduler(timezone="Asia/Jakarta")

    # News Ingester: Every 30 minutes, 24/7
    scheduler.add_job(
        run_news_ingester,
        CronTrigger(minute="0,30"),
        id="news_ingester",
        name="News DB Ingester",
    )

    try:
        logger.info("Scheduler running. Press Ctrl+C to exit.")
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped.")
        logger.info("Scheduler stopped.")


if __name__ == "__main__":
    main()
