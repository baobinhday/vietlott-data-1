"""Shared-core cluster ("burst") ticket generator.

Design goal
-----------
Maximise the number of tickets that win *simultaneously* in a single draw.
Every ticket in a draw shares a common ``core_size``-number core; the
remaining ``number_predict - core_size`` slots are filled from disjoint
"tails".  If the core is among the drawn numbers, every ticket that also
matches its tail can win at once — a *burst* of simultaneous wins.

Honesty note on expected value
------------------------------
The expected **value** of this design is identical to that of diversified
tickets: by linearity of expectation, the sum of the per-ticket win
probabilities does not depend on how the tickets are correlated.  What
changes is the **shape of the outcome distribution**: a cluster produces
bursty simultaneous wins (many tickets win together, or none do) instead
of the steadier trickle of independent diversified tickets.  Because
Vietlott pays a fixed per-winner amount on the lower tiers, that
burstiness does not by itself add value — it exists to satisfy the
product's stated "many simultaneous small wins per draw" objective.

All existing strategies deliberately diversify their tickets; this one is
the deliberate opposite.  No frequency / Markov / pattern / Steiner /
anti-popularity signal is reused here.

Why the core is uniform-random
------------------------------
Every ``core_size``-number core has exactly the same probability of
appearing in a draw (by symmetry of the draw).  A historically "hot"
core is not more likely to come up, so frequency-style scoring would only
add overfitting risk.  The core is therefore sampled uniformly at random.
Determinism is provided purely so backtests and tests are reproducible.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from machine_learning.strategies.base import PredictModel


@dataclass
class _ClusterLayout:
    """Per-(date, range, pool) cluster design: one shared core + tail chunks.

    A layout owns the core and a lazily-grown list of "rounds".  Round 0 is
    built from the base date-seeded RNG; further rounds (only needed when
    ``time_predict`` exceeds the number of chunks in one round) reshuffle
    the remaining numbers with a counter-salted seed.
    """

    core: tuple[int, ...]
    pool: tuple[int, ...]
    tail_size: int
    base_seed: str
    _rounds: list[list[tuple[int, ...]]] = field(default_factory=list)

    @property
    def num_chunks(self) -> int:
        """Number of disjoint tail chunks produced per round (>= 1)."""
        remaining = len(self.pool) - len(self.core)
        return max(1, remaining // self.tail_size)

    def _build_round(self, round_idx: int) -> list[tuple[int, ...]]:
        """Return the ``round_idx``-th disjoint chunking of the remaining numbers."""
        rng = random.Random(f"{self.base_seed}|round|{round_idx}")
        core_set = set(self.core)
        remaining = [n for n in self.pool if n not in core_set]
        rng.shuffle(remaining)
        chunks: list[tuple[int, ...]] = []
        # Only full-size chunks are kept so every emitted ticket has exactly
        # ``number_predict`` numbers.  Leftover numbers are simply unused.
        for i in range(0, len(remaining) - self.tail_size + 1, self.tail_size):
            chunks.append(tuple(sorted(remaining[i : i + self.tail_size])))
        return chunks

    def chunks_for_round(self, round_idx: int) -> list[tuple[int, ...]]:
        """Return chunks for ``round_idx``, building (and caching) on demand."""
        while len(self._rounds) <= round_idx:
            self._rounds.append(self._build_round(len(self._rounds)))
        return self._rounds[round_idx]


class ClusterStrategy(PredictModel):
    """Shared-core "burst" strategy: all tickets in a draw share a common core.

    Parameters
    ----------
    df:
        Historical lottery data.  Unused for number selection (the core is
        deliberately uniform-random); kept for the ``PredictModel`` contract.
    time_predict:
        Number of tickets generated per draw during backtesting.
    min_val, max_val:
        Inclusive number range.
    core_size:
        Number of shared numbers every ticket contains.  Clamped to
        ``[1, number_predict - 1]`` so tails always exist.
    lookback_days:
        Contract-only parameter, accepted for registry consistency and
        ignored (this strategy never reads historical draws).
    """

    def __init__(
        self,
        df,
        time_predict: int = 1,
        min_val: int = PredictModel.POWER_655_MIN_VAL,
        max_val: int = PredictModel.POWER_655_MAX_VAL,
        core_size: int = 3,
        lookback_days: int = 365,
    ):
        """Create the strategy; ``lookback_days`` is contract-only and unused."""
        super().__init__(df, time_predict=time_predict, min_val=min_val, max_val=max_val)
        self.core_size = int(core_size)
        self.lookback_days = int(lookback_days)
        self._layouts: dict[tuple, _ClusterLayout] = {}
        self._call_counter: dict[tuple, int] = {}

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _effective_core_size(self) -> int:
        """Clamp ``core_size`` to ``[1, number_predict - 1]`` so tails exist."""
        return max(1, min(self.core_size, int(self.number_predict) - 1))

    @staticmethod
    def _pool_tag(pool: tuple[int, ...]) -> str:
        """Stable, hash-seed-independent signature for a pool."""
        return ",".join(str(n) for n in pool)

    def _build_layout(self, date, pool: tuple[int, ...]) -> _ClusterLayout:
        """Deterministically build the shared core + tail seed for ``date``/``pool``."""
        core_size = self._effective_core_size()
        tail_size = int(self.number_predict) - core_size
        tag = self._pool_tag(pool)
        full_pool = tuple(range(self.min_val, self.max_val + 1))
        if pool == full_pool:
            # Exact seed from the design contract for the full-range case.
            core_seed = f"cluster-core|{date}|{self.min_val}|{self.max_val}"
            base_seed = f"cluster-tails|{date}|{self.min_val}|{self.max_val}"
        else:
            core_seed = f"cluster-core|{date}|{self.min_val}|{self.max_val}|{tag}"
            base_seed = f"cluster-tails|{date}|{self.min_val}|{self.max_val}|{tag}"
        core_rng = random.Random(core_seed)
        core = tuple(sorted(core_rng.sample(list(pool), core_size)))
        return _ClusterLayout(core=core, pool=pool, tail_size=tail_size, base_seed=base_seed)

    # ------------------------------------------------------------------
    # Prediction
    # ------------------------------------------------------------------

    def predict(self, date=None, candidate_pool=None):
        """Return the next cluster ticket for ``date`` (deterministic per call order).

        Successive calls for the same date return tickets that share the
        same core and use disjoint tails, until the tails are exhausted and
        the remaining numbers are reshuffled (counter-salted seed) for the
        next round.

        When ``candidate_pool`` is given, the core and tails are drawn from
        the sorted pool instead of the full range.  Raises ``ValueError``
        when the pool is smaller than ``number_predict`` (mirrors
        ``packing.py``).
        """
        if candidate_pool is not None:
            pool = tuple(sorted({int(n) for n in candidate_pool}))
            if len(pool) < self.number_predict:
                raise ValueError(f"candidate pool too small: {len(pool)} < {self.number_predict}")
        else:
            pool = tuple(range(self.min_val, self.max_val + 1))
            if len(pool) < self.number_predict:  # pragma: no cover - defensive
                raise ValueError(f"number range too small: {len(pool)} < {self.number_predict}")

        tag = self._pool_tag(pool)
        layout_key = (str(date), self.min_val, self.max_val, self.number_predict, pool)
        layout = self._layouts.get(layout_key)
        if layout is None:
            layout = self._build_layout(date, pool)
            self._layouts[layout_key] = layout

        # Per-date (and per-pool) call counter — ticket i mod num_chunks.
        counter_key = (str(date), tag, self.min_val, self.max_val, self.number_predict)
        idx = self._call_counter.get(counter_key, 0)
        self._call_counter[counter_key] = idx + 1

        num_chunks = layout.num_chunks
        round_idx, pos = divmod(idx, num_chunks)
        chunks = layout.chunks_for_round(round_idx)
        tail = chunks[pos % len(chunks)]
        return sorted(set(layout.core) | set(tail))

    # ------------------------------------------------------------------
    # Proposal (used when this strategy is a voter in a hybrid chain)
    # ------------------------------------------------------------------

    def propose_top_numbers(self, target_date, k: int):
        """Return a deterministic ``k``-number pool led by the date's core.

        The core is included first (then the rest of the range in order) so
        hybrid chains consuming this proposal keep the shared-core flavour.
        The result is returned sorted, matching the base contract.
        """
        pool = list(range(self.min_val, self.max_val + 1))
        layout = self._build_layout(target_date, tuple(pool))
        result: list[int] = list(layout.core)
        for n in pool:
            if n not in result:
                result.append(n)
            if len(result) >= k:
                break
        return sorted(result[:k])
