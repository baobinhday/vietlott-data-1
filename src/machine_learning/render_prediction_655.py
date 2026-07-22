#!/usr/bin/env python
"""
Prediction Summary Generator for Hybrid Strategies (Power 6/55).

This script generates a prediction summary markdown file (readme_655.md)
comparing all hybrid (Steiner + voter) strategies against one another.
"""

from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

import polars as pl
from loguru import logger

from machine_learning.strategies import (
    ColdNumbersStrategy,
    ExponentialDecayStrategy,
    HotNumbersStrategy,
    HybridStrategy,
    LongAbsenceStrategy,
    MarkovChainStrategy,
    NotRepeatStrategy,
    PairFrequencyStrategy,
    SteinerStrategy,
)
from machine_learning.strategies.base import PredictModel
from vietlott.config.products import get_config

# (strategy_name, tickets_per_day, model_instance) after backtest+evaluate
_StrategyEntry = Tuple[str, int, PredictModel]


class HybridPredictionSummaryGenerator:
    """Generator for hybrid prediction summary (Power 6/55)."""

    def __init__(self):
        pass

    # ------------------------------------------------------------------
    # Data loading
    # ------------------------------------------------------------------

    def _load_lottery_data(self, product: str) -> pl.DataFrame:
        """Load and prepare lottery data for predictions."""
        try:
            df = pl.read_ndjson(get_config(product).raw_path)

            if "date" in df.columns:
                try:
                    if df["date"].dtype in [pl.Date, pl.Datetime]:
                        df = df.with_columns(pl.col("date").cast(pl.Date))
                    elif df["date"].dtype in [pl.Int64, pl.Int32, pl.Float64]:
                        max_val = df["date"].max()
                        if max_val > 1_000_000_000_000:
                            df = df.with_columns(
                                (pl.col("date").cast(pl.Int64) / 1000).cast(pl.Datetime("ms")).cast(pl.Date)
                            )
                        else:
                            df = df.with_columns(pl.col("date").cast(pl.Int64).cast(pl.Datetime("s")).cast(pl.Date))
                    else:
                        df = df.with_columns(pl.col("date").str.to_date(strict=False))
                except Exception as e:
                    logger.warning(f"Could not parse date column: {e}")
                    df = df.with_columns(pl.col("date").str.to_date(strict=False))

            df = df.sort(["date", "id"], descending=True)
            return df
        except Exception as e:
            logger.error(f"Error loading data for {product}: {e}")
            return pl.DataFrame()

    # ------------------------------------------------------------------
    # Strategy runner
    # ------------------------------------------------------------------

    def _build_and_run_strategies(self, df_pd, date_from=None, date_to=None) -> List[_StrategyEntry]:
        """
        Instantiate, backtest, and evaluate all hybrid strategies.

        Parameters
        ----------
        df_pd:
            Full historical data as a pandas DataFrame.
        date_from:
            Optional start date (inclusive) for the backtest period.
        date_to:
            Optional end date (inclusive) for the backtest period.

        Returns a list of ``(name, tickets_per_day, model)`` tuples where
        each model has already been backtested and evaluated.
        """
        tpd = 30  # tickets per day for all strategies

        # Build shared Steiner + voter instances (reused across hybrids)
        steiner_strategy = SteinerStrategy(df_pd, time_predict=1, lookback_days=365)

        strategy_defs = [
            (
                "Steiner Strategy",
                SteinerStrategy(
                    df_pd,
                    time_predict=tpd,
                    lookback_days=365,
                ),
            ),
            (
                "Hybrid: Steiner + Pair Frequency",
                HybridStrategy(
                    base=PairFrequencyStrategy(df_pd, time_predict=tpd, lookback_days=365),
                    steiner=steiner_strategy,
                    top_k=15,
                    time_predict=tpd,
                ),
            ),
            (
                "Hybrid: Steiner + Hot Numbers",
                HybridStrategy(
                    base=HotNumbersStrategy(df_pd, time_predict=tpd, lookback_days=365, selection_weight=0.7),
                    steiner=steiner_strategy,
                    top_k=15,
                    time_predict=tpd,
                ),
            ),
            (
                "Hybrid: Steiner + Cold Numbers",
                HybridStrategy(
                    base=ColdNumbersStrategy(df_pd, time_predict=tpd, lookback_days=365, selection_weight=0.7),
                    steiner=steiner_strategy,
                    top_k=15,
                    time_predict=tpd,
                ),
            ),
            (
                "Hybrid: Steiner + Long Absence",
                HybridStrategy(
                    base=LongAbsenceStrategy(df_pd, time_predict=tpd, top_n=15),
                    steiner=steiner_strategy,
                    top_k=15,
                    time_predict=tpd,
                ),
            ),
            (
                "Hybrid: Steiner + Not Repeat",
                HybridStrategy(
                    base=NotRepeatStrategy(df_pd, time_predict=tpd, lookback_days=30, avoid_weight=0.8),
                    steiner=steiner_strategy,
                    top_k=15,
                    time_predict=tpd,
                ),
            ),
            (
                "Hybrid: Steiner + Exponential Decay",
                HybridStrategy(
                    base=ExponentialDecayStrategy(
                        df_pd, time_predict=tpd, half_life_days=90, hot=True, selection_weight=0.8
                    ),
                    steiner=steiner_strategy,
                    top_k=15,
                    time_predict=tpd,
                ),
            ),
            (
                "Hybrid: Steiner + Markov Chain",
                HybridStrategy(
                    base=MarkovChainStrategy(df_pd, time_predict=tpd, lookback_days=365, smoothing=0.5),
                    steiner=steiner_strategy,
                    top_k=15,
                    time_predict=tpd,
                ),
            ),
        ]

        results: List[_StrategyEntry] = []
        for name, model in strategy_defs:
            logger.info(f"Running {name}...")
            model.backtest(date_from=date_from, date_to=date_to)
            model.evaluate()
            results.append((name, tpd, model))

        return results

    # ------------------------------------------------------------------
    # ROI comparison table (header)
    # ------------------------------------------------------------------

    def _roi_comparison_table(self, strategies: List[_StrategyEntry]) -> str:
        """Generate a ROI comparison table sorted best → worst."""
        rows = []
        for name, tpd, model in strategies:
            cost, gain, profit = model.revenue()
            roi = (profit / cost * 100) if cost > 0 else 0.0
            rows.append((name, cost, gain, profit, roi))

        rows.sort(key=lambda x: x[4], reverse=True)

        medals = ["🥇", "🥈", "🥉"] + ["  "] * len(rows)
        header = "| Rank | Strategy | Total Cost (VND) | Total Gain (VND) | Net Profit (VND) | ROI |"
        sep = "|------|----------|-----------------|-----------------|-----------------|-----|"
        lines = [header, sep]
        for i, (name, cost, gain, profit, roi) in enumerate(rows):
            lines.append(f"| {medals[i]} {i + 1} | {name} | {cost:,} | {gain:,} | {profit:,} | {roi:.2f}% |")

        return f"""## 📊 Hybrid Strategy Performance Comparison

> Sorted by ROI (best → worst).  All strategies backtested with **{strategies[0][1]} tickets/draw**.
> Each hybrid uses Steiner as proposer (top-15 number pool) and a voter
> strategy is invoked with ``candidate_pool`` set to that pool.

{chr(10).join(lines)}
"""

    # ------------------------------------------------------------------
    # Per-strategy detailed report
    # ------------------------------------------------------------------

    def _to_int(self, v) -> int:
        """Convert value to integer safely."""
        try:
            return int(v)
        except Exception:
            try:
                return len(v)
            except Exception:
                return 0

    def _generate_strategy_report(self, model: PredictModel, strategy_name: str, tickets_per_day: int) -> str:
        """Generate detailed report for a single hybrid strategy."""
        df_eval = model.df_backtest_evaluate
        if df_eval is None or df_eval.empty:
            return f"### {strategy_name}\n\n> No evaluation data available.\n"

        total_draws = len(model.df_backtest)
        total_predictions = len(df_eval)
        cost, gain, profit = model.revenue()

        s_correct = df_eval["correct_num"].apply(self._to_int).astype(int)
        match_counts = s_correct.value_counts().sort_index(ascending=False)
        match_distribution = "\n".join(
            [f"  - **{matches} matches**: {count:,} times" for matches, count in match_counts.items()]
        )

        mask = (s_correct >= 5).to_numpy()
        df_best = df_eval.loc[mask, ["date", "result", "predicted", "predicted_special", "special_match", "correct_num"]].copy()
        df_best["result"] = df_best["result"].apply(
            lambda x: str([int(i) for i in x]) if hasattr(x, "__iter__") else str(x)
        )
        df_best["predicted"] = df_best["predicted"].apply(
            lambda x: str([int(i) for i in x]) if hasattr(x, "__iter__") else str(x)
        )
        df_best["correct_num"] = df_best["correct_num"].apply(self._to_int)

        best_results_table = (
            df_best.to_markdown(index=False) if not df_best.empty else "No results with 5+ matches found."
        )

        date_min = df_eval["date"].min()
        date_max = df_eval["date"].max()

        return f"""### 🎲 {strategy_name}

#### Configuration
| Parameter | Value |
|-----------|-------|
| Strategy | {strategy_name} |
| Tickets per day | {tickets_per_day} |
| Ticket price | {model.ticket_price:,} VND |
| Number range | {model.min_val} - {model.max_val} |
| Numbers to pick | {model.number_predict} |

#### Backtest Period
| Metric | Value |
|--------|-------|
| Start date | {date_min} |
| End date | {date_max} |
| Total draws | {total_draws:,} |
| Total predictions | {total_predictions:,} |

#### Financial Summary
| Metric | Value |
|--------|-------|
| Total cost | {cost:,} VND |
| Total gain | {gain:,} VND |
| Net profit/loss | {profit:,} VND |
| ROI | {(profit / cost * 100) if cost > 0 else 0:.2f}% |

#### Match Distribution
{match_distribution}

#### Best Results (5+ matches)
{best_results_table}

"""

    def _generate_predictions_section(self, strategies: List[_StrategyEntry]) -> str:
        """Generate per-strategy detailed reports from pre-run strategy list."""
        reports = [self._generate_strategy_report(model, name, tpd) for name, tpd, model in strategies]
        return f"""## 🔮 Hybrid Prediction Models

> ⚠️ **Disclaimer**: These are experimental models for educational purposes only. Lottery outcomes are random and cannot be predicted reliably.

{"".join(reports)}
"""

    # ------------------------------------------------------------------
    # Summary assembly
    # ------------------------------------------------------------------

    def generate_prediction_summary(self, date_from=None, date_to=None) -> str:
        """
        Generate the complete hybrid prediction summary content.

        Parameters
        ----------
        date_from:
            Optional start date (inclusive) for the backtest period.
        date_to:
            Optional end date (inclusive) for the backtest period.
        """
        logger.info("Starting hybrid prediction summary generation...")

        df_power655 = self._load_lottery_data("power_655")
        if df_power655.is_empty():
            return "# Error\n\nNo data available.\n"

        df_pd = df_power655.to_pandas()
        strategies = self._build_and_run_strategies(df_pd, date_from=date_from, date_to=date_to)

        roi_table = self._roi_comparison_table(strategies)
        predictions = self._generate_predictions_section(strategies)

        return f"""# 🔮 Vietlott Power 655 Hybrid Prediction Summary

> **Generated**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
>
> This document compares **hybrid** strategies where Steiner proposes top-K
> candidate tickets (each = 2 disjoint Steiner triples) and a voter strategy
> re-scores them via its native signal.
>
> This is an experimental module for educational purposes only.

{roi_table}

{predictions}

---

## ⚠️ Disclaimer

This prediction summary is for educational and research purposes only. Lottery outcomes are random and cannot be reliably predicted. Never gamble more than you can afford to lose.
"""

    def save_prediction_summary(self, output_path: Optional[Path] = None, date_from=None, date_to=None) -> None:
        """Generate and save hybrid prediction summary to file.

        Parameters
        ----------
        output_path:
            Destination file path.  Defaults to ``<this directory>/readme_655.md``.
        date_from:
            Optional start date (inclusive) for the backtest period.
        date_to:
            Optional end date (inclusive) for the backtest period.
        """
        if output_path is None:
            output_path = Path(__file__).parent / "readme_655.md"

        try:
            summary_content = self.generate_prediction_summary(date_from=date_from, date_to=date_to)

            with output_path.open("w", encoding="utf-8") as ofile:
                ofile.write(summary_content)

            logger.info(f"Hybrid prediction summary successfully written to {output_path.absolute()}")
        except Exception as e:
            logger.error(f"Error saving hybrid prediction summary: {e}")
            raise


def main():
    """Main entry point for hybrid prediction summary generation."""
    try:
        generator = HybridPredictionSummaryGenerator()
        generator.save_prediction_summary()
        logger.info("Hybrid prediction summary generation completed successfully!")
    except Exception as e:
        logger.error(f"Failed to generate hybrid prediction summary: {e}")
        raise


if __name__ == "__main__":
    main()
