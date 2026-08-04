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
from typing import ClassVar, Dict, List, Optional, Set, Tuple

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
from vietlott.config.prizes import get_prize_fn
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
    INVERSE_HYBRID_TOP_K: ClassVar[int] = 15
    # When set, override ``predict_special`` on every strategy to return only the
    # top-N most frequent special numbers in the lookback window (per-draw),
    # instead of wheeling through all of them.  Used by Power 5/35 to buy 2×4
    # tickets/draw instead of 2×12.  ``None`` = leave the default behaviour.
    SPECIALS_TOP_N: ClassVar[Optional[int]] = None
    SPECIALS_MODE: ClassVar[str] = "hot"  #  "hot", "cold", "long_absence", "markov_steiner", "intersection_la_mc"
    SPECIALS_LOOKBACK_DRAWS: ClassVar[int] = 60  # Số kỳ quay dùng làm cửa sổ quan sát lookback
    SPECIALS_OFFSET_DRAWS: ClassVar[int] = 0  # Số kỳ quay lùi lại (offset) trước target_date để bắt đầu khoảng lookback

    # ------------------------------------------------------------------
    # "Special" mode: chỉ mua vé khi jackpot > DD_THRESHOLD
    # ------------------------------------------------------------------
    # Each subclass sets its own ``DD_THRESHOLD`` (12B for 5/35, 70B for
    # 6/45, 200B for 6/55) and the ``JACKPOT_PRIZE_NAME`` used to look
    # up the current jackpot value in ``data/<product>_prizes.jsonl``.
    # Toggle ``DD_FILTER_ENABLED = True`` to restrict ticket purchases
    # to draws whose jackpot strictly exceeds the threshold – the
    # strategies, voters and lookback windows still see the full
    # historical dataset, so the learning step is unaffected.
    DD_FILTER_ENABLED: ClassVar[bool] = False
    DD_THRESHOLD: ClassVar[int] = 0
    DD_FILTER_OUTPUT_SUFFIX: ClassVar[str] = "_special"
    DD_FILTER_DISPLAY_SUFFIX: ClassVar[str] = " (Special: chỉ chơi khi jackpot vượt ngưỡng)"
    JACKPOT_PRIZE_NAME: ClassVar[str] = "Jackpot"

    def __init__(self):
        self.config = get_config(self.PRODUCT_NAME)
        self.min_val = self.config.min_value
        self.max_val = self.config.max_value
        self.number_predict = self.config.size_output
        self.prize_fn = get_prize_fn(self.PRODUCT_NAME)
        if self.DD_FILTER_ENABLED:
            base = self.OUTPUT_NAME.removesuffix(".md")
            self.OUTPUT_NAME = f"{base}{self.DD_FILTER_OUTPUT_SUFFIX}.md"
            self.PRODUCT_DISPLAY = f"{self.PRODUCT_DISPLAY}{self.DD_FILTER_DISPLAY_SUFFIX}"

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

        inv_top_k = self.INVERSE_HYBRID_TOP_K
        defs.extend(
            [
                (
                    "Inverse Hybrid: Pair Frequency → Steiner (cov 3)",
                    InverseHybridStrategy(
                        proposer=self._make_voter(PairFrequencyStrategy, df_pd, tpd, lookback_days=365),
                        steiner=steiner_strategy,
                        top_k=inv_top_k,
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
                        top_k=inv_top_k,
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
                        top_k=inv_top_k,
                        coverage=tpd,
                        time_predict=tpd,
                    ),
                ),
                (
                    "Inverse Hybrid: Long Absence → Steiner (cov 3)",
                    InverseHybridStrategy(
                        proposer=self._make_voter(LongAbsenceStrategy, df_pd, tpd, top_n=inv_top_k),
                        steiner=steiner_strategy,
                        top_k=inv_top_k,
                        coverage=tpd,
                        time_predict=tpd,
                    ),
                ),
                (
                    "Inverse Hybrid: Not Repeat → Steiner (cov 3)",
                    InverseHybridStrategy(
                        proposer=self._make_voter(NotRepeatStrategy, df_pd, tpd, lookback_days=30, avoid_weight=0.8),
                        steiner=steiner_strategy,
                        top_k=inv_top_k,
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
                        top_k=inv_top_k,
                        coverage=tpd,
                        time_predict=tpd,
                    ),
                ),
                (
                    "Inverse Hybrid: Markov Chain → Steiner (cov 3)",
                    InverseHybridStrategy(
                        proposer=self._make_voter(MarkovChainStrategy, df_pd, tpd, lookback_days=365, smoothing=0.5),
                        steiner=steiner_strategy,
                        top_k=inv_top_k,
                        coverage=tpd,
                        time_predict=tpd,
                    ),
                ),
                (
                    "Inverse Hybrid: Pattern → Steiner (cov 3)",
                    InverseHybridStrategy(
                        proposer=self._make_voter(PatternStrategy, df_pd, tpd, lookback_days=180, pattern_weight=0.6),
                        steiner=steiner_strategy,
                        top_k=inv_top_k,
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

        When :attr:`DD_FILTER_ENABLED` is ``True``, restricts every
        strategy's ``backtest`` call to the set of draws whose jackpot
        strictly exceeds :attr:`DD_THRESHOLD` via the ``draw_ids``
        argument on :meth:`PredictModel.backtest`.  The full ``df_pd``
        is still attached to every model so lookback / voter logic
        continues to use every historical draw.
        """
        strategy_defs = self._build_strategy_defs(df_pd)
        tpd = self.TPD
        specials_top_n = self.SPECIALS_TOP_N
        specials_mode = getattr(self, "SPECIALS_MODE", "hot")
        apply_specials = specials_top_n is not None

        eligible_ids: Set[str] | None = None
        if self.DD_FILTER_ENABLED:
            eligible_ids = self._load_eligible_draw_ids(pl.from_pandas(df_pd) if not df_pd.empty else pl.DataFrame())

        results: List[StrategyEntry] = []
        for name, model in strategy_defs:
            model.apply_product_config(self.config)
            model.prize_fn = self.prize_fn
            if apply_specials and model.special_pick_required:
                self._apply_frequency_specials(
                    model,
                    top_n=specials_top_n,
                    lookback_draws=getattr(self, "SPECIALS_LOOKBACK_DRAWS", 60),
                    offset_draws=getattr(self, "SPECIALS_OFFSET_DRAWS", 0),
                    mode=specials_mode,
                )
            logger.info(f"Running {name} on {self.PRODUCT_DISPLAY}...")
            model.backtest(
                date_from=date_from,
                date_to=date_to,
                draw_ids=eligible_ids,
            )
            model.evaluate()
            results.append((name, tpd, model))

        return results

    def _load_eligible_draw_ids(self, df: pl.DataFrame) -> Set[str] | None:
        """Return the set of draw ids whose jackpot > :attr:`DD_THRESHOLD`.

        Reads ``data/<PRODUCT_FILE_STEM>_prizes.jsonl`` and extracts
        the ``JACKPOT_PRIZE_NAME`` ``prize_value`` for every record,
        keeping draws whose value strictly exceeds
        :attr:`DD_THRESHOLD`.  Returns ``None`` (i.e. "all draws") when
        the prize file is missing or contains no jackpot records – this
        preserves the standard behaviour when prize data has not yet
        been crawled.

        Only consulted when :attr:`DD_FILTER_ENABLED` is ``True``.
        """
        # ``PRODUCT_NAME`` is the canonical "power_535" / "power_645" /
        # "power_655" key; the on-disk prize file uses the un-scored
        # form ("power535_prizes.jsonl", etc.).  Strip the underscore
        # before composing the path.
        file_stem = self.PRODUCT_NAME.replace("_", "")
        prize_file = Path(__file__).resolve().parents[2] / "data" / f"{file_stem}_prizes.jsonl"
        if not prize_file.exists():
            logger.warning(
                f"{self.PRODUCT_DISPLAY}: prize file not found at {prize_file}; running on all draws (no DD filter)."
            )
            return None

        import json

        eligible: Set[str] = set()
        with prize_file.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                rec = json.loads(line)
                jackpot_value: int = 0
                for p in rec.get("prizes", []):
                    if p.get("prize_name") == self.JACKPOT_PRIZE_NAME:
                        raw = str(p.get("prize_value", "0")).replace(".", "")
                        try:
                            jackpot_value = int(raw) if raw else 0
                        except ValueError:
                            jackpot_value = 0
                        break
                if jackpot_value > self.DD_THRESHOLD:
                    draw_id = rec.get("id")
                    if draw_id is not None:
                        eligible.add(str(draw_id))

        if not eligible:
            logger.warning(
                f"{self.PRODUCT_DISPLAY}: no draws with {self.JACKPOT_PRIZE_NAME} > "
                f"{self.DD_THRESHOLD:,} VND; running on all draws."
            )
            return None

        if not df.is_empty() and "id" in df.columns:
            df_ids = set(df["id"].cast(pl.String).to_list())
            if not (df_ids & eligible):
                logger.warning(
                    f"{self.PRODUCT_DISPLAY}: no dataset draw IDs match eligible jackpot draws; running on all draws."
                )
                return None

        total_draws = df.height
        logger.info(
            f"{self.PRODUCT_DISPLAY}: {len(eligible)}/{total_draws} draws have "
            f"{self.JACKPOT_PRIZE_NAME} > {self.DD_THRESHOLD:,} VND; backtest will only "
            f"generate tickets for these (lookback windows still see the full "
            f"{total_draws}-draw history)."
        )
        return eligible

    def _apply_frequency_specials(
        self,
        strategy: PredictModel,
        top_n: int,
        lookback_draws: int = 60,
        offset_draws: int = 0,
        mode: str = "hot",
    ) -> None:
        """Replace ``strategy.predict_special`` with a top-N frequency picker (hot or cold).

        Uses historical DRAWS (kỳ quay) gracefully adapting to available history,
        matching the behavior of main-number prediction strategies.
        """
        cache: Dict = {}

        def _top_frequency_specials(inner_self, target_date, candidate_pool=None):
            if target_date in cache:
                return cache[target_date]

            # Filter prior draws (strictly before target_date)
            prior_df = strategy.df[strategy.df["date"] < target_date]
            total_prior = len(prior_df)

            # Slice available window of draws
            # offset_draws = 0 means taking up to lookback_draws prior draws
            # offset_draws = N means skipping N most recent draws
            end_idx = max(0, total_prior - offset_draws)
            start_idx = max(0, end_idx - lookback_draws)
            window_df = prior_df.iloc[start_idx:end_idx]

            specials: List[int] = []
            if not window_df.empty:
                for result in window_df["result"].tolist():
                    if hasattr(result, "__len__") and len(result) > strategy.special_position:
                        specials.append(int(result[strategy.special_position]))

            # Fall back to full range sorted by number value when 0 historical draws exist
            all_specials = list(range(strategy.special_min, strategy.special_max + 1))
            if not specials:
                chosen = sorted(all_specials[:top_n])
                cache[target_date] = chosen
                return chosen

            # Ensure all possible special numbers are present in counts
            all_specials = range(strategy.special_min, strategy.special_max + 1)
            counter = Counter(specials)
            counts = {s: counter.get(s, 0) for s in all_specials}

            if mode == "cold":
                # Sort by (count ascending, value ascending)
                ranked = sorted(counts.items(), key=lambda kv: (kv[1], kv[0]))
            elif mode == "long_absence":
                # Sort by draws since last seen (longest absence first)
                last_seen_idx = {}
                for idx, result in enumerate(window_df["result"].tolist()):
                    if hasattr(result, "__len__") and len(result) > strategy.special_position:
                        sp = int(result[strategy.special_position])
                        last_seen_idx[sp] = idx
                absence_scores = {s: total_prior - last_seen_idx.get(s, -1) for s in all_specials}
                ranked = sorted(absence_scores.items(), key=lambda kv: (-kv[1], kv[0]))
            elif mode == "markov_steiner":
                # Pipeline: MarkovChain proposed top 8 -> Steiner filtered to top_n
                p8 = list(range(strategy.special_min, strategy.special_max + 1))
                specials_series = [
                    int(r[strategy.special_position])
                    for r in window_df["result"].tolist()
                    if hasattr(r, "__len__") and len(r) > strategy.special_position
                ]
                if len(specials_series) >= 2:
                    trans = {}
                    for i in range(len(specials_series) - 1):
                        prev, curr = specials_series[i], specials_series[i + 1]
                        trans.setdefault(prev, Counter())[curr] += 1
                    last_sp = specials_series[-1]
                    next_counts = trans.get(last_sp, Counter())
                    scores = {s: next_counts.get(s, 0) for s in all_specials}
                    ranked_mc = sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))
                    p8 = [n for n, _ in ranked_mc[:8]]
                # Filter p8 with Steiner system strategy
                from machine_learning.strategies import SteinerStrategy

                st_model = SteinerStrategy(strategy.df, min_val=strategy.special_min, max_val=strategy.special_max)
                if hasattr(st_model, "filter_pool"):
                    chosen = st_model.filter_pool(target_date, pool=p8, k=top_n)
                else:
                    chosen = sorted(p8[:top_n])
                cache[target_date] = chosen
                return chosen
            elif mode == "intersection_la_mc":
                # Intersection of Top 8 LongAbsence and Top 8 MarkovChain
                # 1. LongAbsence Top 8
                last_seen_idx = {}
                for idx, result in enumerate(window_df["result"].tolist()):
                    if hasattr(result, "__len__") and len(result) > strategy.special_position:
                        sp = int(result[strategy.special_position])
                        last_seen_idx[sp] = idx
                absence_scores = {s: total_prior - last_seen_idx.get(s, -1) for s in all_specials}
                top8_la = set(n for n, _ in sorted(absence_scores.items(), key=lambda kv: (-kv[1], kv[0]))[:8])

                # 2. MarkovChain Top 8
                specials_series = [
                    int(r[strategy.special_position])
                    for r in window_df["result"].tolist()
                    if hasattr(r, "__len__") and len(r) > strategy.special_position
                ]
                if len(specials_series) >= 2:
                    trans = {}
                    for i in range(len(specials_series) - 1):
                        prev, curr = specials_series[i], specials_series[i + 1]
                        trans.setdefault(prev, Counter())[curr] += 1
                    last_sp = specials_series[-1]
                    next_counts = trans.get(last_sp, Counter())
                    scores = {s: next_counts.get(s, 0) for s in all_specials}
                    top8_mc = set(n for n, _ in sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))[:8])
                else:
                    top8_mc = set(all_specials)

                # Intersection
                inter = sorted(list(top8_la & top8_mc))[:top_n]
                if not inter:
                    inter = sorted(list(top8_la))[:top_n]
                cache[target_date] = inter
                return inter
            else:  # "hot"
                # Sort by (count descending, value ascending)
                ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))

            chosen = sorted(n for n, _ in ranked[:top_n])
            cache[target_date] = chosen
            return chosen

        strategy.predict_special = MethodType(_top_frequency_specials, strategy)

    def _apply_hot_specials(self, strategy: PredictModel, top_n: int, lookback_days: int) -> None:
        """Backward-compatibility wrapper for _apply_frequency_specials(..., mode='hot')."""
        self._apply_frequency_specials(strategy, top_n, lookback_days, mode="hot")

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
        match_lines = [f"  - **{matches} matches**: {count:,} times" for matches, count in match_counts.items()]
        if "special_match" in df_eval.columns and model.special_pick_required:
            special_hits = (df_eval["special_match"].astype(int) > 0).sum()
            match_lines.append(f"  - **Special number match**: {special_hits:,} times")
        match_distribution = "\n".join(match_lines)

        mask = (s_correct >= self.BEST_THRESHOLD).to_numpy()
        df_best = df_eval.loc[
            mask, ["date", "result", "predicted", "predicted_special", "special_match", "correct_num"]
        ].copy()

        # Calculate prize gain for each winning prediction
        product = model.product_name or ""
        use_actual = bool(product) and "draw_id" in df_eval.columns
        if use_actual:
            from vietlott.config.prizes import get_actual_prize_for_draw

            df_best_draw_ids = df_eval.loc[mask, "draw_id"].tolist()
            gains = [
                int(get_actual_prize_for_draw(product, did, int(m), int(s)))
                for m, s, did in zip(
                    df_eval.loc[mask, PredictModel.col_main_match],
                    df_eval.loc[mask, PredictModel.col_special_match],
                    df_best_draw_ids,
                )
            ]
        else:
            gains = [
                model._prize_for(int(m), int(s))
                for m, s in zip(
                    df_eval.loc[mask, PredictModel.col_main_match],
                    df_eval.loc[mask, PredictModel.col_special_match],
                )
            ]
        df_best["gain"] = [f"{g:,} VND" for g in gains]

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
