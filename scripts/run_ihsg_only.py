#!/usr/bin/env python3
"""
Run IHSG Prediction Only
Standalone IHSG predictor (tanpa full stock analysis).
Usage: python scripts/run_ihsg_only.py
"""
import sys
sys.path.insert(0, "/app")

from agents.ihsg_predictor import predict_ihsg
from db.tracker import save_ihsg_prediction
from datetime import date
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


def main():
    logger.info("=" * 60)
    logger.info("IHSG PREDICTOR — Standalone Run")
    logger.info("=" * 60)

    try:
        logger.info("[1/2] Generating IHSG prediction...")
        pred = predict_ihsg()

        if not pred or pred.get("current_price", 0) == 0:
            logger.error("❌ Prediction failed or no data")
            return 1

        logger.info("[2/2] Saving to database...")
        save_ihsg_prediction(date.today(), pred)

        # Display results
        logger.info("=" * 60)
        logger.info("✅ IHSG Prediction Complete")
        logger.info("=" * 60)
        logger.info(f"Direction:      {pred.get('direction')} ({pred.get('confidence')})")
        logger.info(f"Current Price:  {pred.get('current_price'):,.0f}")
        logger.info(f"D+1 Target:     {pred.get('day_1_price'):,.0f} ({pred.get('day_1_pct'):+.2f}%)")
        logger.info(f"D+3 Target:     {pred.get('day_3_price'):,.0f} ({pred.get('day_3_pct'):+.2f}%)")
        logger.info(f"D+5 Target:     {pred.get('day_5_price'):,.0f} ({pred.get('day_5_pct'):+.2f}%)")
        logger.info(f"D+7 Target:     {pred.get('day_7_price'):,.0f} ({pred.get('day_7_pct'):+.2f}%)")
        logger.info(f"Combined Score: {pred.get('component_scores', {}).get('combined', 0):.2f}")
        logger.info("=" * 60)
        logger.info("💾 Saved to: ihsg_predictions table")
        logger.info("🌐 View at: http://localhost:8501 → IHSG Predictor tab")
        logger.info("=" * 60)

        return 0

    except Exception as e:
        logger.exception(f"❌ Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
