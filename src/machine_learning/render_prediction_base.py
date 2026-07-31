#!/usr/bin/env python
"""
Base class for Vietlott power-product prediction summary generators.

This module consolidates the previously copy-pasted logic shared by
``render_prediction_655.py``, ``render_prediction_645.py`` and
``render_prediction_535.py`` into a single configurable base class.

Subclasses set a handful of class attributes (``PRODUCT_NAME``,
``TPD``, ``BEST_THRESHOLD``, ...) and inherit all strategy construction,
backtest orchestration, ROI table, per-strategy report and markdown
assembly.

Side benefits
-------------
* Always calls ``PredictModel.apply_product_config`` on every strategy
  before backtest, fixing a bug where ``render_prediction_655.py`` was
  silently using default ``has_special=False`` and counting the special
  number as a main number.
* Always sets ``prize_fn`` from ``vietlott.config.prizes`` so the
  per-product prize table (including special-number tiers like
  ``(5, 1)`` for Power 6/55) is used during revenue calculation.
* Always passes explicit ``min_val`` / ``max_val`` to voter strategies
  so they don't rely on ``PredictModel.POWER_655_*`` defaults.
"""

from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from types import MethodType
from typing import ClassVar, Dict, List, Optional, Tuple

import pandas as pd
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
from vietlott.config.prizes import get_actual_prize_for_draw, get_prize_fn
from vietlott.config.products import get_config

# (strategy_name, tickets_per_day, model_instance) after backtest+evaluate
StrategyEntry = Tuple[str, int, PredictModel]


class BasePowerPredictionSummaryGenerator:
    """Common logic for power-product prediction summaries.

    Subclasses override the class attributes below to specialise for a
    specific Vietlott product.  No method overrides are required.
    """

    # ---- Subclass-overridable configuration ----
    PRODUCT_NAME: ClassVar[str] = "power_655"
    TPD: ClassVar[int] = 30
    BEST_THRESHOLD: ClassVar[int] = 5
    OUTPUT_NAME: ClassVar[str] = "readme_655.md"
    PRODUCT_DISPLAY: ClassVar[str] = "Power 6/55"
    INCLUDES_SOLO_BASELINES: ClassVar[bool] = False
    INCLUDES_PATTERN_HYBRID: ClassVar[bool] = False
    # When set, override ``predict_special`` on every strategy to return only the
    # top-N most frequent special numbers in the lookback window (per-draw),
    # instead of wheeling through all of them.  Used by Power 5/35 to buy 2×4
    # tickets/draw instead of 2×12.  ``None`` = leave the default behaviour.
    HOT_SPECIALS_TOP_N: ClassVar[Optional[int]] = None
    HOT_SPECIALS_LOOKBACK_DAYS: ClassVar[int] = 365

    def __init__(self):
        self.config = get_config(self.PRODUCT_NAME)
        self.min_val = self.config.min_value
        self.max_val = self.config.max_value
        self.number_predict = self.config.size_output
        self.prize_fn = get_prize_fn(self.PRODUCT_NAME)

    # ------------------------------------------------------------------
    # Data loading
    # ------------------------------------------------------------------

    def _load_lottery_data(self) -> pl.DataFrame:
        """Load and prepare lottery data for the configured product."""
        try:
            df = pl.read_ndjson(self.config.raw_path)

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
            logger.error(f"Error loading data for {self.PRODUCT_NAME}: {e}")
            return pl.DataFrame()

    # ------------------------------------------------------------------
    # Strategy construction
    # ------------------------------------------------------------------

    def _make_voter(self, strategy_cls, df_pd, tpd: int, **kwargs) -> PredictModel:
        """Instantiate a voter strategy with shared range + ticket count."""
        return strategy_cls(
            df_pd,
            time_predict=tpd,
            min_val=self.min_val,
            max_val=self.max_val,
            **kwargs,
        )

    def _build_strategy_defs(self, df_pd) -> List[Tuple[str, PredictModel]]:
        """Build the ordered list of ``(name, model)`` for this product.

        Always emits:
          * ``Steiner`` (solo or part of the solo-baselines block)
          * 7 ``Hybrid: Steiner + <voter>`` entries
          * 8 ``Inverse Hybrid: <voter> → Steiner`` entries

        Conditionally emits (controlled by class flags):
          * The 9 solo baseline voters (Random, LongAbsence, Pattern,
            Hot, Cold, NotRepeat, ExpDecay, PairFreq, Markov) when
            ``INCLUDES_SOLO_BASELINES`` is True.
          * ``Hybrid: Steiner + Pattern`` when ``INCLUDES_PATTERN_HYBRID``
            is True.
        """
        tpd = self.TPD
        steiner_strategy = SteinerStrategy(
            df_pd, time_predict=1, min_val=self.min_val, max_val=self.max_val, lookback_days=365
        )

        defs: List[Tuple[str, PredictModel]] = []

        if self.INCLUDES_SOLO_BASELINES:
            defs.extend(
                [
                    ("Random Strategy", RandomModel(df_pd, tpd, min_val=self.min_val, max_val=self.max_val)),
                    (
                        "Long Absence Strategy",
                        self._make_voter(LongAbsenceStrategy, df_pd, tpd, top_n=10),
                    ),
                    (
                        "Pattern Strategy",
                        self._make_voter(PatternStrategy, df_pd, tpd, lookback_days=180, pattern_weight=0.6),
                    ),
                    (
                        "Hot Numbers Strategy",
                        self._make_voter(HotNumbersStrategy, df_pd, tpd, lookback_days=365, selection_weight=0.7),
                    ),
                    (
                        "Cold Numbers Strategy",
                        self._make_voter(ColdNumbersStrategy, df_pd, tpd, lookback_days=365, selection_weight=0.7),
                    ),
                    (
                        "Not Repeat Strategy",
                        self._make_voter(NotRepeatStrategy, df_pd, tpd, lookback_days=30, avoid_weight=0.8),
                    ),
                    (
                        "Exponential Decay Strategy",
                        self._make_voter(
                            ExponentialDecayStrategy,
                            df_pd,
                            tpd,
                            half_life_days=90,
                            hot=True,
                            selection_weight=0.8,
                        ),
                    ),
                    (
                        "Pair Frequency Strategy",
                        self._make_voter(PairFrequencyStrategy, df_pd, tpd, lookback_days=365),
                    ),
                    (
                        "Markov Chain Strategy",
                        self._make_voter(MarkovChainStrategy, df_pd, tpd, lookback_days=365, smoothing=0.5),
                    ),
                    (
                        "Steiner Strategy",
                        self._make_voter(SteinerStrategy, df_pd, tpd, lookback_days=365),
                    ),
                ]
            )
        else:
            defs.append(("Steiner Strategy", self._make_voter(SteinerStrategy, df_pd, tpd, lookback_days=365)))

        defs.extend(
            [
                (
                    "Hybrid: Steiner + Pair Frequency",
                    HybridStrategy(
                        base=self._make_voter(PairFrequencyStrategy, df_pd, tpd, lookback_days=365),
                        steiner=steiner_strategy,
                        top_k=15,
                        time_predict=tpd,
                    ),
                ),
                (
                    "Hybrid: Steiner + Hot Numbers",
                    HybridStrategy(
                        base=self._make_voter(HotNumbersStrategy, df_pd, tpd, lookback_days=365, selection_weight=0.7),
                        steiner=steiner_strategy,
                        top_k=15,
                        time_predict=tpd,
                    ),
                ),
                (
                    "Hybrid: Steiner + Cold Numbers",
                    HybridStrategy(
                        base=self._make_voter(ColdNumbersStrategy, df_pd, tpd, lookback_days=365, selection_weight=0.7),
                        steiner=steiner_strategy,
                        top_k=15,
                        time_predict=tpd,
                    ),
                ),
                (
                    "Hybrid: Steiner + Long Absence",
                    HybridStrategy(
                        base=self._make_voter(LongAbsenceStrategy, df_pd, tpd, top_n=15),
                        steiner=steiner_strategy,
                        top_k=15,
                        time_predict=tpd,
                    ),
                ),
                (
                    "Hybrid: Steiner + Not Repeat",
                    HybridStrategy(
                        base=self._make_voter(NotRepeatStrategy, df_pd, tpd, lookback_days=30, avoid_weight=0.8),
                        steiner=steiner_strategy,
                        top_k=15,
                        time_predict=tpd,
                    ),
                ),
                (
                    "Hybrid: Steiner + Exponential Decay",
                    HybridStrategy(
                        base=self._make_voter(
                            ExponentialDecayStrategy,
                            df_pd,
                            tpd,
                            half_life_days=90,
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
                        base=self._make_voter(MarkovChainStrategy, df_pd, tpd, lookback_days=365, smoothing=0.5),
                        steiner=steiner_strategy,
                        top_k=15,
                        time_predict=tpd,
                    ),
                ),
            ]
        )

        if self.INCLUDES_PATTERN_HYBRID:
            defs.append(
                (
                    "Hybrid: Steiner + Pattern",
                    HybridStrategy(
                        base=self._make_voter(PatternStrategy, df_pd, tpd, lookback_days=180, pattern_weight=0.6),
                        steiner=steiner_strategy,
                        top_k=15,
                        time_predict=tpd,
                    ),
                )
            )

        defs.extend(
            [
                (
                    "Inverse Hybrid: Pair Frequency → Steiner (cov 3)",
                    InverseHybridStrategy(
                        proposer=self._make_voter(PairFrequencyStrategy, df_pd, tpd, lookback_days=365),
                        steiner=steiner_strategy,
                        top_k=15,
                        coverage=tpd,
                        time_predict=tpd,
                    ),
                ),
                (
                    "Inverse Hybrid: Hot Numbers → Steiner (cov 3)",
                    InverseHybridStrategy(
                        proposer=self._make_voter(
                            HotNumbersStrategy, df_pd, tpd, lookback_days=365, selection_weight=0.7
                        ),
                        steiner=steiner_strategy,
                        top_k=15,
                        coverage=tpd,
                        time_predict=tpd,
                    ),
                ),
                (
                    "Inverse Hybrid: Cold Numbers → Steiner (cov 3)",
                    InverseHybridStrategy(
                        proposer=self._make_voter(
                            ColdNumbersStrategy, df_pd, tpd, lookback_days=365, selection_weight=0.7
                        ),
                        steiner=steiner_strategy,
                        top_k=15,
                        coverage=tpd,
                        time_predict=tpd,
                    ),
                ),
                (
                    "Inverse Hybrid: Long Absence → Steiner (cov 3)",
                    InverseHybridStrategy(
                        proposer=self._make_voter(LongAbsenceStrategy, df_pd, tpd, top_n=15),
                        steiner=steiner_strategy,
                        top_k=15,
                        coverage=tpd,
                        time_predict=tpd,
                    ),
                ),
                (
                    "Inverse Hybrid: Not Repeat → Steiner (cov 3)",
                    InverseHybridStrategy(
                        proposer=self._make_voter(NotRepeatStrategy, df_pd, tpd, lookback_days=30, avoid_weight=0.8),
                        steiner=steiner_strategy,
                        top_k=15,
                        coverage=tpd,
                        time_predict=tpd,
                    ),
                ),
                (
                    "Inverse Hybrid: Exponential Decay → Steiner (cov 3)",
                    InverseHybridStrategy(
                        proposer=self._make_voter(
                            ExponentialDecayStrategy,
                            df_pd,
                            tpd,
                            half_life_days=90,
                            hot=True,
                            selection_weight=0.8,
                        ),
                        steiner=steiner_strategy,
                        top_k=15,
                        coverage=tpd,
                        time_predict=tpd,
                    ),
                ),
                (
                    "Inverse Hybrid: Markov Chain → Steiner (cov 3)",
                    InverseHybridStrategy(
                        proposer=self._make_voter(MarkovChainStrategy, df_pd, tpd, lookback_days=365, smoothing=0.5),
                        steiner=steiner_strategy,
                        top_k=15,
                        coverage=tpd,
                        time_predict=tpd,
                    ),
                ),
                (
                    "Inverse Hybrid: Pattern → Steiner (cov 3)",
                    InverseHybridStrategy(
                        proposer=self._make_voter(PatternStrategy, df_pd, tpd, lookback_days=180, pattern_weight=0.6),
                        steiner=steiner_strategy,
                        top_k=15,
                        coverage=tpd,
                        time_predict=tpd,
                    ),
                ),
            ]
        )

        return defs

    def _build_and_run_strategies(self, df_pd, date_from=None, date_to=None) -> List[StrategyEntry]:
        """Build, configure, backtest, and evaluate all strategies.

        Always calls ``apply_product_config`` and sets ``prize_fn`` so
        per-product special-number rules and prize tiers are honoured.
        """
        strategy_defs = self._build_strategy_defs(df_pd)
        tpd = self.TPD
        hot_top_n = self.HOT_SPECIALS_TOP_N
        apply_hot = hot_top_n is not None

        results: List[StrategyEntry] = []
        for name, model in strategy_defs:
            model.apply_product_config(self.config)
            model.prize_fn = self.prize_fn
            if apply_hot and model.special_pick_required:
                self._apply_hot_specials(model, hot_top_n, self.HOT_SPECIALS_LOOKBACK_DAYS)
            logger.info(f"Running {name} on {self.PRODUCT_DISPLAY}...")
            model.backtest(date_from=date_from, date_to=date_to)
            model.evaluate()
            results.append((name, tpd, model))

        return results

    def _apply_hot_specials(self, strategy: PredictModel, top_n: int, lookback_days: int) -> None:
        """Replace ``strategy.predict_special`` with a top-N hot-frequency picker.

        The replacement computes, for each ``target_date``, the frequency of
        every special number in the ``[target_date - lookback_days, target_date)``
        window, then returns the ``top_n`` specials with the highest counts
        (ties broken by ascending numeric value for determinism).  When the
        lookback window has no usable data, falls back to the full special
        range so the backtest still produces a row per draw.

        Result is cached per ``target_date`` because ``backtest`` calls
        ``predict_special`` once per row in ``self.df``.
        """
        cache: Dict = {}

        def _top_hot_specials(inner_self, target_date, candidate_pool=None):
            if target_date in cache:
                return cache[target_date]

            start_date = target_date - timedelta(days=lookback_days)
            mask = (strategy.df["date"] >= start_date) & (strategy.df["date"] < target_date)
            specials: List[int] = []
            for result in strategy.df.loc[mask, "result"].tolist():
                if hasattr(result, "__len__") and len(result) > strategy.special_position:
                    specials.append(int(result[strategy.special_position]))

            if not specials:
                # No lookback data yet — fall back to the full special range.
                fallback = list(range(strategy.special_min, strategy.special_max + 1))
                cache[target_date] = fallback
                return fallback

            counter = Counter(specials)
            # Sort by (-count, value) so ties resolve deterministically to the
            # smaller number.
            ranked = sorted(counter.items(), key=lambda kv: (-kv[1], kv[0]))
            chosen = sorted(n for n, _ in ranked[:top_n])
            cache[target_date] = chosen
            return chosen

        strategy.predict_special = MethodType(_top_hot_specials, strategy)

    # ------------------------------------------------------------------
    # ROI comparison table
    # ------------------------------------------------------------------

    def _roi_comparison_table(self, strategies: List[StrategyEntry]) -> str:
        """Generate ROI comparison table sorted best → worst."""
        rows = []
        for name, _tpd, model in strategies:
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

        return f"""## 📊 Strategy Performance Comparison ({self.PRODUCT_DISPLAY})

> Sorted by ROI (best → worst). All strategies backtested with **{self.TPD} tickets/draw**.

{chr(10).join(lines)}
"""

    # ------------------------------------------------------------------
    # Per-year breakdown
    # ------------------------------------------------------------------

    def _yearly_breakdown_table(self, model: PredictModel) -> str:
        """Render a per-year breakdown of cost / gain / profit / ROI.

        Each row aggregates one calendar year of backtest results so the
        reader can see which years the strategy was profitable.  A final
        ``Total`` row mirrors the :class:`Financial Summary` for easy
        cross-checking.

        Returns ``_No evaluation data available._`` when the model has
        not been backtested yet (or backtest produced no rows).
        """
        df_eval = model.df_backtest_evaluate
        df_backtest = model.df_backtest
        if df_eval is None or df_eval.empty or df_backtest is None or df_backtest.empty:
            return "_No evaluation data available.\n"

        # Per-row gain.  When ``draw_id`` is available in ``df_eval`` we
        # use ``get_actual_prize_for_draw`` so per-draw crawled prize
        # data (incl. the power_535 1/3-1/6 split + redistribution rule)
        # is honoured.  Otherwise we fall back to the hardcoded
        # ``prize_fn`` / ``prices`` table.
        _prize_fn_resolved = model.prize_fn
        _prices = model.prices
        _product_name = self.PRODUCT_NAME
        use_actual = "draw_id" in df_eval.columns and bool(_product_name)
        if use_actual:
            from vietlott.config.prizes import get_actual_prize_for_draw

            main_matches = df_eval["main_match"].astype(int)
            special_matches = df_eval["special_match"].astype(int)
            draw_ids = df_eval["draw_id"]
            gains = [
                int(
                    get_actual_prize_for_draw(
                        _product_name,
                        did,
                        int(m),
                        int(s),
                    )
                )
                for m, s, did in zip(main_matches, special_matches, draw_ids)
            ]
        else:
            main_matches = df_eval["main_match"].astype(int)
            special_matches = df_eval["special_match"].astype(int)

            def _prize_fallback(m, s):
                if _prize_fn_resolved is None:
                    return _prices.get(int(m), 0)
                return _prize_fn_resolved(int(m), int(s))

            gains = [int(_prize_fallback(int(m), int(s))) for m, s in zip(main_matches, special_matches)]

        # Per-year aggregation of predictions + gain
        eval_years = pd.to_datetime(df_eval["date"]).dt.year.to_numpy()
        yearly = (
            pd.DataFrame({"year": eval_years, "gain": gains})
            .groupby("year")
            .agg(
                predictions=("gain", "size"),
                gain=("gain", "sum"),
            )
        )

        # Draws per year from ``df_backtest`` (one row per draw).
        back_years = pd.to_datetime(df_backtest["date"]).dt.year
        draws_per_year = back_years.value_counts().to_dict()
        yearly["draws"] = yearly.index.map(lambda y: int(draws_per_year.get(int(y), 0)))

        # Cost and ROI
        ticket_price = int(model.ticket_price)
        yearly["cost"] = yearly["predictions"].astype(int) * ticket_price
        yearly["profit"] = yearly["gain"].astype(int) - yearly["cost"]
        yearly["roi"] = yearly.apply(
            lambda r: (r["profit"] / r["cost"] * 100) if r["cost"] > 0 else 0.0,
            axis=1,
        )

        # Build markdown
        lines = [
            "| Year | Draws | Predictions | Cost (VND) | Gain (VND) | Net Profit (VND) | ROI |",
            "|------|-------|-------------|------------|------------|------------------|-----|",
        ]
        total_d = total_p = total_c = total_g = 0
        for year in sorted(yearly.index):
            r = yearly.loc[year]
            d = int(r["draws"])
            p = int(r["predictions"])
            c = int(r["cost"])
            g = int(r["gain"])
            prof = g - c
            roi = float(r["roi"])
            lines.append(f"| {int(year)} | {d:,} | {p:,} | {c:,} | {g:,} | {prof:,} | {roi:.2f}% |")
            total_d += d
            total_p += p
            total_c += c
            total_g += g

        total_profit = total_g - total_c
        total_roi = (total_profit / total_c * 100) if total_c > 0 else 0.0
        lines.append(
            f"| **Total** | **{total_d:,}** | **{total_p:,}** | **{total_c:,}** | "
            f"**{total_g:,}** | **{total_profit:,}** | **{total_roi:.2f}%** |"
        )
        return "\n".join(lines) + "\n"

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
        """Generate detailed report for a single strategy."""
        df_eval = model.df_backtest_evaluate
        df_backtest = model.df_backtest
        if df_eval is None or df_eval.empty or df_backtest is None:
            return f"### {strategy_name}\n\n> No evaluation data available.\n"

        total_draws = len(df_backtest)
        total_predictions = len(df_eval)
        cost, gain, profit = model.revenue()

        s_correct = df_eval["correct_num"].apply(self._to_int).astype(int)
        match_counts = s_correct.value_counts().sort_index(ascending=False)
        match_distribution = "\n".join(
            [f"  - **{matches} matches**: {count:,} times" for matches, count in match_counts.items()]
        )

        mask = (s_correct >= self.BEST_THRESHOLD).to_numpy()
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
            df_best.to_markdown(index=False)
            if not df_best.empty
            else f"No results with {self.BEST_THRESHOLD}+ matches found."
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

#### 🗓 Yearly Breakdown
{self._yearly_breakdown_table(model)}

#### Match Distribution
{match_distribution}

#### Best Results ({self.BEST_THRESHOLD}+ matches)
{best_results_table}

"""

    # ------------------------------------------------------------------
    # Summary assembly
    # ------------------------------------------------------------------

    def generate_prediction_summary(self, date_from=None, date_to=None) -> str:
        """Generate the complete prediction summary content."""
        logger.info(f"Starting {self.PRODUCT_DISPLAY} prediction summary generation...")

        df = self._load_lottery_data()
        if df.is_empty():
            return "# Error\n\nNo data available.\n"

        df_pd = df.to_pandas()
        strategies = self._build_and_run_strategies(df_pd, date_from=date_from, date_to=date_to)

        roi_table = self._roi_comparison_table(strategies)
        reports = [self._generate_strategy_report(model, name, tpd) for name, tpd, model in strategies]

        return f"""# 🔮 Vietlott {self.PRODUCT_DISPLAY} Prediction Summary

> **Generated**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
>
> This document contains machine learning predictions and backtests for Vietlott {self.PRODUCT_DISPLAY} data.

{roi_table}

## 🔮 Prediction Models

{"".join(reports)}

---

## ⚠️ Disclaimer

This prediction summary is for educational and research purposes only. Lottery outcomes are random.
"""

    def save_prediction_summary(
        self,
        output_path: Optional[Path] = None,
        date_from=None,
        date_to=None,
    ) -> None:
        """Generate and save the prediction summary to a markdown file."""
        if output_path is None:
            output_path = Path(__file__).parent / self.OUTPUT_NAME

        try:
            summary_content = self.generate_prediction_summary(date_from=date_from, date_to=date_to)

            with output_path.open("w", encoding="utf-8") as ofile:
                ofile.write(summary_content)

            logger.info(f"{self.PRODUCT_DISPLAY} prediction summary written to {output_path.absolute()}")
        except Exception as e:
            logger.error(f"Error saving {self.PRODUCT_DISPLAY} prediction summary: {e}")
            raise
