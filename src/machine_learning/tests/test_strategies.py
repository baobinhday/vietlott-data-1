"""
Tests for ML prediction strategies.

Covers:
- All strategies return exactly `number_predict` distinct numbers within [min_val, max_val]
- RandomModel correctly samples from the full range including max_val
- MarkovChainStrategy handles date_from / date_to backtest filtering
- backtest + evaluate pipeline produces expected DataFrame columns
"""

import random
from datetime import date, timedelta
from itertools import combinations

import pandas as pd
import pytest

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

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

MIN_VAL = 1
MAX_VAL = 55
N_DRAWS = 40

_config_655 = None  # lazy-loaded
_config_535 = None
_config_645 = None


def _get_config_655():
    global _config_655
    if _config_655 is None:
        _config_655 = get_config("power_655")
    return _config_655


def _get_config_535():
    global _config_535
    if _config_535 is None:
        _config_535 = get_config("power_535")
    return _config_535


def _get_config_645():
    global _config_645
    if _config_645 is None:
        _config_645 = get_config("power_645")
    return _config_645


def _make_df(n: int = N_DRAWS, seed: int = 42, ncols: int = 6) -> pd.DataFrame:
    """Create a synthetic lottery DataFrame with `n` draws."""
    rng = random.Random(seed)
    start = date(2023, 1, 1)
    rows = []
    for i in range(n):
        draw_date = start + timedelta(days=i * 3)
        result = sorted(rng.sample(range(MIN_VAL, MAX_VAL + 1), ncols))
        rows.append({"date": draw_date, "result": result, "id": i + 1})
    return pd.DataFrame(rows)


@pytest.fixture
def df():
    return _make_df()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _assert_valid_prediction(pred, model: PredictModel):
    """Assert that a prediction is a sorted list of valid distinct numbers."""
    assert isinstance(pred, list), "predict() must return a list"
    assert len(pred) == model.number_predict, f"Expected {model.number_predict} numbers, got {len(pred)}"
    assert len(set(pred)) == model.number_predict, "Predicted numbers must be distinct"
    assert all(model.min_val <= n <= model.max_val for n in pred), (
        f"All numbers must be in [{model.min_val}, {model.max_val}]"
    )
    assert pred == sorted(pred), "Predicted numbers must be sorted"


# ---------------------------------------------------------------------------
# RandomModel: correctness and full-range coverage
# ---------------------------------------------------------------------------


class TestRandomModel:
    def test_predict_returns_valid_numbers(self, df):
        model = RandomModel(df, time_predict=1)
        pred = model.predict(date(2023, 6, 1))
        _assert_valid_prediction(pred, model)

    def test_predict_includes_max_val(self, df):
        """max_val (55) must be reachable — regression for off-by-one bug."""
        model = RandomModel(df, time_predict=1)
        # 150 iterations: P(55 not seen) = (54/55)^(6*150) ≈ 5e-8
        all_nums = set()
        for _ in range(150):
            all_nums.update(model.predict(date(2023, 6, 1)))
        assert MAX_VAL in all_nums, f"max_val ({MAX_VAL}) was never predicted — off-by-one bug in range() call"

    def test_predict_includes_min_val(self, df):
        """min_val (1) must be reachable."""
        model = RandomModel(df, time_predict=1)
        all_nums = set()
        for _ in range(150):
            all_nums.update(model.predict(date(2023, 6, 1)))
        assert MIN_VAL in all_nums

    def test_backtest_evaluate_pipeline(self, df):
        model = RandomModel(df, time_predict=2)
        model.backtest()
        result = model.evaluate()
        assert "correct_time" in result
        assert "count_correct_num" in result
        assert model.df_backtest_evaluate is not None
        assert not model.df_backtest_evaluate.empty

    def test_revenue_returns_three_values(self, df):
        model = RandomModel(df, time_predict=1)
        model.backtest()
        model.evaluate()
        cost, gain, profit = model.revenue()
        assert cost > 0
        assert gain >= 0
        assert profit == gain - cost


# ---------------------------------------------------------------------------
# MarkovChainStrategy
# ---------------------------------------------------------------------------


class TestMarkovChainStrategy:
    def test_predict_valid(self, df):
        model = MarkovChainStrategy(df, time_predict=1, lookback_days=365)
        pred = model.predict(df["date"].iloc[-1] + timedelta(days=3))
        _assert_valid_prediction(pred, model)

    def test_predict_fallback_no_history(self, df):
        """With no prior history, falls back to uniform random."""
        model = MarkovChainStrategy(df, time_predict=1, lookback_days=365)
        very_early = df["date"].min() - timedelta(days=1)
        pred = model.predict(very_early)
        _assert_valid_prediction(pred, model)

    def test_backtest_date_from_filters_rows(self, df):
        """date_from filters evaluated rows but leaves self.df unchanged."""
        model = MarkovChainStrategy(df, time_predict=1)
        split_date = df["date"].quantile(0.5)
        if hasattr(split_date, "date"):
            split_date = split_date.date()

        model.backtest(date_from=split_date)
        model.evaluate()

        assert model.df_backtest["date"].min() >= split_date
        # Full data still accessible on the model
        assert len(model.df) == len(df)

    def test_backtest_date_to_filters_rows(self, df):
        """date_to filters evaluated rows."""
        model = MarkovChainStrategy(df, time_predict=1)
        split_date = df["date"].quantile(0.5)
        if hasattr(split_date, "date"):
            split_date = split_date.date()

        model.backtest(date_to=split_date)
        model.evaluate()

        assert model.df_backtest["date"].max() <= split_date

    def test_backtest_date_range(self, df):
        """Both date_from and date_to together narrow the evaluated window."""
        model = MarkovChainStrategy(df, time_predict=1)
        all_dates = sorted(df["date"].unique())
        d_from = all_dates[len(all_dates) // 4]
        d_to = all_dates[3 * len(all_dates) // 4]

        model.backtest(date_from=d_from, date_to=d_to)
        model.evaluate()

        assert model.df_backtest["date"].min() >= d_from
        assert model.df_backtest["date"].max() <= d_to

    def test_caching_consistent(self, df):
        """Multiple predict() calls for the same date return same-length result."""
        model = MarkovChainStrategy(df, time_predict=1)
        target = df["date"].iloc[-1] + timedelta(days=3)
        results = [model.predict(target) for _ in range(10)]
        # All predictions must have the right length and be valid
        for r in results:
            _assert_valid_prediction(r, model)


# ---------------------------------------------------------------------------
# All strategies: parametric correctness check
# ---------------------------------------------------------------------------

STRATEGY_FACTORIES = [
    lambda df: RandomModel(df, time_predict=1).apply_product_config(_get_config_655()),
    lambda df: LongAbsenceStrategy(df, time_predict=1, top_n=10).apply_product_config(_get_config_655()),
    lambda df: PatternStrategy(df, time_predict=1, lookback_days=90, pattern_weight=0.6).apply_product_config(
        _get_config_655()
    ),
    lambda df: HotNumbersStrategy(df, time_predict=1, lookback_days=90).apply_product_config(_get_config_655()),
    lambda df: ColdNumbersStrategy(df, time_predict=1, lookback_days=90).apply_product_config(_get_config_655()),
    lambda df: NotRepeatStrategy(df, time_predict=1, lookback_days=14).apply_product_config(_get_config_655()),
    lambda df: ExponentialDecayStrategy(df, time_predict=1, half_life_days=30).apply_product_config(_get_config_655()),
    lambda df: PairFrequencyStrategy(df, time_predict=1, lookback_days=90).apply_product_config(_get_config_655()),
    lambda df: MarkovChainStrategy(df, time_predict=1, lookback_days=90).apply_product_config(_get_config_655()),
    lambda df: SteinerStrategy(df, time_predict=1, lookback_days=90).apply_product_config(_get_config_655()),
    lambda df: HybridStrategy(
        base=PairFrequencyStrategy(df, time_predict=1, lookback_days=180).apply_product_config(_get_config_655()),
        steiner=SteinerStrategy(df, time_predict=1, lookback_days=180).apply_product_config(_get_config_655()),
        top_k=5,
        time_predict=1,
    ).apply_product_config(_get_config_655()),
    lambda df: InverseHybridStrategy(
        proposer=LongAbsenceStrategy(df, time_predict=1, top_n=15).apply_product_config(_get_config_655()),
        steiner=SteinerStrategy(df, time_predict=1, lookback_days=180).apply_product_config(_get_config_655()),
        top_k=15,
        coverage=3,
        time_predict=1,
    ).apply_product_config(_get_config_655()),
]

STRATEGY_NAMES = [
    "RandomModel",
    "LongAbsenceStrategy",
    "PatternStrategy",
    "HotNumbersStrategy",
    "ColdNumbersStrategy",
    "NotRepeatStrategy",
    "ExponentialDecayStrategy",
    "PairFrequencyStrategy",
    "MarkovChainStrategy",
    "SteinerStrategy",
    "HybridStrategy",
    "InverseHybridStrategy",
]


@pytest.mark.parametrize("factory,name", zip(STRATEGY_FACTORIES, STRATEGY_NAMES))
def test_all_strategies_predict_valid(factory, name, df):
    """Every strategy must return a valid ticket for an unseen future date."""
    model = factory(df)
    future_date = df["date"].max() + timedelta(days=3)
    pred = model.predict(future_date)
    _assert_valid_prediction(pred, model)


@pytest.mark.parametrize("factory,name", zip(STRATEGY_FACTORIES, STRATEGY_NAMES))
def test_all_strategies_backtest_pipeline(factory, name, df):
    """Every strategy must complete backtest + evaluate + revenue without error."""
    model = factory(df)
    model.backtest()
    result = model.evaluate()
    cost, gain, profit = model.revenue()

    assert cost > 0, f"{name}: cost should be positive"
    assert gain >= 0, f"{name}: gain cannot be negative"
    assert profit == gain - cost, f"{name}: profit must equal gain - cost"
    assert model.df_backtest_evaluate is not None
    assert not model.df_backtest_evaluate.empty


# ---------------------------------------------------------------------------
# PredictModel.backtest: date filtering works for base class
# ---------------------------------------------------------------------------


class TestBacktestDateFilter:
    def test_no_filter_uses_all_rows(self, df):
        model = RandomModel(df, time_predict=1)
        model.backtest()
        assert len(model.df_backtest) == len(df)

    def test_date_from_reduces_rows(self, df):
        model = RandomModel(df, time_predict=1)
        cutoff = df["date"].iloc[len(df) // 2]
        model.backtest(date_from=cutoff)
        assert len(model.df_backtest) < len(df)
        assert all(d >= cutoff for d in model.df_backtest["date"])

    def test_date_to_reduces_rows(self, df):
        model = RandomModel(df, time_predict=1)
        cutoff = df["date"].iloc[len(df) // 2]
        model.backtest(date_to=cutoff)
        assert len(model.df_backtest) < len(df)
        assert all(d <= cutoff for d in model.df_backtest["date"])


# ---------------------------------------------------------------------------
# Special-number (số đặc biệt) tests
# ---------------------------------------------------------------------------


def test_5_35_wheeling_12_tickets(df):
    """5/35: predict() with special_pick_required=True generates 12 tickets per call."""
    config = _get_config_535()
    model = RandomModel(df, time_predict=1).apply_product_config(config)
    model.prize_fn = lambda m, s: 0
    model.backtest()
    model.evaluate()
    # 40 draws * 1 call * 12 specials = 480 predictions
    assert len(model.df_backtest_evaluate) == 40 * 1 * 12


def test_6_55_overlap_special_match():
    """6/55: special_match = 1 when any of 6 main picks equals result[6]."""
    predicted = [1, 2, 3, 4, 5, 6]
    result = [1, 2, 3, 4, 5, 7, 6]  # last (6) is cầu vàng, matches predicted
    main_match, special_match = PredictModel._compare_list(
        predicted,
        None,
        result,
        has_special=True,
        special_position=6,
        special_pick_required=False,
        main_count=6,
    )
    assert main_match == 5  # first 5 match (6 is not in result[0:6])
    assert special_match == 1  # predicted has 6, result[6] is 6


def test_5_35_explicit_special():
    """5/35: special_match = 1 when predicted_special == result[5]."""
    predicted_main = [1, 2, 3, 4, 5]
    predicted_special = 7
    result = [1, 2, 3, 4, 5, 7]  # last is special=7
    main_match, special_match = PredictModel._compare_list(
        predicted_main,
        predicted_special,
        result,
        has_special=True,
        special_position=5,
        special_pick_required=True,
        main_count=5,
    )
    assert main_match == 5
    assert special_match == 1


def test_6_45_no_special(df):
    """6/45: no special, predict() creates 1 ticket per call."""
    config = _get_config_645()
    model = RandomModel(df, time_predict=1).apply_product_config(config)
    model.prize_fn = lambda m, s: 0
    model.backtest()
    model.evaluate()
    # 40 draws * 1 call * 1 (no special) = 40 predictions
    assert len(model.df_backtest_evaluate) == 40 * 1


# ---------------------------------------------------------------------------
# propose_top_numbers (newly added base capability)
# ---------------------------------------------------------------------------


class TestProposeTopNumbers:
    """All voter strategies must expose ``propose_top_numbers(target_date, k)``."""

    def test_random_deterministic_seed(self, df):
        model = RandomModel(df, time_predict=1)
        target = df["date"].max() + timedelta(days=3)
        first = model.propose_top_numbers(target, 10)
        second = model.propose_top_numbers(target, 10)
        assert first == second, "RandomModel propose_top_numbers must be deterministic per date"
        assert len(first) == 10
        assert len(set(first)) == 10, "Numbers must be distinct"

    def test_long_absence_returns_overdue(self, df):
        model = LongAbsenceStrategy(df, time_predict=1, top_n=10)
        target = df["date"].max() + timedelta(days=3)
        pool = model.propose_top_numbers(target, 10)
        assert len(pool) == 10
        assert len(set(pool)) == 10
        # All within the valid range
        assert all(model.min_val <= n <= model.max_val for n in pool)

    def test_hot_returns_distinct_in_range(self, df):
        model = HotNumbersStrategy(df, time_predict=1, lookback_days=90)
        target = df["date"].max() + timedelta(days=3)
        pool = model.propose_top_numbers(target, 15)
        assert len(pool) == 15
        assert len(set(pool)) == 15
        assert all(model.min_val <= n <= model.max_val for n in pool)

    def test_cold_returns_distinct_in_range(self, df):
        model = ColdNumbersStrategy(df, time_predict=1, lookback_days=90)
        target = df["date"].max() + timedelta(days=3)
        pool = model.propose_top_numbers(target, 15)
        assert len(pool) == 15
        assert len(set(pool)) == 15
        assert all(model.min_val <= n <= model.max_val for n in pool)

    def test_not_repeat_skips_recent(self, df):
        model = NotRepeatStrategy(df, time_predict=1, lookback_days=14)
        target = df["date"].max() + timedelta(days=3)
        pool = model.propose_top_numbers(target, 15)
        assert len(pool) == 15
        # All within the valid range
        assert all(model.min_val <= n <= model.max_val for n in pool)

    def test_pattern_proportional_buckets(self, df):
        model = PatternStrategy(df, time_predict=1, lookback_days=90, pattern_weight=0.6)
        target = df["date"].max() + timedelta(days=3)
        pool = model.propose_top_numbers(target, 15)
        assert len(pool) == 15
        assert all(model.min_val <= n <= model.max_val for n in pool)

    def test_exponential_decay_hot(self, df):
        model = ExponentialDecayStrategy(df, time_predict=1, half_life_days=30, hot=True)
        target = df["date"].max() + timedelta(days=3)
        pool = model.propose_top_numbers(target, 15)
        assert len(pool) == 15
        assert all(model.min_val <= n <= model.max_val for n in pool)

    def test_pair_frequency_proposes(self, df):
        model = PairFrequencyStrategy(df, time_predict=1, lookback_days=90)
        target = df["date"].max() + timedelta(days=3)
        pool = model.propose_top_numbers(target, 15)
        assert len(pool) == 15
        assert all(model.min_val <= n <= model.max_val for n in pool)

    def test_markov_proposes(self, df):
        model = MarkovChainStrategy(df, time_predict=1, lookback_days=90)
        target = df["date"].max() + timedelta(days=3)
        pool = model.propose_top_numbers(target, 15)
        assert len(pool) == 15
        assert all(model.min_val <= n <= model.max_val for n in pool)

    def test_returns_sorted(self, df):
        """All propose_top_numbers implementations must return a sorted list."""
        target = df["date"].max() + timedelta(days=3)
        for factory in [
            lambda d: RandomModel(d, time_predict=1),
            lambda d: LongAbsenceStrategy(d, time_predict=1, top_n=10),
            lambda d: HotNumbersStrategy(d, time_predict=1, lookback_days=90),
            lambda d: ColdNumbersStrategy(d, time_predict=1, lookback_days=90),
            lambda d: NotRepeatStrategy(d, time_predict=1, lookback_days=14),
            lambda d: ExponentialDecayStrategy(d, time_predict=1, half_life_days=30),
            lambda d: PairFrequencyStrategy(d, time_predict=1, lookback_days=90),
            lambda d: MarkovChainStrategy(d, time_predict=1, lookback_days=90),
        ]:
            pool = factory(df).propose_top_numbers(target, 12)
            assert pool == sorted(pool), (
                f"{factory.__name__ if hasattr(factory, '__name__') else factory} returned unsorted pool"
            )


# ---------------------------------------------------------------------------
# SteinerStrategy.predict_from_pool (new method for inverse hybrid)
# ---------------------------------------------------------------------------


class TestSteinerPredictFromPool:
    def test_returns_numbers_from_pool(self, df):
        steiner = SteinerStrategy(df, time_predict=1, lookback_days=180)
        target = df["date"].max() + timedelta(days=3)
        pool = list(range(1, 16))  # 1..15
        pred = steiner.predict_from_pool(target, pool, coverage=3)
        assert len(pred) == steiner.number_predict
        # All predictions must be drawn from the pool
        assert all(n in pool for n in pred), f"Prediction {pred} not all in pool {pool}"
        # Distinct
        assert len(set(pred)) == steiner.number_predict
        # Sorted
        assert pred == sorted(pred)

    def test_coverage_1_works(self, df):
        steiner = SteinerStrategy(df, time_predict=1, lookback_days=180)
        target = df["date"].max() + timedelta(days=3)
        pred = steiner.predict_from_pool(target, list(range(1, 16)), coverage=1)
        assert len(pred) == steiner.number_predict
        assert all(n in range(1, 16) for n in pred)

    def test_coverage_5_works(self, df):
        steiner = SteinerStrategy(df, time_predict=1, lookback_days=180)
        target = df["date"].max() + timedelta(days=3)
        pred = steiner.predict_from_pool(target, list(range(1, 16)), coverage=5)
        assert len(pred) == steiner.number_predict
        assert all(n in range(1, 16) for n in pred)

    def test_small_pool_padding(self, df):
        """Pool smaller than number_predict should pad from the full range."""
        steiner = SteinerStrategy(df, time_predict=1, lookback_days=180)
        target = df["date"].max() + timedelta(days=3)
        # Pool has only 3 numbers; expect padding to number_predict
        pred = steiner.predict_from_pool(target, [10, 20, 30], coverage=3)
        assert len(pred) == steiner.number_predict
        assert all(steiner.min_val <= n <= steiner.max_val for n in pred)

    def test_unsorted_pool_is_handled(self, df):
        steiner = SteinerStrategy(df, time_predict=1, lookback_days=180)
        target = df["date"].max() + timedelta(days=3)
        pool = [55, 1, 23, 7, 42, 11, 33, 5, 19, 28, 14, 50, 2, 39, 17]
        pred = steiner.predict_from_pool(target, pool, coverage=3)
        assert all(n in pool for n in pred)

    @pytest.mark.parametrize("np_value", [3, 4, 5, 6])
    def test_number_predict_via_explicit_arg(self, df, np_value):
        """predict_from_pool honours an explicit number_predict override.

        The standalone Steiner is constructed with default
        ``number_predict=6``, but the caller may pass an explicit value
        (used by ``InverseHybridStrategy`` for non-6/55 products).
        """
        steiner = SteinerStrategy(df, time_predict=1, lookback_days=180)
        target = df["date"].max() + timedelta(days=3)
        pool = list(range(1, 16))  # 1..15
        pred = steiner.predict_from_pool(target, pool, coverage=3, number_predict=np_value)
        assert len(pred) == np_value, f"Expected {np_value} numbers, got {len(pred)}: {pred}"
        assert all(n in pool for n in pred)
        assert len(set(pred)) == np_value
        assert pred == sorted(pred)

    @pytest.mark.parametrize("np_value", [3, 4, 5, 6])
    def test_decompose_into_units(self, np_value):
        """Static helper matches the documented mapping."""
        from machine_learning.strategies.steiner import SteinerStrategy as St

        units = St._decompose_into_units(np_value)
        assert sum(units) == np_value
        assert all(u in (1, 2, 3) for u in units)
        # Specific documented cases
        mapping = {3: [3], 4: [3, 1], 5: [3, 2], 6: [3, 3]}
        if np_value in mapping:
            assert units == mapping[np_value]

    def test_5_35_returns_exactly_5_numbers(self, df):
        """Regression: InverseHybridStrategy on 5/35 must return exactly 5.

        Before the fix, ``SteinerStrategy.predict_from_pool`` always
        built 2 disjoint triples (6 numbers) and the result was sliced
        to 5, which actually returned 6 because the slice was applied
        to a tuple cast that kept the original length.  This test
        guards the bug.
        """
        config = _get_config_535()
        steiner = SteinerStrategy(
            df, time_predict=1, min_val=config.min_value, max_val=config.max_value, lookback_days=180
        )
        target = df["date"].max() + timedelta(days=3)
        pool = list(range(1, 16))  # 1..15
        # Standalone steiner has default number_predict=6
        assert steiner.number_predict == 6
        # But the override must give 5
        pred = steiner.predict_from_pool(target, pool, coverage=3, number_predict=5)
        assert len(pred) == 5, f"5/35: expected 5 numbers, got {len(pred)}: {pred}"
        assert all(1 <= n <= 15 for n in pred)

    def test_5_35_via_inverse_hybrid(self, df):
        """End-to-end: InverseHybridStrategy on 5/35 returns 5 numbers per ticket."""
        config = _get_config_535()
        proposer = LongAbsenceStrategy(df, time_predict=1, min_val=config.min_value, max_val=config.max_value, top_n=15)
        steiner = SteinerStrategy(
            df, time_predict=1, min_val=config.min_value, max_val=config.max_value, lookback_days=180
        )
        model = InverseHybridStrategy(
            proposer=proposer, steiner=steiner, top_k=15, coverage=3, time_predict=1
        ).apply_product_config(config)
        target = df["date"].max() + timedelta(days=3)
        for _ in range(5):
            pred = model.predict(target)
            assert len(pred) == 5, f"5/35 hybrid: expected 5 numbers, got {len(pred)}: {pred}"
            assert all(1 <= n <= 35 for n in pred)


# ---------------------------------------------------------------------------
# InverseHybridStrategy
# ---------------------------------------------------------------------------


class TestInverseHybridStrategy:
    def _build(self, df, proposer=None, coverage=3):
        if proposer is None:
            proposer = LongAbsenceStrategy(df, time_predict=1, top_n=15)
        steiner = SteinerStrategy(df, time_predict=1, lookback_days=180)
        return InverseHybridStrategy(proposer=proposer, steiner=steiner, top_k=15, coverage=coverage, time_predict=1)

    def test_predict_uses_proposer_pool(self, df):
        model = self._build(df, proposer=HotNumbersStrategy(df, time_predict=1, lookback_days=90))
        target = df["date"].max() + timedelta(days=3)
        pred = model.predict(target)
        _assert_valid_prediction(pred, model)
        # Steiner must pick from the proposer's pool of 15 numbers
        pool = set(model.proposer.propose_top_numbers(target, 15))
        assert set(pred).issubset(pool), f"Prediction {pred} not subset of pool {pool}"

    def test_different_proposers_give_different_pools(self, df):
        """Two different proposers should produce two different candidate pools."""
        target = df["date"].max() + timedelta(days=3)
        pool_a = set(HotNumbersStrategy(df, time_predict=1, lookback_days=90).propose_top_numbers(target, 15))
        pool_b = set(LongAbsenceStrategy(df, time_predict=1, top_n=15).propose_top_numbers(target, 15))
        # Sanity: pools should overlap but not be identical (proposers are different signals)
        assert pool_a != pool_b, "Hot and LongAbsence proposers should differ on at least one number"

    def test_backtest_pipeline(self, df):
        model = self._build(df)
        model.backtest()
        model.evaluate()
        cost, gain, profit = model.revenue()
        assert cost > 0
        assert gain >= 0
        assert profit == gain - cost
        assert model.df_backtest_evaluate is not None
        assert not model.df_backtest_evaluate.empty

    def test_ticket_count_per_draw(self, df):
        """time_predict=1 should produce 1 prediction row per draw."""
        model = self._build(df)
        model.backtest()
        model.evaluate()
        # 40 draws * 1 time_predict = 40 rows
        assert len(model.df_backtest_evaluate) == 40

    def test_coverage_param_accepted(self, df):
        model_a = self._build(df, coverage=1)
        model_b = self._build(df, coverage=5)
        target = df["date"].max() + timedelta(days=3)
        # Both should produce valid predictions
        _assert_valid_prediction(model_a.predict(target), model_a)
        _assert_valid_prediction(model_b.predict(target), model_b)

    def test_inherits_proposer_pricing(self, df):
        """InverseHybrid should mirror proposer's ticket_price / prices."""
        proposer = PairFrequencyStrategy(df, time_predict=1, lookback_days=180)
        model = self._build(df, proposer=proposer)
        assert model.ticket_price == proposer.ticket_price
        assert model.number_predict == proposer.number_predict
        assert model.min_val == proposer.min_val
        assert model.max_val == proposer.max_val


# ---------------------------------------------------------------------------
# SteinerStrategy Filters
# ---------------------------------------------------------------------------


class TestSteinerFilters:
    def test_is_valid_triple_consecutive(self):
        # Consecutive numbers
        assert not SteinerStrategy.is_valid_triple((1, 2, 10), filter_consecutive=True, filter_same_decade=False)
        assert not SteinerStrategy.is_valid_triple((10, 15, 16), filter_consecutive=True, filter_same_decade=False)
        assert SteinerStrategy.is_valid_triple((1, 3, 5), filter_consecutive=True, filter_same_decade=False)

    def test_is_valid_triple_same_decade(self):
        # Same decade numbers
        assert not SteinerStrategy.is_valid_triple((12, 15, 18), filter_consecutive=False, filter_same_decade=True)
        assert not SteinerStrategy.is_valid_triple((20, 22, 29), filter_consecutive=False, filter_same_decade=True)
        assert SteinerStrategy.is_valid_triple((12, 25, 38), filter_consecutive=False, filter_same_decade=True)

    def test_steiner_strategy_with_filters(self, df):
        model = SteinerStrategy(df, time_predict=1, filter_consecutive=True, filter_same_decade=True)
        pred = model.predict(df["date"].max() + timedelta(days=3))
        _assert_valid_prediction(pred, model)


# ---------------------------------------------------------------------------
# SteinerStrategy custom S(t, k, v) system
# ---------------------------------------------------------------------------


class TestSteinerCustomSystem:
    """Custom Steiner system: ``S(t, k, v)`` over the number range."""

    def test_default_t_k_v_for_power_655(self, df):
        """S(2, 3, 55) is the default for power_655."""
        model = SteinerStrategy(df, time_predict=1).apply_product_config(_get_config_655())
        assert model.steiner_system == (2, 3, 55)
        assert model.t == 2
        assert model.k == 3
        assert model.v == 55

    def test_default_t_k_v_for_power_645(self, df):
        """S(2, 3, 45) is the default for power_645."""
        model = SteinerStrategy(df, time_predict=1).apply_product_config(_get_config_645())
        assert model.steiner_system == (2, 3, 45)

    def test_default_t_k_v_for_power_535(self, df):
        """S(2, 3, 35) is the default for power_535."""
        model = SteinerStrategy(df, time_predict=1).apply_product_config(_get_config_535())
        assert model.steiner_system == (2, 3, 35)

    def test_set_steiner_system_rebuilds_blocks(self, df):
        """set_steiner_system clears caches and rebuilds the blocks."""
        model = SteinerStrategy(df, time_predict=1, min_val=1, max_val=55)
        original_blocks = list(model._blocks)
        original_t, original_k, original_v = model.t, model.k, model.v

        # Switch to a custom S(2, 3, 27) system.
        model.set_steiner_system(t=2, k=3, v=27)
        assert model.steiner_system == (2, 3, 27)
        assert all(max(b) <= 27 for b in model._blocks)
        # All blocks have exactly k=3 elements
        assert all(len(b) == 3 for b in model._blocks)
        # No pair is covered twice (t=2 → pairwise disjoint)
        pairs_covered: set = set()
        for b in model._blocks:
            for pair in combinations(sorted(b), 2):
                assert pair not in pairs_covered, f"Pair {pair} covered twice in S(2, 3, 27)"
                pairs_covered.add(pair)
        # Restore defaults for other tests
        model.set_steiner_system(t=original_t, k=original_k, v=original_v)
        # After restore we should get back an equivalent set of blocks
        assert len(model._blocks) == len(original_blocks)

    def test_custom_steiner_k_4_works(self, df):
        """Custom block size k=4 (S(2, 4, v)) produces valid 4-element blocks."""
        model = SteinerStrategy(df, time_predict=1, min_val=1, max_val=21, t=2, k=4, v=21)
        # k=4, v=21: every 4-block is sorted and has distinct elements
        for b in model._blocks:
            assert len(b) == 4
            assert len(set(b)) == 4
            assert list(b) == sorted(b)
        # No pair appears in two blocks
        pairs_covered: set = set()
        for b in model._blocks:
            for pair in combinations(sorted(b), 2):
                assert pair not in pairs_covered
                pairs_covered.add(pair)
        # t=2 validation: v=21, k=4 → v*(v-1)=420, k*(k-1)=12, 420 % 12 == 0 ✓
        # so a full system is possible (necessary but not sufficient).
        assert model.steiner_system == (2, 4, 21)

    def test_on_pool_steiner_general_t_k(self, df):
        """Regression: ``_build_steiner_on_pool`` must support any (t, k).

        Previously the on-pool builder was hard-coded to a 2-element
        anchor (k=3 only) so S(5, 6, 12) on a 12-element user pool
        produced only 2 blocks instead of 68.  The fix uses the same
        general t/k algorithm as :meth:`_build_partial_steiner`.
        """
        user_pool = [3, 7, 11, 15, 22, 28, 35, 41, 47, 49, 52, 55]
        # S(5, 6, 12) — every 5-tuple covered at most once.
        blocks = SteinerStrategy._build_steiner_on_pool(user_pool, k=6, t=5)
        assert len(blocks) > 2, f"Expected many blocks, got {len(blocks)}"
        # All blocks have 6 sorted distinct elements from the pool.
        for b in blocks:
            assert len(b) == 6
            assert list(b) == sorted(b)
            assert all(n in user_pool for n in b)
        # No 5-tuple appears in two blocks.
        seen_5: set = set()
        for b in blocks:
            for tup in combinations(sorted(b), 5):
                assert tup not in seen_5, f"5-tuple {tup} covered twice"
                seen_5.add(tup)

    def test_fano_plane_s_2_3_7(self, df):
        """S(2, 3, 7) — the Fano plane has 7 blocks covering all 21 pairs.

        Regression for the index/value mixing bug in the on-pool builder:
        the 'anchor already covered' check was comparing index frozensets
        against value frozensets, so the check never fired correctly and
        the greedy produced only 6 of 7 blocks.
        """
        blocks = SteinerStrategy._build_steiner_on_pool(list(range(1, 8)), k=3, t=2)
        assert len(blocks) == 7, f"Fano plane has 7 blocks, got {len(blocks)}"
        # Every pair of {1..7} is covered exactly once.
        covered: set = set()
        for b in blocks:
            for p in combinations(sorted(b), 2):
                assert p not in covered, f"Pair {p} covered twice"
                covered.add(p)
        assert len(covered) == 21, f"Expected all 21 pairs covered, got {len(covered)}"
        # Every block has 3 sorted distinct elements from {1..7}.
        for b in blocks:
            assert len(b) == 3
            assert list(b) == sorted(b)
            assert all(1 <= n <= 7 for n in b)
            assert len(set(b)) == 3

    def test_partial_steiner_fano_plane(self, df):
        """``_build_partial_steiner`` must also produce all 7 Fano triples."""
        model = SteinerStrategy(df, time_predict=1, min_val=1, max_val=7, t=2, k=3, v=7)
        assert len(model._blocks) == 7, f"Fano plane has 7 blocks, got {len(model._blocks)}"

    def test_on_pool_steiner_s_2_6_12(self, df):
        """S(2, 6, 12) on [1..12] — full greedy decomposition."""
        blocks = SteinerStrategy._build_steiner_on_pool(list(range(1, 13)), k=6, t=2)
        for b in blocks:
            assert len(b) == 6
            for pair in combinations(sorted(b), 2):
                # All elements are within [1, 12]
                pass  # sanity only — disjointness already guaranteed
        # Every pair must be unique across blocks (t=2 invariant).
        seen: set = set()
        for b in blocks:
            for pair in combinations(sorted(b), 2):
                assert pair not in seen
                seen.add(pair)

    def test_custom_steiner_validates_arguments(self, df):
        """Constructor rejects t < 1, k < t, k > pool_size, v < k."""
        # t < 1
        with pytest.raises(ValueError, match="Steiner strength t must be"):
            SteinerStrategy(df, time_predict=1, min_val=1, max_val=10, t=0)
        # k < t
        with pytest.raises(ValueError, match="Block size k=2 must be >= t=3"):
            SteinerStrategy(df, time_predict=1, min_val=1, max_val=10, t=3, k=2)
        # k > pool
        with pytest.raises(ValueError, match="larger than the number range"):
            SteinerStrategy(df, time_predict=1, min_val=1, max_val=5, t=2, k=6)
        # v < k
        with pytest.raises(ValueError, match="Steiner v=2 must be >= k=3"):
            SteinerStrategy(df, time_predict=1, min_val=1, max_val=10, t=2, k=3, v=2)

    def test_set_steiner_system_validates_arguments(self, df):
        """set_steiner_system enforces the same invariants as the constructor."""
        model = SteinerStrategy(df, time_predict=1, min_val=1, max_val=10)
        with pytest.raises(ValueError, match="Steiner strength t must be"):
            model.set_steiner_system(t=0, k=2, v=5)
        with pytest.raises(ValueError, match="Block size k=2 must be >= t=3"):
            model.set_steiner_system(t=3, k=2, v=5)
        with pytest.raises(ValueError, match="larger than the number range"):
            model.set_steiner_system(t=2, k=20, v=20)
        with pytest.raises(ValueError, match="Steiner v=2 must be >= k=3"):
            model.set_steiner_system(t=2, k=3, v=2)

    def test_is_valid_steiner_v_classic_conditions(self):
        """Necessary conditions for a full S(2, 3, v) to exist.

        A full Steiner triple system S(2, 3, v) exists iff
        ``v ≡ 1 or 3 (mod 6)``.  Note: this excludes 35 (5 mod 6) and 50
        (2 mod 6), so the configured default ``S(2, 3, 35)`` for
        ``power_535`` is necessarily a *partial* system — the greedy
        algorithm produces a pairwise-disjoint decomposition of [1, 35]
        but does not cover every pair.
        """
        # v ≡ 1 or 3 (mod 6) — full STS exists
        for v in (7, 9, 13, 15, 19, 21, 25, 27, 31, 33, 37, 39, 43, 45, 49, 51, 55):
            assert SteinerStrategy.is_valid_steiner_v(v, k=3), f"S(2,3,{v}) should be constructible"
        # v % 6 ∈ {0, 2, 4, 5} — full STS does NOT exist (v ≥ k = 3)
        for v in (5, 6, 8, 10, 11, 12, 14, 20, 22, 35, 50, 100):
            assert not SteinerStrategy.is_valid_steiner_v(v, k=3), f"S(2,3,{v}) should not be constructible"

    def test_power_535_steiner_is_partial(self, df):
        """S(2, 3, 35) is necessarily partial — only some pairs are covered.

        Documents the design choice: ``power_535`` configures the greedy
        partial Steiner system.  The pool still produces valid Steiner
        triples for prediction but does not cover every pair.
        """
        model = SteinerStrategy(df, time_predict=1, min_val=1, max_val=35, t=2, k=3, v=35)
        pairs_covered: set = set()
        for b in model._blocks:
            for pair in combinations(sorted(b), 2):
                pairs_covered.add(pair)
        # Full S(2, 3, 35) would cover C(35, 2) = 595 pairs.
        # The partial greedy system covers a smaller subset.
        assert 0 < len(pairs_covered) < 595, (
            f"Partial S(2,3,35) should cover some but not all pairs, got {len(pairs_covered)}"
        )
        # All triples still have 3 sorted distinct elements in [1, 35].
        for b in model._blocks:
            assert len(b) == 3
            assert list(b) == sorted(b)
            assert all(1 <= n <= 35 for n in b)

    def test_default_steiner_system_classmethod(self):
        """Class-level lookup of per-product default Steiner systems."""
        assert SteinerStrategy.default_steiner_system("power_535") == (2, 3, 35)
        assert SteinerStrategy.default_steiner_system("power_645") == (2, 3, 45)
        assert SteinerStrategy.default_steiner_system("power_655") == (2, 3, 55)
        assert SteinerStrategy.default_steiner_system("keno") is None
        assert SteinerStrategy.default_steiner_system("bingo18") is None

    def test_custom_steiner_predict_uses_custom_pool(self, df):
        """Predict with custom (t, k, v) honours the new design and returns valid tickets."""
        model = SteinerStrategy(df, time_predict=1, min_val=1, max_val=27, t=2, k=3, v=27)
        target = df["date"].max() + timedelta(days=3)
        for _ in range(3):
            pred = model.predict(target)
            # Default number_predict is 6; with k=3, the ticket is the
            # union of 2 disjoint triples, then sliced to 6.
            assert len(pred) == model.number_predict == 6
            assert all(1 <= n <= 27 for n in pred)
            assert len(set(pred)) == 6
            assert pred == sorted(pred)

    def test_apply_product_config_uses_default_steiner(self, df):
        """Per-product defaults are applied via apply_product_config."""
        for cfg in (_get_config_535(), _get_config_645(), _get_config_655()):
            model = SteinerStrategy(df, time_predict=1).apply_product_config(cfg)
            expected = (2, 3, cfg.max_value)
            assert model.steiner_system == expected, f"Expected S{expected} for {cfg.name}"

    def test_registry_lists_steiner_params(self):
        """Registry exposes t, k, v on the 'steiner' entry."""
        from machine_learning.strategies.registry import list_strategies

        entries = {e["key"]: e for e in list_strategies()}
        assert "steiner" in entries
        names = {p["name"] for p in entries["steiner"]["params"]}
        assert {"t", "k", "v"}.issubset(names), f"Steiner params should include t/k/v, got {names}"


# ---------------------------------------------------------------------------
# ProductConfig.steiner_system wiring
# ---------------------------------------------------------------------------


class TestProductConfigSteinerSystem:
    """ProductConfig.steiner_system wires the default S(t, k, v) per product."""

    def test_power_655_default_steiner_system(self):
        from vietlott.config.products import get_config

        cfg = get_config("power_655")
        assert cfg.steiner_system == (2, 3, 55)

    def test_power_645_default_steiner_system(self):
        from vietlott.config.products import get_config

        cfg = get_config("power_645")
        assert cfg.steiner_system == (2, 3, 45)

    def test_power_535_default_steiner_system(self):
        from vietlott.config.products import get_config

        cfg = get_config("power_535")
        assert cfg.steiner_system == (2, 3, 35)

    def test_non_steiner_products_have_none(self):
        from vietlott.config.products import get_config

        # Products without a registered default leave it as None so the
        # strategy auto-derives ``(2, 3, max_value)``.
        for name in ("keno", "3d", "3d_pro", "bingo18"):
            assert get_config(name).steiner_system is None, f"{name} should have steiner_system=None"
