#!/usr/bin/env python
"""
Prediction Summary Generator for Vietlott Power 5/35 Data.

This script generates a prediction summary markdown file (readme_535.md) for Power 5/35.
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
    InverseHybridStrategy,
    LongAbsenceStrategy,
    MarkovChainStrategy,
    NotRepeatStrategy,
    PairFrequencyStrategy,
    PatternStrategy,
    RandomModel,
    SteinerStrategy,
)
from machine_learning.strategies.base import PredictModel
from vietlott.config.products import get_config

_StrategyEntry = Tuple[str, int, PredictModel]


from vietlott.config.prizes import _prize_for_power_535


class Power535PredictionSummaryGenerator:
    """Generator for Power 5/35 prediction summary."""

    def __init__(self):
        self.config = get_config("power_535")
        self.min_val = self.config.min_value
        self.max_val = self.config.max_value
        self.number_predict = self.config.size_output

    def _load_lottery_data(self) -> pl.DataFrame:
        """Load and prepare Power 5/35 data."""
        try:
            config = get_config("power_535")
            df = pl.read_ndjson(config.raw_path)

            if "date" in df.columns:
                try:
                    if df["date"].dtype in [pl.Date, pl.Datetime]:
                        df = df.with_columns(pl.col("date").cast(pl.Date))
                    else:
                        df = df.with_columns(pl.col("date").str.to_date(strict=False))
                except Exception as e:
                    logger.warning(f"Could not parse date column: {e}")
                    df = df.with_columns(pl.col("date").str.to_date(strict=False))

            df = df.sort(["date", "id"], descending=True)
            return df
        except Exception as e:
            logger.error(f"Error loading data for power_535: {e}")
            return pl.DataFrame()

    def _build_and_run_strategies(self, df_pd, date_from=None, date_to=None) -> List[_StrategyEntry]:
        """Instantiate, backtest, and evaluate all strategies for Power 5/35."""
        tpd = 2  # 2 mains × 12 specials = 24 tickets / draw
        config = self.config

        steiner_strategy = SteinerStrategy(
            df_pd, time_predict=1, min_val=self.min_val, max_val=self.max_val, lookback_days=365
        )

        strategy_defs = [
            ("Random Strategy", RandomModel(df_pd, tpd, min_val=self.min_val, max_val=self.max_val)),
            (
                "Long Absence Strategy",
                LongAbsenceStrategy(df_pd, time_predict=tpd, min_val=self.min_val, max_val=self.max_val, top_n=10),
            ),
            (
                "Pattern Strategy",
                PatternStrategy(
                    df_pd,
                    time_predict=tpd,
                    min_val=self.min_val,
                    max_val=self.max_val,
                    lookback_days=180,
                    pattern_weight=0.6,
                ),
            ),
            (
                "Hot Numbers Strategy",
                HotNumbersStrategy(
                    df_pd,
                    time_predict=tpd,
                    min_val=self.min_val,
                    max_val=self.max_val,
                    lookback_days=365,
                    selection_weight=0.7,
                ),
            ),
            (
                "Cold Numbers Strategy",
                ColdNumbersStrategy(
                    df_pd,
                    time_predict=tpd,
                    min_val=self.min_val,
                    max_val=self.max_val,
                    lookback_days=365,
                    selection_weight=0.7,
                ),
            ),
            (
                "Not Repeat Strategy",
                NotRepeatStrategy(
                    df_pd,
                    time_predict=tpd,
                    min_val=self.min_val,
                    max_val=self.max_val,
                    lookback_days=30,
                    avoid_weight=0.8,
                ),
            ),
            (
                "Exponential Decay Strategy",
                ExponentialDecayStrategy(
                    df_pd,
                    time_predict=tpd,
                    min_val=self.min_val,
                    max_val=self.max_val,
                    half_life_days=90,
                    hot=True,
                    selection_weight=0.8,
                ),
            ),
            (
                "Pair Frequency Strategy",
                PairFrequencyStrategy(
                    df_pd, time_predict=tpd, min_val=self.min_val, max_val=self.max_val, lookback_days=365
                ),
            ),
            (
                "Markov Chain Strategy",
                MarkovChainStrategy(
                    df_pd,
                    time_predict=tpd,
                    min_val=self.min_val,
                    max_val=self.max_val,
                    lookback_days=365,
                    smoothing=0.5,
                ),
            ),
            (
                "Steiner Strategy",
                SteinerStrategy(
                    df_pd,
                    time_predict=tpd,
                    min_val=self.min_val,
                    max_val=self.max_val,
                    lookback_days=365,
                ),
            ),
            (
                "Hybrid: Steiner + Pair Frequency",
                HybridStrategy(
                    base=PairFrequencyStrategy(
                        df_pd, time_predict=tpd, min_val=self.min_val, max_val=self.max_val, lookback_days=365
                    ),
                    steiner=steiner_strategy,
                    top_k=15,
                    time_predict=tpd,
                ),
            ),
            (
                "Hybrid: Steiner + Hot Numbers",
                HybridStrategy(
                    base=HotNumbersStrategy(
                        df_pd,
                        time_predict=tpd,
                        min_val=self.min_val,
                        max_val=self.max_val,
                        lookback_days=365,
                        selection_weight=0.7,
                    ),
                    steiner=steiner_strategy,
                    top_k=15,
                    time_predict=tpd,
                ),
            ),
            (
                "Hybrid: Steiner + Cold Numbers",
                HybridStrategy(
                    base=ColdNumbersStrategy(
                        df_pd,
                        time_predict=tpd,
                        min_val=self.min_val,
                        max_val=self.max_val,
                        lookback_days=365,
                        selection_weight=0.7,
                    ),
                    steiner=steiner_strategy,
                    top_k=15,
                    time_predict=tpd,
                ),
            ),
            (
                "Hybrid: Steiner + Long Absence",
                HybridStrategy(
                    base=LongAbsenceStrategy(
                        df_pd, time_predict=tpd, min_val=self.min_val, max_val=self.max_val, top_n=15
                    ),
                    steiner=steiner_strategy,
                    top_k=15,
                    time_predict=tpd,
                ),
            ),
            (
                "Hybrid: Steiner + Not Repeat",
                HybridStrategy(
                    base=NotRepeatStrategy(
                        df_pd,
                        time_predict=tpd,
                        min_val=self.min_val,
                        max_val=self.max_val,
                        lookback_days=30,
                        avoid_weight=0.8,
                    ),
                    steiner=steiner_strategy,
                    top_k=15,
                    time_predict=tpd,
                ),
            ),
            (
                "Hybrid: Steiner + Exponential Decay",
                HybridStrategy(
                    base=ExponentialDecayStrategy(
                        df_pd,
                        time_predict=tpd,
                        half_life_days=90,
                        min_val=self.min_val,
                        max_val=self.max_val,
                        hot=True,
                        selection_weight=0.8,
                    ),
                    steiner=steiner_strategy,
                    top_k=15,
                    time_predict=tpd,
                ),
            ),
            (
                "Hybrid: Steiner + Markov Chain",
                HybridStrategy(
                    base=MarkovChainStrategy(
                        df_pd,
                        time_predict=tpd,
                        min_val=self.min_val,
                        max_val=self.max_val,
                        lookback_days=365,
                        smoothing=0.5,
                    ),
                    steiner=steiner_strategy,
                    top_k=15,
                    time_predict=tpd,
                ),
            ),
            (
                "Inverse Hybrid: Pair Frequency → Steiner (cov 3)",
                InverseHybridStrategy(
                    proposer=PairFrequencyStrategy(
                        df_pd, time_predict=tpd, min_val=self.min_val, max_val=self.max_val, lookback_days=365
                    ),
                    steiner=steiner_strategy,
                    top_k=15,
                    coverage=3,
                    time_predict=tpd,
                ),
            ),
            (
                "Inverse Hybrid: Hot Numbers → Steiner (cov 3)",
                InverseHybridStrategy(
                    proposer=HotNumbersStrategy(
                        df_pd,
                        time_predict=tpd,
                        min_val=self.min_val,
                        max_val=self.max_val,
                        lookback_days=365,
                        selection_weight=0.7,
                    ),
                    steiner=steiner_strategy,
                    top_k=15,
                    coverage=3,
                    time_predict=tpd,
                ),
            ),
            (
                "Inverse Hybrid: Cold Numbers → Steiner (cov 3)",
                InverseHybridStrategy(
                    proposer=ColdNumbersStrategy(
                        df_pd,
                        time_predict=tpd,
                        min_val=self.min_val,
                        max_val=self.max_val,
                        lookback_days=365,
                        selection_weight=0.7,
                    ),
                    steiner=steiner_strategy,
                    top_k=15,
                    coverage=3,
                    time_predict=tpd,
                ),
            ),
            (
                "Inverse Hybrid: Long Absence → Steiner (cov 3)",
                InverseHybridStrategy(
                    proposer=LongAbsenceStrategy(
                        df_pd, time_predict=tpd, min_val=self.min_val, max_val=self.max_val, top_n=15
                    ),
                    steiner=steiner_strategy,
                    top_k=15,
                    coverage=3,
                    time_predict=tpd,
                ),
            ),
            (
                "Inverse Hybrid: Not Repeat → Steiner (cov 3)",
                InverseHybridStrategy(
                    proposer=NotRepeatStrategy(
                        df_pd,
                        time_predict=tpd,
                        min_val=self.min_val,
                        max_val=self.max_val,
                        lookback_days=30,
                        avoid_weight=0.8,
                    ),
                    steiner=steiner_strategy,
                    top_k=15,
                    coverage=3,
                    time_predict=tpd,
                ),
            ),
            (
                "Inverse Hybrid: Exponential Decay → Steiner (cov 3)",
                InverseHybridStrategy(
                    proposer=ExponentialDecayStrategy(
                        df_pd,
                        time_predict=tpd,
                        half_life_days=90,
                        min_val=self.min_val,
                        max_val=self.max_val,
                        hot=True,
                        selection_weight=0.8,
                    ),
                    steiner=steiner_strategy,
                    top_k=15,
                    coverage=3,
                    time_predict=tpd,
                ),
            ),
            (
                "Inverse Hybrid: Markov Chain → Steiner (cov 3)",
                InverseHybridStrategy(
                    proposer=MarkovChainStrategy(
                        df_pd,
                        time_predict=tpd,
                        min_val=self.min_val,
                        max_val=self.max_val,
                        lookback_days=365,
                        smoothing=0.5,
                    ),
                    steiner=steiner_strategy,
                    top_k=15,
                    coverage=3,
                    time_predict=tpd,
                ),
            ),
            (
                "Inverse Hybrid: Pattern → Steiner (cov 3)",
                InverseHybridStrategy(
                    proposer=PatternStrategy(
                        df_pd,
                        time_predict=tpd,
                        min_val=self.min_val,
                        max_val=self.max_val,
                        lookback_days=180,
                        pattern_weight=0.6,
                    ),
                    steiner=steiner_strategy,
                    top_k=15,
                    coverage=3,
                    time_predict=tpd,
                ),
            ),
        ]

        results: List[_StrategyEntry] = []
        for name, model in strategy_defs:
            model.apply_product_config(config)
            model.prize_fn = _prize_for_power_535
            logger.info(f"Running {name} on Power 5/35...")
            model.backtest(date_from=date_from, date_to=date_to)
            model.evaluate()
            results.append((name, tpd, model))

        return results

    def _roi_comparison_table(self, strategies: List[_StrategyEntry]) -> str:
        """Generate ROI comparison table."""
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

        return f"""## 📊 Strategy Performance Comparison (Power 5/35)

> Sorted by ROI (best → worst). All strategies backtested with **30 tickets/draw**.

{chr(10).join(lines)}
"""

    def _to_int(self, v) -> int:
        try:
            return int(v)
        except Exception:
            try:
                return len(v)
            except Exception:
                return 0

    def _generate_strategy_report(self, model: PredictModel, strategy_name: str, tickets_per_day: int) -> str:
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

        mask = (s_correct >= 4).to_numpy()
        df_best = df_eval.loc[
            mask, ["date", "result", "predicted", "predicted_special", "special_match", "correct_num"]
        ].copy()
        df_best["result"] = df_best["result"].apply(
            lambda x: str([int(i) for i in x]) if hasattr(x, "__iter__") else str(x)
        )
        df_best["predicted"] = df_best["predicted"].apply(
            lambda x: str([int(i) for i in x]) if hasattr(x, "__iter__") else str(x)
        )
        df_best["correct_num"] = df_best["correct_num"].apply(self._to_int)

        best_results_table = (
            df_best.to_markdown(index=False) if not df_best.empty else "No results with 4+ matches found."
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

#### Best Results (4+ matches)
{best_results_table}

"""

    def generate_prediction_summary(self, date_from=None, date_to=None) -> str:
        logger.info("Starting Power 5/35 prediction summary generation...")

        df_power535 = self._load_lottery_data()
        if df_power535.is_empty():
            return "# Error\n\nNo data available.\n"

        df_pd = df_power535.to_pandas()
        strategies = self._build_and_run_strategies(df_pd, date_from=date_from, date_to=date_to)

        roi_table = self._roi_comparison_table(strategies)
        reports = [self._generate_strategy_report(model, name, tpd) for name, tpd, model in strategies]

        return f"""# 🔮 Vietlott Power 5/35 Prediction Summary

> **Generated**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
>
> This document contains machine learning predictions and backtests for Vietlott Power 5/35 data.

{roi_table}

## 🔮 Prediction Models

{"".join(reports)}

---

## ⚠️ Disclaimer

This prediction summary is for educational and research purposes only. Lottery outcomes are random.
"""

    def save_prediction_summary(self, output_path: Optional[Path] = None, date_from=None, date_to=None) -> None:
        if output_path is None:
            output_path = Path(__file__).parent / "readme_535.md"

        summary_content = self.generate_prediction_summary(date_from=date_from, date_to=date_to)

        with output_path.open("w", encoding="utf-8") as ofile:
            ofile.write(summary_content)

        logger.info(f"Power 5/35 prediction summary written to {output_path.absolute()}")


def main():
    generator = Power535PredictionSummaryGenerator()
    generator.save_prediction_summary()


if __name__ == "__main__":
    main()
