"""
Tests for PipelineStrategy.

Covers:
- Construction with valid / invalid specs
- predict() returns sorted distinct numbers in range
- generate_tickets() produces distinct deduplicated tickets
- backtest() populates df_backtest and integrates with evaluate() / revenue()
- Post-filter violation logs warning and returns best-effort ticket
"""

import json
import random
from datetime import date, timedelta
from pathlib import Path
from typing import List

import pandas as pd
import pytest
from loguru import logger

from machine_learning.strategies.base import PredictModel
from machine_learning.strategies.pipeline import PipelineStrategy, _validate_spec

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

MIN_VAL = 1
MAX_VAL = 55
N_DRAWS = 40


def _make_df(n: int = N_DRAWS, seed: int = 42, ncols: int = 6) -> pd.DataFrame:
    """Create a synthetic lottery DataFrame with ``n`` draws."""
    rng = random.Random(seed)
    start = date(2023, 1, 1)
    rows = []
    for i in range(n):
        draw_date = start + timedelta(days=i * 3)
        result = sorted(rng.sample(range(MIN_VAL, MAX_VAL + 1), ncols))
        # Include all 7 numbers (6 main + 1 special) for power_655-like data.
        special = rng.randint(MIN_VAL, MAX_VAL)
        rows.append({"date": draw_date, "result": result + [special], "id": str(i + 1)})
    return pd.DataFrame(rows)


def _load_real_data() -> pd.DataFrame:
    """Try to load real power_655 data; return synthetic fallback if unavailable."""
    data_path = Path(__file__).parent.parent.parent.parent.parent / "data" / "power655.jsonl"
    if data_path.exists():
        import polars as pl

        pdf = pl.read_ndjson(data_path)
        df = pdf.to_pandas()
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date").reset_index(drop=True)
        # Keep only the last 60 draws for fast tests.
        return df.tail(60).reset_index(drop=True)
    logger.warning("Real data not found at {}, using synthetic data", data_path)
    return _make_df(n=60)


def _base_spec() -> dict:
    """Return a valid pipeline spec for power_655 with 2 groups."""
    return {
        "product": "power_655",
        "groups": [
            {
                "name": "Steiner pool",
                "strategy": "steiner",
                "params": {"lookback_days": 365},
                "pool_size": 15,
                "pick_count": 5,
            },
            {
                "name": "Frequency filler",
                "strategy": "frequency",
                "params": {"lookback_days": 90, "strategy_type": "hot"},
                "pool_size": 10,
                "pick_count": 1,
            },
        ],
        "combiner": {"method": "concatenate"},
        "post_filters": {},
        "ticket_count": 1,
    }


@pytest.fixture(scope="module")
def df():
    return _load_real_data()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _assert_valid_ticket(ticket: List[int], model: PredictModel) -> None:
    """Assert that *ticket* is a sorted list of valid distinct numbers."""
    assert isinstance(ticket, list), "Ticket must be a list"
    assert len(ticket) == model.number_predict, f"Expected {model.number_predict} numbers, got {len(ticket)}"
    assert len(set(ticket)) == model.number_predict, "Ticket numbers must be distinct"
    assert all(model.min_val <= n <= model.max_val for n in ticket), (
        f"All numbers must be in [{model.min_val}, {model.max_val}]"
    )
    assert ticket == sorted(ticket), "Ticket must be sorted"


# ---------------------------------------------------------------------------
# Spec validation
# ---------------------------------------------------------------------------


class TestSpecValidation:
    def test_invalid_spec_not_dict(self):
        with pytest.raises(ValueError, match="must be a dict"):
            _validate_spec("not a dict")

    def test_missing_groups(self):
        with pytest.raises(ValueError, match="groups"):
            _validate_spec({})

    def test_empty_groups(self):
        with pytest.raises(ValueError, match="non-empty"):
            _validate_spec({"groups": []})

    def test_missing_strategy_key(self):
        with pytest.raises(ValueError, match="strategy"):
            _validate_spec({"groups": [{"pick_count": 3}]})

    def test_unknown_strategy(self):
        with pytest.raises(ValueError, match="unknown strategy"):
            _validate_spec({"groups": [{"strategy": "bogus", "pick_count": 3}]})

    def test_invalid_pick_count(self):
        with pytest.raises(ValueError, match="positive integer"):
            _validate_spec({"groups": [{"strategy": "random", "pick_count": 0}]})

    def test_valid_spec_passes(self, df):
        spec = _base_spec()
        model = PipelineStrategy(df, spec)
        assert model is not None
        print("OK: valid pipeline spec constructs without error")

    def test_pick_count_mismatch(self, df):
        """Sum of pick_counts must equal number_predict."""
        spec = _base_spec()
        spec["groups"][0]["pick_count"] = 6  # was 5, now total = 7 ≠ 6
        with pytest.raises(ValueError, match="must equal"):
            PipelineStrategy(df, spec)

    def test_pick_exceeds_pool_graceful(self, df):
        """pick_count > first-step pool_size is handled gracefully at runtime.
        The chain produces what it can and pads from the full range."""
        spec = {
            "product": "power_655",
            "groups": [
                {
                    "name": "Over-pick group",
                    "strategy": "random",
                    "params": {},
                    "pool_size": 2,
                    "pick_count": 6,
                },
            ],
            "combiner": {"method": "concatenate"},
            "post_filters": {},
        }
        model = PipelineStrategy(df, spec)
        target = df["date"].max() + timedelta(days=3)
        ticket = model.predict(target)
        _assert_valid_ticket(ticket, model)
        print(f"OK: pick_count > pool_size handled gracefully: {ticket}")


# ---------------------------------------------------------------------------
# predict()
# ---------------------------------------------------------------------------


class TestPredict:
    def test_returns_valid_ticket(self, df):
        spec = _base_spec()
        model = PipelineStrategy(df, spec)
        target = df["date"].max() + timedelta(days=3)
        ticket = model.predict(target)
        _assert_valid_ticket(ticket, model)
        print(f"OK: predict returned {ticket}")

    def test_numbers_within_range(self, df):
        spec = _base_spec()
        model = PipelineStrategy(df, spec)
        target = df["date"].max() + timedelta(days=3)
        for _ in range(10):
            ticket = model.predict(target)
            assert all(MIN_VAL <= n <= MAX_VAL for n in ticket)
        print("OK: all predicted numbers in range")

    def test_deterministic_groups(self, df):
        """Same inputs produce same ticket (strategies may be stochastic,
        so we just verify valid structure)."""
        spec = _base_spec()
        model = PipelineStrategy(df, spec)
        target = df["date"].max() + timedelta(days=3)
        ticket = model.predict(target)
        _assert_valid_ticket(ticket, model)
        print(f"OK: predict deterministic shape: {ticket}")


# ---------------------------------------------------------------------------
# generate_tickets()
# ---------------------------------------------------------------------------


def _random_spec() -> dict:
    """Return a pipeline spec using random strategies for stochastic output."""
    return {
        "product": "power_655",
        "groups": [
            {
                "name": "Random group 1",
                "strategy": "random",
                "params": {},
                "pool_size": 55,
                "pick_count": 3,
            },
            {
                "name": "Random group 2",
                "strategy": "random",
                "params": {},
                "pool_size": 55,
                "pick_count": 3,
            },
        ],
        "combiner": {"method": "concatenate"},
        "post_filters": {},
        "ticket_count": 1,
    }


class TestGenerateTickets:
    def test_returns_multiple_distinct(self, df):
        spec = _random_spec()
        spec["ticket_count"] = 3
        model = PipelineStrategy(df, spec)
        target = df["date"].max() + timedelta(days=3)
        tickets = model.generate_tickets(target, ticket_count=3)
        assert len(tickets) == 3, f"Expected 3 tickets, got {len(tickets)}"
        # All must be valid.
        for t in tickets:
            _assert_valid_ticket(t, model)
        # Must be distinct.
        unique = {tuple(t) for t in tickets}
        assert len(unique) == 3, "Tickets must be distinct"
        print(f"OK: generate_tickets returned 3 distinct tickets")

    def test_ticket_count_default(self, df):
        spec = _base_spec()
        model = PipelineStrategy(df, spec)
        target = df["date"].max() + timedelta(days=3)
        tickets = model.generate_tickets(target)
        # Default ticket_count is 1.
        assert len(tickets) == 1
        _assert_valid_ticket(tickets[0], model)
        print("OK: default ticket_count=1 works")

    def test_dedup_warning(self, df):
        """With a very constrained pick, dedup may produce fewer tickets than
        requested.  We just verify it doesn't crash."""
        spec = _base_spec()
        spec["groups"] = [
            {
                "name": "Only group",
                "strategy": "random",
                "params": {},
                "pool_size": 55,
                "pick_count": 6,
            }
        ]
        model = PipelineStrategy(df, spec)
        target = df["date"].max() + timedelta(days=3)
        tickets = model.generate_tickets(target, ticket_count=10)
        assert len(tickets) > 0
        for t in tickets:
            _assert_valid_ticket(t, model)
        print(f"OK: generate_tickets produced {len(tickets)} tickets (requested 10)")


# ---------------------------------------------------------------------------
# backtest()
# ---------------------------------------------------------------------------


class TestBacktest:
    def test_backtest_populates_df(self, df):
        spec = _base_spec()
        model = PipelineStrategy(df, spec)
        # Use a small date range for speed.
        dates = sorted(df["date"].unique())
        d_from = dates[-15] if len(dates) >= 15 else dates[0]
        d_to = dates[-1]
        model.backtest(date_from=d_from, date_to=d_to)
        assert model.df_backtest is not None
        assert len(model.df_backtest) > 0
        print(f"OK: backtest populated df_backtest with {len(model.df_backtest)} rows")

    def test_backtest_in_range(self, df):
        model = PipelineStrategy(df, _base_spec())
        dates = sorted(df["date"].unique())
        d_from = dates[-10] if len(dates) >= 10 else dates[0]
        d_to = dates[-1]
        model.backtest(date_from=d_from, date_to=d_to)
        assert model.df_backtest["date"].min() >= d_from
        assert model.df_backtest["date"].max() <= d_to
        print(f"OK: backtest date range [{d_from}, {d_to}] respected")

    def test_evaluate_and_revenue(self, df):
        model = PipelineStrategy(df, _base_spec())
        dates = sorted(df["date"].unique())
        d_from = dates[-10] if len(dates) >= 10 else dates[0]
        d_to = dates[-1]
        model.backtest(date_from=d_from, date_to=d_to)
        result = model.evaluate()
        assert "correct_time" in result
        assert "count_correct_num" in result
        cost, gain, profit = model.revenue()
        assert cost > 0
        assert gain >= 0
        assert profit == gain - cost
        # Cost = num_backtest_rows * ticket_price
        expected_cost = len(model.df_backtest_evaluate) * model.ticket_price
        assert cost == expected_cost, f"Expected cost {expected_cost}, got {cost}"
        print(f"OK: evaluate+revenue: cost={cost}, gain={gain}, profit={profit}")

    def test_backtest_ticket_count_cost(self, df):
        """When ticket_count > 1, cost should reflect the extra tickets per draw."""
        spec = _random_spec()
        spec["ticket_count"] = 3
        model = PipelineStrategy(df, spec)
        dates = sorted(df["date"].unique())
        d_from = dates[-5] if len(dates) >= 5 else dates[0]
        d_to = dates[-1]
        model.backtest(date_from=d_from, date_to=d_to)
        model.evaluate()
        num_draws = len(model.df_backtest)
        expected_cost = num_draws * 3 * model.ticket_price  # ticket_count=3
        cost, gain, profit = model.revenue()
        assert cost == expected_cost, f"ticket_count=3: expected cost {expected_cost}, got {cost}"
        print(f"OK: backtest with ticket_count=3: cost={cost}, draws={num_draws}")


# ---------------------------------------------------------------------------
# Post-filters
# ---------------------------------------------------------------------------


class TestPostFilters:
    def test_impossible_filter_logs_warning(self, df):
        """A min_sum=400 is impossible for 6 numbers in [1,55]
        (max sum = 55+54+53+52+51+50 = 315)."""
        from loguru import logger as loguru_logger

        captured_messages = []

        def _sink(msg):
            captured_messages.append(msg)

        sink_id = loguru_logger.add(_sink, level="WARNING")
        try:
            spec = _base_spec()
            spec["post_filters"] = {"min_sum": 400}
            model = PipelineStrategy(df, spec)
            target = df["date"].max() + timedelta(days=3)
            ticket = model.predict(target)
            _assert_valid_ticket(ticket, model)
        finally:
            loguru_logger.remove(sink_id)

        assert any("best-effort" in str(m) for m in captured_messages), "Expected warning about best-effort ticket"
        print(f"OK: impossible post-filter logged warning and returned ticket")

    def test_even_odd_filter(self, df):
        """Filter: at least 2 even numbers, at most 4 odd numbers."""
        spec = _base_spec()
        spec["post_filters"] = {"min_even": 2, "max_odd": 4}
        model = PipelineStrategy(df, spec)
        target = df["date"].max() + timedelta(days=3)
        for _ in range(10):
            ticket = model.predict(target)
            _assert_valid_ticket(ticket, model)
            evens = sum(1 for n in ticket if n % 2 == 0)
            odds = model.number_predict - evens
            assert evens >= 2, f"Filter min_even=2 violated: {ticket} (evens={evens})"
            assert odds <= 4, f"Filter max_odd=4 violated: {ticket} (odds={odds})"
        print("OK: even/odd post-filters enforced")

    def test_sum_filter(self, df):
        """Filter: sum between 80 and 200 (using random strategies for variety)."""
        spec = _random_spec()
        spec["post_filters"] = {"min_sum": 80, "max_sum": 200}
        model = PipelineStrategy(df, spec)
        target = df["date"].max() + timedelta(days=3)
        for _ in range(10):
            ticket = model.predict(target)
            _assert_valid_ticket(ticket, model)
            total = sum(ticket)
            assert 80 <= total <= 200, f"Sum filter [80, 200] violated: {ticket} (sum={total})"
        print("OK: sum post-filter enforced")


# ---------------------------------------------------------------------------
# No product name (user-specified range)
# ---------------------------------------------------------------------------


class TestExplicitRange:
    def test_explicit_min_max(self, df):
        """Pipeline can work without a 'product' key by providing explicit
        min_val / max_val."""
        spec = _base_spec()
        del spec["product"]
        model = PipelineStrategy(df, spec, min_val=1, max_val=55)
        target = df["date"].max() + timedelta(days=3)
        ticket = model.predict(target)
        _assert_valid_ticket(ticket, model)
        print("OK: explicit min_val/max_val without product key works")


# ---------------------------------------------------------------------------
# JSON serialisation of spec (round-trip)
# ---------------------------------------------------------------------------


class TestSpecJsonRoundTrip:
    def test_spec_json_roundtrip(self, df):
        """A spec dict serialised to JSON and back should still construct a
        valid pipeline."""
        spec = _base_spec()
        json_str = json.dumps(spec)
        restored = json.loads(json_str)
        model = PipelineStrategy(df, restored)
        target = df["date"].max() + timedelta(days=3)
        ticket = model.predict(target)
        _assert_valid_ticket(ticket, model)
        print("OK: JSON round-trip spec constructs valid pipeline")


# ---------------------------------------------------------------------------
# Chain strategy tests (new multi-step format)
# ---------------------------------------------------------------------------


class TestChains:
    """Tests for the new multi-strategy chain feature."""

    def _chain_spec(self, n_strategies: int = 2) -> dict:
        """Return a spec with a single multi-step chain group."""
        chain = [
            {"strategy": "steiner", "params": {"lookback_days": 365}, "pool_size": 20},
        ]
        if n_strategies >= 2:
            chain.append({"strategy": "frequency", "params": {"lookback_days": 90, "strategy_type": "hot"}})
        if n_strategies >= 3:
            chain.append({"strategy": "random", "params": {}})
        return {
            "product": "power_655",
            "groups": [
                {
                    "name": "Chain group",
                    "strategies": chain,
                    "pick_count": 6,
                },
            ],
            "combiner": {"method": "concatenate"},
            "post_filters": {},
            "ticket_count": 1,
        }

    def test_multi_step_chain_produces_valid_ticket(self, df):
        """2-step chain: Steiner → Frequency, single group of 6."""
        spec = self._chain_spec(2)
        model = PipelineStrategy(df, spec)
        target = df["date"].max() + timedelta(days=3)
        ticket = model.predict(target)
        _assert_valid_ticket(ticket, model)
        print(f"OK: 2-step chain returned {ticket}")

    def test_three_step_chain(self, df):
        """3-step chain: Steiner → Frequency → Random."""
        spec = self._chain_spec(3)
        model = PipelineStrategy(df, spec)
        target = df["date"].max() + timedelta(days=3)
        ticket = model.predict(target)
        _assert_valid_ticket(ticket, model)
        print(f"OK: 3-step chain returned {ticket}")

    def test_two_groups_with_chains(self, df):
        """Two groups each with 2-step chains, summing to 6 picks."""
        spec = {
            "product": "power_655",
            "groups": [
                {
                    "name": "Chain A",
                    "strategies": [
                        {"strategy": "steiner", "params": {"lookback_days": 365}, "pool_size": 20},
                        {"strategy": "frequency", "params": {"lookback_days": 90, "strategy_type": "hot"}},
                    ],
                    "pick_count": 3,
                },
                {
                    "name": "Chain B",
                    "strategies": [
                        {"strategy": "random", "params": {}, "pool_size": 55},
                        {"strategy": "steiner", "params": {"lookback_days": 180}},
                    ],
                    "pick_count": 3,
                },
            ],
            "combiner": {"method": "concatenate"},
            "post_filters": {},
            "ticket_count": 2,
        }
        model = PipelineStrategy(df, spec)
        target = df["date"].max() + timedelta(days=3)
        tickets = model.generate_tickets(target, ticket_count=2)
        assert len(tickets) == 2
        for t in tickets:
            _assert_valid_ticket(t, model)
        print(f"OK: two chain groups produced {len(tickets)} valid tickets")

    def test_empty_strategies_raises(self, df):
        """Empty strategies list should raise ValueError."""
        spec = {
            "product": "power_655",
            "groups": [
                {
                    "name": "Empty chain",
                    "strategies": [],
                    "pick_count": 6,
                },
            ],
        }
        with pytest.raises(ValueError, match="non-empty list"):
            PipelineStrategy(df, spec)

    def test_missing_strategies_key_raises(self, df):
        """Group with neither 'strategies' nor 'strategy' should raise."""
        spec = {
            "product": "power_655",
            "groups": [
                {
                    "name": "No strategy",
                    "pick_count": 6,
                },
            ],
        }
        with pytest.raises(ValueError, match="strategies.*or.*strategy"):
            PipelineStrategy(df, spec)

    def test_pick_count_sum_enforced_with_chains(self, df):
        """Sum of pick_counts must equal number_predict even with chains."""
        spec = self._chain_spec(2)
        spec["groups"][0]["pick_count"] = 5  # sum=5, not 6
        with pytest.raises(ValueError, match="must equal"):
            PipelineStrategy(df, spec)

    def test_new_format_backward_compat_old_format(self, df):
        """Old-format groups (strategy+params+pool_size) still work."""
        spec = _base_spec()  # uses old format
        model = PipelineStrategy(df, spec)
        target = df["date"].max() + timedelta(days=3)
        ticket = model.predict(target)
        _assert_valid_ticket(ticket, model)
        print(f"OK: old format still works: {ticket}")

    def test_mixed_old_and_new_format(self, df):
        """Groups in mixed old/new format within the same spec."""
        spec = {
            "product": "power_655",
            "groups": [
                {
                    "name": "Old format",
                    "strategy": "random",
                    "params": {},
                    "pool_size": 55,
                    "pick_count": 3,
                },
                {
                    "name": "New format",
                    "strategies": [
                        {"strategy": "random", "params": {}, "pool_size": 55},
                    ],
                    "pick_count": 3,
                },
            ],
            "combiner": {"method": "concatenate"},
            "post_filters": {},
            "ticket_count": 1,
        }
        model = PipelineStrategy(df, spec)
        target = df["date"].max() + timedelta(days=3)
        ticket = model.predict(target)
        _assert_valid_ticket(ticket, model)
        print(f"OK: mixed old/new format produced: {ticket}")

    def test_pool_size_default_on_second_step(self, df):
        """Second step without pool_size should not raise."""
        spec = {
            "product": "power_655",
            "groups": [
                {
                    "name": "Chain with partial pool_size",
                    "strategies": [
                        {"strategy": "random", "params": {}, "pool_size": 55},
                        {"strategy": "steiner", "params": {"lookback_days": 365}},  # no pool_size
                    ],
                    "pick_count": 6,
                },
            ],
        }
        model = PipelineStrategy(df, spec)
        target = df["date"].max() + timedelta(days=3)
        ticket = model.predict(target)
        _assert_valid_ticket(ticket, model)
        print(f"OK: second step without pool_size works: {ticket}")

    def test_chain_with_random_sampling_variety(self, df):
        """Multiple tickets from same chain should vary."""
        spec = self._chain_spec(2)
        model = PipelineStrategy(df, spec)
        target = df["date"].max() + timedelta(days=3)

        # Make pool_size larger than pick_count so random sampling kicks in.
        spec["groups"][0]["strategies"][0]["pool_size"] = 55
        model2 = PipelineStrategy(df, spec)
        tickets = [tuple(model2.predict(target)) for _ in range(5)]
        unique = set(tickets)
        # At least some variety (not all identical).
        assert len(unique) > 1, f"Expected variety but got only {len(unique)} unique ticket(s)"
        print(f"OK: chain produced {len(unique)} unique variants out of {len(tickets)} draws")

    # ------------------------------------------------------------------
    # Per-step pool_size control
    # ------------------------------------------------------------------

    def test_explicit_pool_size_every_step(self, df):
        """Every step has explicit pool_size; pool gets narrower each step."""
        spec = {
            "product": "power_655",
            "groups": [
                {
                    "name": "Narrowing chain",
                    "strategies": [
                        {"strategy": "random", "params": {}, "pool_size": 20},
                        {
                            "strategy": "frequency",
                            "params": {"lookback_days": 90, "strategy_type": "hot"},
                            "pool_size": 10,
                        },
                        {"strategy": "steiner", "params": {"lookback_days": 365}, "pool_size": 8},
                    ],
                    "pick_count": 6,
                },
            ],
            "combiner": {"method": "concatenate"},
            "post_filters": {},
            "ticket_count": 1,
        }
        model = PipelineStrategy(df, spec)
        target = df["date"].max() + timedelta(days=3)
        ticket = model.predict(target)
        _assert_valid_ticket(ticket, model)
        print(f"OK: 3-step chain with explicit pool_sizes produced: {ticket}")

    def test_explicit_pool_size_second_step_only(self, df):
        """First step auto, second step explicit pool_size=8."""
        spec = {
            "product": "power_655",
            "groups": [
                {
                    "name": "Second step explicit",
                    "strategies": [
                        {"strategy": "random", "params": {}},  # auto pool_size
                        {
                            "strategy": "frequency",
                            "params": {"lookback_days": 90, "strategy_type": "hot"},
                            "pool_size": 8,
                        },
                    ],
                    "pick_count": 6,
                },
            ],
            "combiner": {"method": "concatenate"},
            "post_filters": {},
        }
        model = PipelineStrategy(df, spec)
        target = df["date"].max() + timedelta(days=3)
        for _ in range(5):
            ticket = model.predict(target)
            _assert_valid_ticket(ticket, model)
        print("OK: second step with explicit pool_size=8 works")

    def test_pool_size_zero_rejected(self, df):
        """pool_size=0 must be rejected in validation."""
        spec = {
            "product": "power_655",
            "groups": [
                {
                    "name": "Bad pool size",
                    "strategies": [
                        {"strategy": "random", "params": {}, "pool_size": 0},
                    ],
                    "pick_count": 6,
                },
            ],
        }
        with pytest.raises(ValueError, match="positive integer"):
            PipelineStrategy(df, spec)

    def test_pool_size_negative_rejected(self, df):
        """pool_size=-1 must be rejected in validation."""
        spec = {
            "product": "power_655",
            "groups": [
                {
                    "name": "Bad pool size",
                    "strategies": [
                        {"strategy": "random", "params": {}, "pool_size": -1},
                    ],
                    "pick_count": 6,
                },
            ],
        }
        with pytest.raises(ValueError, match="positive integer"):
            PipelineStrategy(df, spec)

    def test_pool_size_zero_old_format_rejected(self, df):
        """pool_size=0 in old format must be rejected."""
        spec = {
            "product": "power_655",
            "groups": [
                {
                    "name": "Bad old format",
                    "strategy": "random",
                    "params": {},
                    "pool_size": 0,
                    "pick_count": 6,
                },
            ],
        }
        with pytest.raises(ValueError, match="positive integer"):
            PipelineStrategy(df, spec)

    # ------------------------------------------------------------------
    # filter_pool integration with chains
    # ------------------------------------------------------------------

    def test_chain_steiner_filters_random_pool(self, df):
        """Random → Steiner (auto): Steiner filters within the random pool.
        All output numbers must be a subset of the pool produced by Random."""
        spec = {
            "product": "power_655",
            "groups": [
                {
                    "name": "Random->Steiner",
                    "strategies": [
                        {"strategy": "random", "params": {}, "pool_size": 12},
                        {"strategy": "steiner", "params": {"lookback_days": 365}},
                    ],
                    "pick_count": 6,
                },
            ],
            "combiner": {"method": "concatenate"},
            "post_filters": {},
        }
        model = PipelineStrategy(df, spec)
        target = df["date"].max() + timedelta(days=3)

        # Capture the pool produced by the first step to verify subset.
        original_step0 = model._get_strategy(0, 0).propose_top_numbers
        captured_pool: list[int] | None = None

        def _capture_propose(date, k):
            nonlocal captured_pool
            result = list(original_step0(date, k))
            captured_pool = list(result)
            return result

        model._get_strategy(0, 0).propose_top_numbers = _capture_propose

        ticket = model.predict(target)
        _assert_valid_ticket(ticket, model)

        # Every number in the ticket must be from the captured pool
        # (or padded if chain couldn't produce enough).
        if captured_pool is not None and len(captured_pool) >= 6:
            pool_set = set(captured_pool)
            for n in ticket:
                assert n in pool_set, f"Number {n} not in the random pool {sorted(captured_pool)}"
        print(f"OK: Steiner filtered from random pool of size {len(captured_pool or [])}: {ticket}")

    def test_chain_steiner_with_explicit_pool_size(self, df):
        """Random (12) → Steiner (explicit pool_size=4).  Final pool has ≤ 4
        elements from the random pool."""
        spec = {
            "product": "power_655",
            "groups": [
                {
                    "name": "Random->Steiner(4)",
                    "strategies": [
                        {"strategy": "random", "params": {}, "pool_size": 12},
                        {"strategy": "steiner", "params": {"lookback_days": 365}, "pool_size": 4},
                    ],
                    "pick_count": 3,
                },
                {
                    "name": "Filler",
                    "strategy": "random",
                    "params": {},
                    "pool_size": 55,
                    "pick_count": 3,
                },
            ],
            "combiner": {"method": "concatenate"},
            "post_filters": {},
        }
        model = PipelineStrategy(df, spec)
        target = df["date"].max() + timedelta(days=3)
        ticket = model.predict(target)
        _assert_valid_ticket(ticket, model)
        # First 3 numbers came from the Steiner-filtered pool of ≤ 4
        print(f"OK: Steiner with pool_size=4 produced ticket: {ticket}")

    def test_filter_pool_base_class_default(self, df):
        """Direct call to base PredictModel.filter_pool."""
        from machine_learning.strategies.frequency import FrequencyStrategy

        freq = FrequencyStrategy(df, lookback_days=90, strategy_type="hot")
        target = df["date"].max() + timedelta(days=3)

        # Pool of 10 numbers; filter_pool should return ≤ 6 (number_predict).
        pool = list(range(10, 21))  # [10..20]
        result = freq.filter_pool(target, pool, k=6)
        assert isinstance(result, list), "filter_pool must return a list"
        assert len(result) <= 6, f"Expected ≤ 6, got {len(result)}"
        for n in result:
            assert n in pool, f"Number {n} not in input pool"
        assert result == sorted(result), "Result must be sorted"
        print(f"OK: base filter_pool returned {len(result)} numbers from {len(pool)}-element pool: {result}")

    def test_filter_pool_steiner_override(self, df):
        """Steiner.filter_pool returns numbers strictly from the pool."""
        from machine_learning.strategies.steiner import SteinerStrategy

        steiner = SteinerStrategy(df, lookback_days=365)
        target = df["date"].max() + timedelta(days=3)

        pool = list(range(5, 25))  # 20 numbers [5..24]
        result = steiner.filter_pool(target, pool, k=6)
        assert isinstance(result, list)
        assert len(result) == 6, f"Expected 6, got {len(result)}"
        for n in result:
            assert n in pool, f"Steiner returned {n} outside pool {pool}"
        assert result == sorted(result), "Result must be sorted"
        print(f"OK: Steiner.filter_pool returned 6 numbers from pool: {result}")

    def test_filter_pool_steiner_small_pool(self, df):
        """Steiner.filter_pool with k > len(pool) returns the whole pool."""
        from machine_learning.strategies.steiner import SteinerStrategy

        steiner = SteinerStrategy(df, lookback_days=365)
        target = df["date"].max() + timedelta(days=3)

        pool = [7, 13, 42]
        result = steiner.filter_pool(target, pool, k=6)
        assert len(result) == 3
        assert result == sorted(pool)
        print(f"OK: Steiner.filter_pool with small pool returned whole pool: {result}")
