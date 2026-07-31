#!/usr/bin/env python
"""
Prediction Summary Generator for Vietlott Power 6/45 Data.

Thin subclass of :class:`BasePowerPredictionSummaryGenerator` that
configures the base for the Power 6/45 product.  All strategy
construction, backtest orchestration and markdown assembly is shared
with Power 6/55 and Power 5/35 via ``render_prediction_base.py``.
"""

from loguru import logger

from machine_learning.render_prediction_base import BasePowerPredictionSummaryGenerator


class Power645PredictionSummaryGenerator(BasePowerPredictionSummaryGenerator):
    """Power 6/45 prediction summary generator."""

    PRODUCT_NAME = "power_645"
    TPD = 30
    BEST_THRESHOLD = 4
    OUTPUT_NAME = "readme_645.md"
    PRODUCT_DISPLAY = "Power 6/45"
    INCLUDES_SOLO_BASELINES = True
    INCLUDES_PATTERN_HYBRID = True


def main():
    """Main entry point for Power 6/45 prediction summary generation."""
    generator = Power645PredictionSummaryGenerator()
    generator.save_prediction_summary()
    logger.info("Power 6/45 prediction summary generation completed successfully!")


if __name__ == "__main__":
    main()
