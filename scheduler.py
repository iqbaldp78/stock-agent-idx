"""
Stock Agent IDX — Scheduler
Placeholder untuk Phase 0. APScheduler jobs akan ditambahkan di Phase 6.
"""
import time
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def main():
    logger.info("Stock Agent IDX — Scheduler started")
    logger.info("Waiting for Phase 6 implementation (APScheduler jobs)")
    logger.info("Container is alive and connected to stock_net")

    # Keep container alive
    while True:
        time.sleep(3600)


if __name__ == "__main__":
    main()
