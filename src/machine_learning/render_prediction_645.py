#!/usr/bin/env python
"""
Prediction Summary Generator for Vietlott Power 6/45 Data.

Thin subclass of :class:`BasePowerPredictionSummaryGenerator` that
configures the base for the Power 6/45 product.  All strategy
construction, backtest orchestration and markdown assembly is shared
with Power 6/55 and Power 5/35 via ``render_prediction_base.py``.

"Special" mode (DD filter)
--------------------------
Set :attr:`DD_FILTER_ENABLED` to ``True`` to restrict ticket purchases
to draws where the Jackpot strictly exceeds :attr:`DD_THRESHOLD`
(default 70B VND).  Strategies / voters / lookback windows still see
the full historical dataset – only the ticket purchase is gated.
The output file is renamed to ``<base>_special.md`` and the product
display gains a ``(Special: …)`` suffix.
"""

from typing import ClassVar, List, Tuple

from loguru import logger

from machine_learning.render_prediction_base import BasePowerPredictionSummaryGenerator
from machine_learning.strategies import AntiShareStrategy, PackingScheduler
from machine_learning.strategies.base import PredictModel


class Power645PredictionSummaryGenerator(BasePowerPredictionSummaryGenerator):
    """Power 6/45 prediction summary generator."""

    PRODUCT_NAME: ClassVar[str] = "power_645"
    TPD: ClassVar[int] = 4
    BEST_THRESHOLD: ClassVar[int] = 4
    OUTPUT_NAME: ClassVar[str] = "readme_645.md"
    PRODUCT_DISPLAY: ClassVar[str] = "Power 6/45"
    INCLUDES_SOLO_BASELINES: ClassVar[bool] = True
    INCLUDES_PATTERN_HYBRID: ClassVar[bool] = True

    # "Special" mode: chỉ mua vé khi Jackpot > 70B (toggle True to enable).
    DD_FILTER_ENABLED: ClassVar[bool] = True
    DD_THRESHOLD: ClassVar[int] = 70_000_000_000  # 78.8B VND
    JACKPOT_PRIZE_NAME: ClassVar[str] = "Jackpot"

    INVERSE_HYBRID_TOP_K: ClassVar[int] = 15

    def _extra_strategy_defs(self, df_pd) -> List[Tuple[str, PredictModel]]:
        """Append the 6/45-specific ``AntiShare`` and ``Packing`` strategies.

        Both are ``PredictModel`` subclasses that accept the shared
        constructor signature, so they are instantiated through
        :meth:`_make_voter` for consistency with the solo baselines.
        """
        return [
            (
                "AntiShare Strategy",
                self._make_voter(AntiShareStrategy, df_pd, self.TPD, lookback_days=365),
            ),
            (
                "Packing Scheduler",
                self._make_voter(PackingScheduler, df_pd, self.TPD),
            ),
        ]


def main():
    """Main entry point for Power 6/45 prediction summary generation."""
    generator = Power645PredictionSummaryGenerator()
    generator.save_prediction_summary()
    logger.info("Power 6/45 prediction summary generation completed successfully!")


if __name__ == "__main__":
    main()
