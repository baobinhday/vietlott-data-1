#!/usr/bin/env python
"""
Prediction Summary Generator for Vietlott Power 5/35 Data.

Thin subclass of :class:`BasePowerPredictionSummaryGenerator` that
configures the base for the Power 5/35 product.  All strategy
construction, backtest orchestration and markdown assembly is shared
with Power 6/55 and Power 6/45 via ``render_prediction_base.py``.

Note
----
Power 5/35 uses ``TPD = 2`` (two main-number tickets per draw) and is
the only product where ``special_pick_required=True``.  Instead of
wheeling through all 12 specials (which would yield ``2 × 12 = 24``
tickets per draw), we set ``HOT_SPECIALS_TOP_N = 4`` so the base class
overrides ``predict_special`` to return only the 4 most frequently
drawn specials in the lookback window per draw date.  Effective cost
becomes ``2 × 3 = 8`` tickets per draw.
"""

from loguru import logger

from machine_learning.render_prediction_base import BasePowerPredictionSummaryGenerator


class Power535PredictionSummaryGenerator(BasePowerPredictionSummaryGenerator):
    """Power 5/35 prediction summary generator."""

    PRODUCT_NAME = "power_535"
    TPD = 2  # 2 mains × 3 hot specials = 6 tickets / draw
    BEST_THRESHOLD = 4
    OUTPUT_NAME = "readme_535.md"
    PRODUCT_DISPLAY = "Power 5/35"
    INCLUDES_SOLO_BASELINES = True
    INCLUDES_PATTERN_HYBRID = True
    HOT_SPECIALS_TOP_N = 3  # top-3 hot specials instead of wheeling 1..12


def main():
    """Main entry point for Power 5/35 prediction summary generation."""
    generator = Power535PredictionSummaryGenerator()
    generator.save_prediction_summary()
    logger.info("Power 5/35 prediction summary generation completed successfully!")


if __name__ == "__main__":
    main()
