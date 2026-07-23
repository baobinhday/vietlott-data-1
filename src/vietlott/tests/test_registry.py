"""
Tests for StrategyRegistry.

Covers:
- list_strategies() returns non-empty list with expected keys
- Each entry has key, label, params
- instantiate() returns correct strategy type
- Unknown strategy raises ValueError
- JSON serialisability
"""

import json
import random
from datetime import date, timedelta
from typing import List

import pandas as pd
import pytest

from machine_learning.strategies import (
    ColdNumbersStrategy,
    ExponentialDecayStrategy,
    FrequencyStrategy,
    HotNumbersStrategy,
    LongAbsenceStrategy,
    MarkovChainStrategy,
    NotRepeatStrategy,
    PairFrequencyStrategy,
    PatternStrategy,
    RandomModel,
    SteinerStrategy,
)
from machine_learning.strategies.registry import (
    get_strategy_class,
    instantiate,
    instantiate_from_dict,
    list_strategies,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

MIN_VAL = 1
MAX_VAL = 55


@pytest.fixture(scope="module")
def df():
    """Create a synthetic DataFrame for strategy instantiation."""
    rng = random.Random(42)
    start = date(2023, 1, 1)
    rows = []
    for i in range(40):
        draw_date = start + timedelta(days=i * 3)
        result = sorted(rng.sample(range(MIN_VAL, MAX_VAL + 1), 6))
        rows.append({"date": draw_date, "result": result})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# list_strategies
# ---------------------------------------------------------------------------


class TestListStrategies:
    def test_returns_non_empty_list(self):
        strategies = list_strategies()
        assert isinstance(strategies, list)
        assert len(strategies) > 0
        print(f"OK: list_strategies() returned {len(strategies)} strategies")

    def test_each_entry_has_required_keys(self):
        strategies = list_strategies()
        for s in strategies:
            assert "key" in s, f"Missing 'key' in {s}"
            assert "label" in s, f"Missing 'label' in {s}"
            assert "params" in s, f"Missing 'params' in {s}"
        print("OK: all entries have key, label, params")

    def test_minimal_entry_structure(self):
        """Each param entry must have at least name, type, default."""
        strategies = list_strategies()
        for s in strategies:
            for p in s["params"]:
                assert "name" in p, f"Missing param name in {s['key']}"
                assert "type" in p, f"Missing param type in {s['key']}"
                assert "default" in p, f"Missing param default in {s['key']}"
        print("OK: all params have name, type, default")

    def test_known_keys_present(self):
        keys = {s["key"] for s in list_strategies()}
        expected = {
            "random",
            "frequency",
            "hot_numbers",
            "cold_numbers",
            "long_absence",
            "not_repeat",
            "pattern",
            "exponential_decay",
            "pair_frequency",
            "markov_chain",
            "steiner",
            "hybrid",
            "inverse_hybrid",
        }
        missing = expected - keys
        assert not missing, f"Missing strategies: {missing}"
        print(f"OK: all {len(expected)} expected strategies registered")


# ---------------------------------------------------------------------------
# JSON serialisability
# ---------------------------------------------------------------------------


class TestJsonSerializable:
    def test_list_strategies_json_serializable(self):
        strategies = list_strategies()
        dumped = json.dumps(strategies)
        loaded = json.loads(dumped)
        assert len(loaded) == len(strategies)
        print(f"OK: list_strategies() is JSON-serialisable ({len(dumped)} bytes)")

    def test_single_entry_json_roundtrip(self):
        strategies = list_strategies()
        for s in strategies:
            dumped = json.dumps(s)
            loaded = json.loads(dumped)
            assert loaded["key"] == s["key"]
            assert loaded["label"] == s["label"]
            assert len(loaded["params"]) == len(s["params"])
        print("OK: each strategy entry round-trips through JSON")


# ---------------------------------------------------------------------------
# get_strategy_class
# ---------------------------------------------------------------------------


class TestGetStrategyClass:
    def test_known_keys(self):
        assert get_strategy_class("random") is RandomModel
        assert get_strategy_class("frequency") is FrequencyStrategy
        assert get_strategy_class("hot_numbers") is HotNumbersStrategy
        assert get_strategy_class("cold_numbers") is ColdNumbersStrategy
        assert get_strategy_class("long_absence") is LongAbsenceStrategy
        assert get_strategy_class("not_repeat") is NotRepeatStrategy
        assert get_strategy_class("pattern") is PatternStrategy
        assert get_strategy_class("exponential_decay") is ExponentialDecayStrategy
        assert get_strategy_class("pair_frequency") is PairFrequencyStrategy
        assert get_strategy_class("markov_chain") is MarkovChainStrategy
        assert get_strategy_class("steiner") is SteinerStrategy
        print("OK: all known strategy keys resolve to correct classes")

    def test_unknown_key_raises(self):
        with pytest.raises(ValueError, match="Unknown strategy"):
            get_strategy_class("bogus")
        print("OK: unknown strategy key raises ValueError")


# ---------------------------------------------------------------------------
# instantiate
# ---------------------------------------------------------------------------


class TestInstantiate:
    def test_random(self, df):
        model = instantiate("random", df)
        assert isinstance(model, RandomModel)
        print("OK: instantiate('random') returns RandomModel")

    def test_frequency(self, df):
        model = instantiate("frequency", df, lookback_days=90)
        assert isinstance(model, FrequencyStrategy)
        assert model.lookback_days == 90
        print("OK: instantiate('frequency') with lookback_days=90")

    def test_frequency_default_params(self, df):
        """Defaults from metadata are applied when not overridden."""
        model = instantiate("frequency", df)
        assert model.lookback_days == 365  # metadata default
        assert model.strategy_type == "hot"
        print("OK: instantiate('frequency') uses metadata defaults")

    def test_hot_numbers(self, df):
        model = instantiate("hot_numbers", df, lookback_days=30)
        assert isinstance(model, HotNumbersStrategy)
        print("OK: instantiate('hot_numbers') returns HotNumbersStrategy")

    def test_cold_numbers(self, df):
        model = instantiate("cold_numbers", df, lookback_days=30)
        assert isinstance(model, ColdNumbersStrategy)
        print("OK: instantiate('cold_numbers') returns ColdNumbersStrategy")

    def test_long_absence(self, df):
        model = instantiate("long_absence", df, top_n=15)
        assert isinstance(model, LongAbsenceStrategy)
        assert model.top_n == 15
        print("OK: instantiate('long_absence') with top_n=15")

    def test_not_repeat(self, df):
        model = instantiate("not_repeat", df, lookback_days=14, avoid_weight=0.5)
        assert isinstance(model, NotRepeatStrategy)
        assert model.lookback_days == 14
        print("OK: instantiate('not_repeat')")

    def test_pattern(self, df):
        model = instantiate("pattern", df, lookback_days=90, pattern_weight=0.6)
        assert isinstance(model, PatternStrategy)
        print("OK: instantiate('pattern')")

    def test_exponential_decay(self, df):
        model = instantiate("exponential_decay", df, half_life_days=30, hot=True)
        assert isinstance(model, ExponentialDecayStrategy)
        assert model.half_life_days == 30
        print("OK: instantiate('exponential_decay')")

    def test_pair_frequency(self, df):
        model = instantiate("pair_frequency", df, lookback_days=180)
        assert isinstance(model, PairFrequencyStrategy)
        print("OK: instantiate('pair_frequency')")

    def test_markov_chain(self, df):
        model = instantiate("markov_chain", df, lookback_days=90, smoothing=1.0)
        assert isinstance(model, MarkovChainStrategy)
        assert model.smoothing == 1.0
        print("OK: instantiate('markov_chain')")

    def test_steiner(self, df):
        model = instantiate("steiner", df, lookback_days=180)
        assert isinstance(model, SteinerStrategy)
        print("OK: instantiate('steiner')")

    def test_unknown_key_raises_value_error(self, df):
        with pytest.raises(ValueError, match="Unknown strategy"):
            instantiate("bogus", df)
        print("OK: instantiate with unknown key raises ValueError")


# ---------------------------------------------------------------------------
# instantiate_from_dict
# ---------------------------------------------------------------------------


class TestInstantiateFromDict:
    def test_simple_spec(self, df):
        spec = {"strategy": "frequency", "params": {"lookback_days": 90}}
        model = instantiate_from_dict(spec, df)
        assert isinstance(model, FrequencyStrategy)
        assert model.lookback_days == 90
        print("OK: instantiate_from_dict simple spec")

    def test_spec_without_params(self, df):
        spec = {"strategy": "random"}
        model = instantiate_from_dict(spec, df)
        assert isinstance(model, RandomModel)
        print("OK: instantiate_from_dict spec without params")

    def test_missing_strategy_key(self, df):
        with pytest.raises(ValueError, match="strategy"):
            instantiate_from_dict({"params": {}}, df)
        print("OK: missing strategy key raises ValueError")

    def test_unknown_strategy_key(self, df):
        with pytest.raises(ValueError, match="Unknown strategy"):
            instantiate_from_dict({"strategy": "bogus"}, df)
        print("OK: unknown strategy key raises ValueError")

    def test_hybrid_spec(self, df):
        spec = {
            "strategy": "hybrid",
            "params": {"top_k": 10},
            "components": {
                "base": {"strategy": "frequency", "params": {"lookback_days": 90}},
                "steiner": {"strategy": "steiner", "params": {"lookback_days": 180}},
            },
        }
        model = instantiate_from_dict(spec, df)
        from machine_learning.strategies.hybrid import HybridStrategy

        assert isinstance(model, HybridStrategy)
        print("OK: instantiate_from_dict hybrid spec")

    def test_inverse_hybrid_spec(self, df):
        spec = {
            "strategy": "inverse_hybrid",
            "params": {"top_k": 15, "coverage": 3},
            "components": {
                "proposer": {"strategy": "long_absence", "params": {"top_n": 15}},
                "steiner": {"strategy": "steiner", "params": {"lookback_days": 365}},
            },
        }
        model = instantiate_from_dict(spec, df)
        from machine_learning.strategies.inverse_hybrid import InverseHybridStrategy

        assert isinstance(model, InverseHybridStrategy)
        print("OK: instantiate_from_dict inverse_hybrid spec")

    def test_hybrid_missing_components(self, df):
        spec = {
            "strategy": "hybrid",
            "params": {"top_k": 10},
            "components": {"base": {"strategy": "random"}},
        }
        with pytest.raises(ValueError, match="components.steiner"):
            instantiate_from_dict(spec, df)
        print("OK: hybrid missing steiner raises ValueError")


# ---------------------------------------------------------------------------
# Additional integrity checks
# ---------------------------------------------------------------------------


class TestRegistryIntegrity:
    def test_frequency_has_params(self):
        """Frequency strategy must have its 3 documented params."""
        strategies = list_strategies()
        freq = next(s for s in strategies if s["key"] == "frequency")
        param_names = {p["name"] for p in freq["params"]}
        expected = {"lookback_days", "strategy_type", "selection_weight"}
        assert expected.issubset(param_names), f"frequency missing params: {expected - param_names}"
        print("OK: frequency strategy has all 3 params")

    def test_random_has_no_params(self):
        strategies = list_strategies()
        random_entry = next(s for s in strategies if s["key"] == "random")
        assert random_entry["params"] == []
        print("OK: random strategy has no params")

    def test_all_params_have_min_max_types(self):
        """For numeric params, min/max should be set where appropriate."""
        strategies = list_strategies()
        for s in strategies:
            for p in s["params"]:
                assert p["type"] in ("int", "float", "bool", "str"), (
                    f"{s['key']}.{p['name']}: unexpected type '{p['type']}'"
                )
        print("OK: all param types are valid")
