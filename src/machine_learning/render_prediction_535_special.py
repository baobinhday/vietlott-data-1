#!/usr/bin/env python
"""
Prediction Summary Generator for Vietlott Power 5/35 - **Special** variant.

Like :class:`Power535PredictionSummaryGenerator` but only buys tickets on
draws where the Độc Đắc (jackpot) is **greater than 12B VND** – the
threshold at which Vietlott's jackpot-split rule can kick in.  Draws
where the jackpot is at or below 12B are excluded from the backtest
entirely (no cost, no ticket, no revenue).

Notes
-----
* The threshold is configurable via the ``DD_THRESHOLD`` class
  attribute (default ``12_000_000_000`` VND, matching the official
  Vietlott rule described in :mod:`vietlott.config.prizes`).
* Filtering is done at data-load time by overriding
  :meth:`BasePowerPredictionSummaryGenerator._load_lottery_data`, so
  every strategy / voter / lookback sees the same filtered set of
  draws.  Draws not in the prize file fall back to the standard
  (non-special) dataset – useful for older history that has not yet
  been crawled for prize values.
* Prize calculation per draw is unchanged from the regular
  ``power_535`` pipeline – the split rule + 1/3-1/6 redistribution is
  honoured by :func:`vietlott.config.prizes.get_actual_prize_for_draw`.
"""

from pathlib import Path
from typing import ClassVar

import polars as pl
from loguru import logger

from machine_learning.render_prediction_535 import Power535PredictionSummaryGenerator

# Project root for resolving the prize data file (matches
# ``vietlott.config.prizes.DATA_DIR`` – re-declared here to avoid
# importing private constants).
_PROJECT_ROOT: Path = Path(__file__).resolve().parents[2]
_DATA_DIR: Path = _PROJECT_ROOT / "data"
PRIZE_FILE: Path = _DATA_DIR / "power535_prizes.jsonl"


class Power535SpecialPredictionSummaryGenerator(Power535PredictionSummaryGenerator):
    """Power 5/35 prediction summary – only backtest draws with DD > 12B.

    Class attributes
    ----------------
    DD_THRESHOLD
        Minimum Độc Đắc value (VND) required for a draw to be included
        in the backtest.  Defaults to 12B per the official Vietlott
        rule.
    OUTPUT_NAME
        Markdown file name written to ``data/``.
    PRODUCT_DISPLAY
        Display name used in the generated markdown.
    """

    PRODUCT_NAME: ClassVar[str] = "power_535"
    TPD: ClassVar[int] = 2
    BEST_THRESHOLD: ClassVar[int] = 4
    OUTPUT_NAME: ClassVar[str] = "readme_535_special.md"
    PRODUCT_DISPLAY: ClassVar[str] = "Power 5/35 (Special: chỉ chơi khi Độc Đắc > 12B)"
    INCLUDES_SOLO_BASELINES: ClassVar[bool] = True
    INCLUDES_PATTERN_HYBRID: ClassVar[bool] = True
    HOT_SPECIALS_TOP_N: ClassVar[int] = 3

    # Trigger threshold for "interesting" draws.
    DD_THRESHOLD: ClassVar[int] = 12_000_000_000  # 12B VND

    def _load_lottery_data(self) -> pl.DataFrame:
        """Load lottery data, then keep only draws with Độc Đắc > threshold.

        Strategy:
          1. Load the full main dataset (date / id / result / …).
          2. Load ``power535_prizes.jsonl`` if present and extract
             ``(id, dd_value)`` for every record.  Draws without a prize
             record are kept (treated as "no info – include by default"
             so the special variant still has some data even when prize
             crawling is partial).
          3. Keep only rows whose ``dd_value`` exceeds
             :attr:`DD_THRESHOLD`.
          4. Log how many draws were filtered out.
        """
        df = super()._load_lottery_data()
        if df.is_empty():
            return df

        if not PRIZE_FILE.exists():
            logger.warning(
                f"{self.PRODUCT_DISPLAY}: prize file not found at {PRIZE_FILE}; "
                "running on the full dataset without DD filter."
            )
            return df

        prize_records: list[dict] = []
        with PRIZE_FILE.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                import json

                rec = json.loads(line)
                dd_value: int | None = None
                for p in rec.get("prizes", []):
                    if p.get("prize_name") == "Giải Độc Đắc":
                        raw = str(p.get("prize_value", "0")).replace(".", "")
                        try:
                            dd_value = int(raw) if raw else 0
                        except ValueError:
                            dd_value = 0
                        break
                if dd_value is not None:
                    prize_records.append({"id": str(rec.get("id")), "dd_value": dd_value})

        if not prize_records:
            logger.warning(
                f"{self.PRODUCT_DISPLAY}: no Độc Đắc records parsed; running on the full dataset without DD filter."
            )
            return df

        prize_df = pl.DataFrame(prize_records)
        joined = df.join(prize_df, on="id", how="left")
        # Rows with no prize record get dd_value = null; we keep them
        # (treated as "unknown – include by default") by filling with a
        # value > threshold.
        joined = joined.with_columns(pl.col("dd_value").fill_null(self.DD_THRESHOLD + 1))
        before = joined.height
        filtered = joined.filter(pl.col("dd_value") > self.DD_THRESHOLD)
        after = filtered.height
        logger.info(
            f"{self.PRODUCT_DISPLAY}: kept {after}/{before} draws with "
            f"Độc Đắc > {self.DD_THRESHOLD:,} VND ({before - after} skipped)."
        )
        return filtered


def main():
    """Main entry point for the Power 5/35 special prediction summary."""
    generator = Power535SpecialPredictionSummaryGenerator()
    generator.save_prediction_summary()
    logger.info("Power 5/35 (special) prediction summary generation completed successfully!")


if __name__ == "__main__":
    main()
