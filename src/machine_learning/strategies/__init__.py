"""
Lottery prediction strategy implementations.

Available strategies
--------------------
PredictModel
    Abstract base class all strategies inherit from.
RandomModel
    Pure random baseline — numbers are selected uniformly at random with no
    use of historical data.
FrequencyStrategy
    Selects numbers weighted by their draw frequency over a configurable
    lookback window.  Use ``strategy_type="hot"`` to favour the most
    frequently drawn numbers or ``"cold"`` to favour the least frequent.
HotNumbersStrategy
    Convenience subclass of ``FrequencyStrategy`` locked to ``"hot"`` mode.
ColdNumbersStrategy
    Convenience subclass of ``FrequencyStrategy`` locked to ``"cold"`` mode.
LongAbsenceStrategy
    Favours numbers that have not appeared for the longest time, under the
    assumption that overdue numbers are more likely to appear.
NotRepeatStrategy
    Avoids numbers that appeared in recent draws, preferring numbers that
    have not been drawn in the most recent ``lookback_days`` window.
PatternStrategy
    Analyses spacing between consecutive drawn numbers and range distribution
    across five equal sub-ranges to generate structurally plausible tickets.
ExponentialDecayStrategy
    Like FrequencyStrategy but uses exponentially-decaying weights so recent
    draws contribute more than old ones, with no hard window cutoff.
PairFrequencyStrategy
    Builds a co-occurrence matrix and greedily selects numbers that
    historically appear together, capturing second-order correlations.
MarkovChainStrategy
    Models first-order sequential dependencies between consecutive draws.
    Builds a transition matrix T[a][b] counting how often number ``a``
    in draw ``t`` was followed by number ``b`` in draw ``t+1``, then
    scores candidates based on the previous draw's composition.
SteinerStrategy
    Decomposes the number range into 3-element pair-disjoint triples
    (a partial Steiner triple system) and selects 6 numbers by finding
    two disjoint triples whose historical pair co-occurrence is highest.
HybridStrategy
    Two-stage strategy: a Steiner proposer generates a top-K candidate
    number pool, and a voter strategy is invoked with ``candidate_pool``
    set to that pool.  The voter runs its own original algorithm
    constrained to the pool, so each hybrid produces a distinct output.
InverseHybridStrategy
    Structural mirror of ``HybridStrategy``: a proposer strategy (any
    ``PredictModel`` subclass) emits a top-K candidate pool and Steiner
    picks ``number_predict`` numbers from that pool using its pair-disjoint
    triple decomposition with configurable coverage.  Useful when you want
    the proposer's signal to narrow the search space but the final ticket
    to satisfy the Steiner structural constraint.
"""

from .base import PredictModel
from .exponential_decay import ExponentialDecayStrategy
from .frequency import ColdNumbersStrategy, FrequencyStrategy, HotNumbersStrategy
from .hybrid import HybridStrategy
from .inverse_hybrid import InverseHybridStrategy
from .inverse_hybrid_trio import InverseHybridTrioStrategy
from .long_absence import LongAbsenceStrategy
from .markov_chain import MarkovChainStrategy
from .not_repeat import NotRepeatStrategy
from .pair_frequency import PairFrequencyStrategy
from .pattern import PatternStrategy
from .random_strategy import RandomModel
from .steiner import SteinerStrategy

__all__ = [
    "PredictModel",
    "RandomModel",
    "FrequencyStrategy",
    "HotNumbersStrategy",
    "ColdNumbersStrategy",
    "NotRepeatStrategy",
    "PatternStrategy",
    "LongAbsenceStrategy",
    "ExponentialDecayStrategy",
    "PairFrequencyStrategy",
    "MarkovChainStrategy",
    "SteinerStrategy",
    "HybridStrategy",
    "InverseHybridStrategy",
    "InverseHybridTrioStrategy",
]
