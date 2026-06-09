"""
Stock Agent IDX — Scheduler
APScheduler: end-of-day analysis + performance check.
"""
import logging
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
        from datetime import date, timedelta
        from sqlalchemy.orm import Session
        from db import SessionLocal
        from db.models import Signal, Performance
        from data.fetcher_stockbit import get_stock_info

        db: Session = SessionLocal()
        today = date.today()

        # Get open signals (no performance record with final result)
        open_signals = db.query(Signal).filter(
            Signal.run_date <= today - timedelta(days=1),
            ~Signal.id.in_(
                db.query(Performance.signal_id).filter(
                    Performance.result.in_(["HIT_TARGET_1", "HIT_TARGET_2", "HIT_SL"])
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


def main():
    logger.info("Stock Agent IDX — Scheduler started")
    logger.info("Jobs: daily_analysis@16:15 WIB, performance_check@16:30 WIB")

    scheduler = BlockingScheduler(timezone="Asia/Jakarta")

    # End-of-day analysis: Mon-Fri at 16:15 WIB
    scheduler.add_job(
        run_daily_analysis,
        CronTrigger(day_of_week="mon-fri", hour=16, minute=15),
        id="daily_analysis",
        name="Daily Stock Analysis",
    )

    # Performance check: Mon-Fri at 16:30 WIB
    scheduler.add_job(
        run_performance_check,
        CronTrigger(day_of_week="mon-fri", hour=16, minute=30),
        id="performance_check",
        name="Performance Check",
    )

    logger.info("Scheduler running. Press Ctrl+C to exit.")

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped.")


if __name__ == "__main__":
    main()
