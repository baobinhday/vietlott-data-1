#!/usr/bin/env python
"""
Prediction Summary Generator for Vietlott Power 6/55 Data.

Thin subclass of :class:`BasePowerPredictionSummaryGenerator` that
configures the base for the Power 6/55 product.  All strategy
construction, backtest orchestration and markdown assembly is shared
with Power 6/45 and Power 5/35 via ``render_prediction_base.py``.

Note
----
The 6/55 report historically contained only hybrid strategies (no
solo-baseline voters, no Pattern → Hybrid).  ``INCLUDES_SOLO_BASELINES``
and ``INCLUDES_PATTERN_HYBRID`` are kept ``False`` here to preserve
the historical report shape.
"""

from loguru import logger

from machine_learning.render_prediction_base import BasePowerPredictionSummaryGenerator


class HybridPredictionSummaryGenerator(BasePowerPredictionSummaryGenerator):
    """Power 6/55 prediction summary generator."""

    PRODUCT_NAME = "power_655"
    TPD = 30
    BEST_THRESHOLD = 5
    OUTPUT_NAME = "readme_655.md"
    PRODUCT_DISPLAY = "Power 6/55"
    INCLUDES_SOLO_BASELINES = True
    INCLUDES_PATTERN_HYBRID = True


def main():
    """Main entry point for Power 6/55 prediction summary generation."""
    try:
        generator = HybridPredictionSummaryGenerator()
        generator.save_prediction_summary()
        logger.info("Power 6/55 prediction summary generation completed successfully!")
    except Exception as e:
        logger.error(f"Failed to generate Power 6/55 prediction summary: {e}")
        raise


if __name__ == "__main__":
    main()
