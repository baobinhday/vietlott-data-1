"""
Strategy registry — maps string keys to strategy classes and their parameter metadata.

Provides lookup, listing, and instantiation services used by the API layer and
the ``PipelineStrategy``.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Type

import pandas as pd

from machine_learning.strategies import (
    ColdNumbersStrategy,
    ExponentialDecayStrategy,
    FrequencyStrategy,
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

# ------------------------------------------------------------------
# Metadata types
# ------------------------------------------------------------------


@dataclass
class ParamDef:
    """Metadata for a single strategy parameter."""

    name: str
    type: str  # "int", "float", "bool", "str"
    default: Any
    min: Optional[Any] = None
    max: Optional[Any] = None
    description: str = ""


@dataclass
class StrategyDef:
    """Metadata for a registered strategy."""

    key: str
    label: str
    description: str
    cls: Type[PredictModel]
    params: List[ParamDef] = field(default_factory=list)


# ------------------------------------------------------------------
# Internal registry
# ------------------------------------------------------------------

_REGISTRY: Dict[str, StrategyDef] = {}


def _register(
    key: str,
    label: str,
    description: str,
    params: List[ParamDef],
    cls: Type[PredictModel],
) -> None:
    _REGISTRY[key] = StrategyDef(key=key, label=label, description=description, params=params, cls=cls)


# ------------------------------------------------------------------
# Register all strategies — parameter metadata must be exhaustive
# ------------------------------------------------------------------

_register(
    "random",
    "Random",
    "Pure random baseline — numbers are selected uniformly at random with no use of historical data.",
    [],
    RandomModel,
)

_register(
    "frequency",
    "Frequency (Hot/Cold)",
    "Selects numbers weighted by their draw frequency over a configurable lookback window.",
    [
        ParamDef("lookback_days", "int", 365, 7, 1825, "Number of days to analyse for frequency"),
        ParamDef("strategy_type", "str", "hot", None, None, "hot, cold, or balanced"),
        ParamDef("selection_weight", "float", 0.8, 0.0, 1.0, "Weight for frequency-based selection vs random"),
    ],
    FrequencyStrategy,
)

_register(
    "hot_numbers",
    "Hot Numbers",
    "Convenience strategy locked to hot (frequently drawn) mode.",
    [
        ParamDef("lookback_days", "int", 365, 7, 1825, "Number of days to analyse for frequency"),
        ParamDef("selection_weight", "float", 0.8, 0.0, 1.0, "Weight for frequency-based selection vs random"),
    ],
    HotNumbersStrategy,
)

_register(
    "cold_numbers",
    "Cold Numbers",
    "Convenience strategy locked to cold (rarely drawn) mode.",
    [
        ParamDef("lookback_days", "int", 365, 7, 1825, "Number of days to analyse for frequency"),
        ParamDef("selection_weight", "float", 0.8, 0.0, 1.0, "Weight for frequency-based selection vs random"),
    ],
    ColdNumbersStrategy,
)

_register(
    "long_absence",
    "Long Absence",
    "Favours numbers that have not appeared for the longest time (overdue numbers).",
    [
        ParamDef("top_n", "int", 10, 5, 55, "Pool size of longest-absent numbers to sample from"),
    ],
    LongAbsenceStrategy,
)

_register(
    "not_repeat",
    "Not Repeat",
    "Avoids numbers that appeared in recent draws.",
    [
        ParamDef("lookback_days", "int", 30, 1, 365, "Number of days to look back for recent numbers"),
        ParamDef("avoid_weight", "float", 0.7, 0.0, 1.0, "Probability of avoiding recently drawn numbers"),
    ],
    NotRepeatStrategy,
)

_register(
    "pattern",
    "Pattern",
    "Analyses spacing between consecutive drawn numbers and range distribution to generate structurally plausible tickets.",
    [
        ParamDef("lookback_days", "int", 180, 7, 1825, "Rolling window (days) for spacing and range statistics"),
        ParamDef("pattern_weight", "float", 0.6, 0.0, 1.0, "Fraction of ticket filled with pattern-derived numbers"),
    ],
    PatternStrategy,
)

_register(
    "exponential_decay",
    "Exponential Decay",
    "Like frequency but uses exponentially-decaying weights so recent draws contribute more than old ones.",
    [
        ParamDef("half_life_days", "int", 90, 1, 730, "Days after which a draw's contribution is halved"),
        ParamDef("hot", "bool", True, None, None, "True → prefer recently frequent; False → recently rare"),
        ParamDef("selection_weight", "float", 0.8, 0.0, 1.0, "Fraction of ticket filled from score-weighted pool"),
    ],
    ExponentialDecayStrategy,
)

_register(
    "pair_frequency",
    "Pair Frequency",
    "Builds a co-occurrence matrix and greedily selects numbers that historically appear together.",
    [
        ParamDef("lookback_days", "int", 365, 7, 1825, "Rolling window (days) for co-occurrence counts"),
    ],
    PairFrequencyStrategy,
)

_register(
    "markov_chain",
    "Markov Chain",
    "Models first-order sequential dependencies between consecutive draws via a transition matrix.",
    [
        ParamDef("lookback_days", "int", 365, 7, 1825, "Rolling window (days) for the transition matrix"),
        ParamDef("smoothing", "float", 0.5, 0.0, 5.0, "Laplace smoothing constant added to every transition count"),
    ],
    MarkovChainStrategy,
)

_register(
    "steiner",
    "Steiner Triple",
    "Decomposes the number range into pair-disjoint triples (partial Steiner triple system) and selects numbers via pair co-occurrence.",
    [
        ParamDef("lookback_days", "int", 365, 7, 1825, "Only use draws from this many days for pair co-occurrence"),
    ],
    SteinerStrategy,
)

_register(
    "hybrid",
    "Hybrid (Steiner → Voter)",
    "Two-stage strategy: Steiner proposes a top-K candidate pool, then a voter strategy picks from it.",
    [
        ParamDef("top_k", "int", 10, 5, 55, "Size of the Steiner candidate number pool"),
    ],
    HybridStrategy,
)

_register(
    "inverse_hybrid",
    "Inverse Hybrid (Proposer → Steiner)",
    "Structural mirror of hybrid: a proposer strategy outputs a top-K pool and Steiner picks from it.",
    [
        ParamDef("top_k", "int", 15, 5, 55, "Size of the proposer's candidate number pool"),
        ParamDef("coverage", "int", 3, 1, 10, "Number of disjoint Steiner ticket candidates to generate"),
    ],
    InverseHybridStrategy,
)


# ------------------------------------------------------------------
# Public API
# ------------------------------------------------------------------


def get_strategy_class(key: str) -> Type[PredictModel]:
    """Return the strategy class for a given registry key.

    Raises ValueError if *key* is not registered.
    """
    if key not in _REGISTRY:
        available = ", ".join(sorted(_REGISTRY))
        raise ValueError(f"Unknown strategy: '{key}'. Available: {available}")
    return _REGISTRY[key].cls


def list_strategies() -> List[dict]:
    """Return a JSON-serialisable list of strategy metadata dicts.

    Each entry has the keys: ``key``, ``label``, ``description``, ``params``.
    Every value is a built-in Python type (safe for ``json.dumps``).
    """
    result: List[dict] = []
    for sd in _REGISTRY.values():
        entry: dict = {
            "key": sd.key,
            "label": sd.label,
            "description": sd.description,
            "params": [
                {
                    "name": p.name,
                    "type": p.type,
                    "default": p.default,
                    "min": p.min,
                    "max": p.max,
                    "description": p.description,
                }
                for p in sd.params
            ],
        }
        result.append(entry)
    return result


def instantiate(key: str, df: pd.DataFrame, **params) -> PredictModel:
    """Construct a strategy instance by registry *key*.

    Parameters not provided will use their default values from the registry
    metadata.  Extra keyword arguments are forwarded to the strategy
    constructor unchanged.
    """
    cls = get_strategy_class(key)
    sd = _REGISTRY[key]

    kwargs: dict = {}
    for p in sd.params:
        if p.name in params:
            kwargs[p.name] = params[p.name]
        elif p.default is not None:
            kwargs[p.name] = p.default

    # Include any extra params not in the registry (e.g. time_predict)
    for k, v in params.items():
        if k not in kwargs:
            kwargs[k] = v

    return cls(df, **kwargs)


def instantiate_from_dict(spec: dict, df: pd.DataFrame) -> PredictModel:
    """Construct a strategy from a JSON-compatible spec dictionary.

    Simple spec (leaf strategy)
    ---------------------------
    ``{"strategy": "frequency", "params": {"lookback_days": 90}}``

    Composite spec (hybrid / inverse_hybrid)
    ----------------------------------------
    ``{"strategy": "hybrid", "params": {"top_k": 10}, "components": {...}}``

    The ``components`` dict must contain ``"base"`` and ``"steiner"`` (for
    hybrid) or ``"proposer"`` and ``"steiner"`` (for inverse_hybrid), each
    being a nested spec dict.

    Raises
    ------
    ValueError
        If *spec* lacks a ``"strategy"`` key, or the strategy is unknown,
        or required components are missing.
    """
    if "strategy" not in spec:
        raise ValueError("Spec dict must contain a 'strategy' key")

    key = spec["strategy"]
    params = spec.get("params", {})

    if key == "hybrid":
        return _instantiate_hybrid(spec, df)
    if key == "inverse_hybrid":
        return _instantiate_inverse_hybrid(spec, df)
    return instantiate(key, df, **params)


# ------------------------------------------------------------------
# Composite instantiation helpers
# ------------------------------------------------------------------


def _instantiate_hybrid(spec: dict, df: pd.DataFrame) -> HybridStrategy:
    """Construct a HybridStrategy from a spec dict with nested components."""
    components = spec.get("components", {})
    base_spec = components.get("base")
    steiner_spec = components.get("steiner")

    if not base_spec:
        raise ValueError("HybridStrategy spec must include 'components.base'")
    if not steiner_spec:
        raise ValueError("HybridStrategy spec must include 'components.steiner'")

    base: PredictModel = instantiate_from_dict(base_spec, df)
    steiner_raw: PredictModel = instantiate_from_dict(steiner_spec, df)
    if not isinstance(steiner_raw, SteinerStrategy):
        raise ValueError("HybridStrategy 'components.steiner' must resolve to a SteinerStrategy")

    params = spec.get("params", {})
    top_k: int = params.get("top_k", 10)
    time_predict: int = params.get("time_predict", 1)

    return HybridStrategy(base=base, steiner=steiner_raw, top_k=top_k, time_predict=time_predict)


def _instantiate_inverse_hybrid(spec: dict, df: pd.DataFrame) -> InverseHybridStrategy:
    """Construct an InverseHybridStrategy from a spec dict with nested components."""
    components = spec.get("components", {})
    proposer_spec = components.get("proposer")
    steiner_spec = components.get("steiner")

    if not proposer_spec:
        raise ValueError("InverseHybridStrategy spec must include 'components.proposer'")
    if not steiner_spec:
        raise ValueError("InverseHybridStrategy spec must include 'components.steiner'")

    proposer: PredictModel = instantiate_from_dict(proposer_spec, df)
    steiner_raw: PredictModel = instantiate_from_dict(steiner_spec, df)
    if not isinstance(steiner_raw, SteinerStrategy):
        raise ValueError("InverseHybridStrategy 'components.steiner' must resolve to a SteinerStrategy")

    params = spec.get("params", {})
    top_k: int = params.get("top_k", 15)
    coverage: int = params.get("coverage", 3)
    time_predict: int = params.get("time_predict", 1)

    return InverseHybridStrategy(
        proposer=proposer, steiner=steiner_raw, top_k=top_k, coverage=coverage, time_predict=time_predict
    )
