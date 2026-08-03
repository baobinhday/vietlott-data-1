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
tickets per draw), we set ``SPECIALS_TOP_N = 4`` so the base class
overrides ``predict_special`` to return only the 4 most frequently
drawn specials in the lookback window per draw date.  Effective cost
becomes ``2 × 3 = 8`` tickets per draw.

"Special" mode (DD filter)
--------------------------
Set :attr:`DD_FILTER_ENABLED` to ``True`` to restrict ticket purchases
to draws where the Độc Đắc (jackpot) strictly exceeds
:attr:`DD_THRESHOLD` (default 12B VND – the threshold at which
Vietlott's jackpot-split rule can kick in, see
:mod:`vietlott.config.prizes`).  In that mode:

* The strategies, voters and lookback windows still see the **full**
  historical dataset (so they can learn from every draw, not just
  the eligible ones).
* Only the eligible draws generate tickets (no cost, no gain for
  draws where Độc Đắc ≤ threshold).
* The output file is renamed to ``<base>_special.md`` and the
  product display gains a ``(Special: …)`` suffix.

Leave the flag at ``False`` to keep the original behaviour (one
ticket per draw on the full history).
"""

from typing import ClassVar

from loguru import logger

from machine_learning.render_prediction_base import BasePowerPredictionSummaryGenerator


class Power535PredictionSummaryGenerator(BasePowerPredictionSummaryGenerator):
    """Power 5/35 prediction summary generator."""

    PRODUCT_NAME: ClassVar[str] = "power_535"
    TPD: ClassVar[int] = 4  # 2 mains × 3 hot specials = 6 tickets / draw
    BEST_THRESHOLD: ClassVar[int] = 4
    OUTPUT_NAME: ClassVar[str] = "readme_535.md"
    PRODUCT_DISPLAY: ClassVar[str] = "Power 5/35"
    INCLUDES_SOLO_BASELINES: ClassVar[bool] = True
    INCLUDES_PATTERN_HYBRID: ClassVar[bool] = True
    SPECIALS_TOP_N: ClassVar[int | None] = 4
    SPECIALS_MODE: ClassVar[str] = "cold"  # Chọn các số đặc biệt ít về nhất

    # Jackpot-split threshold (see :mod:`vietlott.config.prizes`).
    DD_FILTER_ENABLED: ClassVar[bool] = True
    DD_THRESHOLD: ClassVar[int] = 12_000_000_000  # 12B VND
    JACKPOT_PRIZE_NAME: ClassVar[str] = "Giải Độc Đắc"


def main():
    """Main entry point for Power 5/35 prediction summary generation."""
    generator = Power535PredictionSummaryGenerator()
    generator.save_prediction_summary()
    logger.info("Power 5/35 prediction summary generation completed successfully!")


if __name__ == "__main__":
    main()
