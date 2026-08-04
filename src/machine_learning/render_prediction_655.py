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

"Special" mode (DD filter)
--------------------------
Set :attr:`DD_FILTER_ENABLED` to ``True`` to restrict ticket purchases
to draws where the Jackpot 1 strictly exceeds :attr:`DD_THRESHOLD`
(default 200B VND).  Strategies / voters / lookback windows still see
the full historical dataset – only the ticket purchase is gated.
The output file is renamed to ``<base>_special.md`` and the product
display gains a ``(Special: …)`` suffix.
"""

from typing import ClassVar

from loguru import logger

from machine_learning.render_prediction_base import BasePowerPredictionSummaryGenerator


class HybridPredictionSummaryGenerator(BasePowerPredictionSummaryGenerator):
    """Power 6/55 prediction summary generator."""

    PRODUCT_NAME: ClassVar[str] = "power_655"
    TPD: ClassVar[int] = 30
    BEST_THRESHOLD: ClassVar[int] = 5
    OUTPUT_NAME: ClassVar[str] = "readme_655.md"
    PRODUCT_DISPLAY: ClassVar[str] = "Power 6/55"
    INCLUDES_SOLO_BASELINES: ClassVar[bool] = True
    INCLUDES_PATTERN_HYBRID: ClassVar[bool] = True

    # "Special" mode: chỉ mua vé khi Jackpot 1 > 200B (toggle True to enable).
    DD_FILTER_ENABLED: ClassVar[bool] = True
    DD_THRESHOLD: ClassVar[int] = 280_000_000_000  # 200B VND
    JACKPOT_PRIZE_NAME: ClassVar[str] = "Jackpot 1"
    INVERSE_HYBRID_TOP_K: ClassVar[int] = 16


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
