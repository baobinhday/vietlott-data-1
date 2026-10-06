"""Positional (slot-wise) empirical ticket generator.

Rationale
---------
Every other strategy in this package models *numbers* (frequency,
absence), *pairs* (co-occurrence, Steiner) or *structure* (Pattern).
None models the **sorted positions** of a draw.  When the ``k`` drawn
main numbers are sorted ascending, slot 1 is necessarily small and slot
``k`` large, and each slot has its own empirical marginal distribution.
This strategy estimates those ``k`` slot marginals from history and
samples each slot independently, producing tickets whose *shape* matches
the historical slot marginals.

Honesty note on expected value
------------------------------
Sampling the empirical slot marginals is exactly equivalent to drawing
the same uniform ticket by a different factorisation.  The expected
value is therefore **identical to uniform random** tickets — no ticket
is more likely than any other and the per-draw win probability is
unchanged.  The novelty is *distribution-matched ticket shapes* (which
slot each number tends to occupy), not any edge.

Determinism
-----------
The RNG is seeded from ``(date, call-order)`` so a replay of the same
date sequence reproduces the same tickets.  The histograms are cached
per ``(min_val, max_val, number_predict, pool)`` and built once.
"""

from __future__ import annotations

import random
from collections import Counter

from machine_learning.strategies.base import PredictModel


class SlotSamplerStrategy(PredictModel):
    """Sample one number per sorted slot from the empirical slot marginals.

    Parameters
    ----------
    df:
        Historical lottery data; only the ``result`` column (main numbers)
        is read to build the per-slot histograms.
    time_predict:
        Number of tickets generated per draw during backtesting.
    min_val, max_val:
        Inclusive number range.
    lookback_days:
        Contract-only parameter, accepted for registry consistency and
        ignored (the histograms are built once from the whole frame).
    """

    def __init__(
        self,
        df,
        time_predict: int = 1,
        min_val: int = PredictModel.POWER_655_MIN_VAL,
        max_val: int = PredictModel.POWER_655_MAX_VAL,
        lookback_days: int = 365,
    ):
        """Create the strategy; ``lookback_days`` is contract-only and unused."""
        super().__init__(df, time_predict=time_predict, min_val=min_val, max_val=max_val)
        self.lookback_days = int(lookback_days)
        self._hist_cache: dict[tuple, list[tuple[list[int], list[int]]]] = {}
        self._call_counter: dict[tuple, int] = {}

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _pool_tag(pool: tuple[int, ...]) -> str:
        """Stable, hash-seed-independent signature for a pool."""
        return ",".join(str(n) for n in pool)

    def _build_histograms(self, pool: tuple[int, ...]) -> list[tuple[list[int], list[int]]]:
        """Return per-slot ``(values, weights)`` histograms over ``pool``.

        Slot ``i`` tallies the ``i``-th smallest main number across every
        historical draw (only values inside ``pool``).  An empty slot
        falls back to a uniform distribution over the pool.
        """
        k = int(self.number_predict)
        counts: list[Counter] = [Counter() for _ in range(k)]
        pool_set = set(pool)
        df = self.df
        if df is not None and len(df):
            for result in df[self.col_result]:
                mains = sorted(self._main_numbers(result))
                for i in range(min(k, len(mains))):
                    value = int(mains[i])
                    if value in pool_set:
                        counts[i][value] += 1
        histograms: list[tuple[list[int], list[int]]] = []
        for counter in counts:
            if counter:
                values = sorted(counter)
                weights = [counter[v] for v in values]
            else:
                values = list(pool)
                weights = [1] * len(pool)
            histograms.append((values, weights))
        return histograms

    def _histograms(self, pool: tuple[int, ...]) -> list[tuple[list[int], list[int]]]:
        """Return the cached histograms for ``pool``, building on first use."""
        key = (self.min_val, self.max_val, int(self.number_predict), self._pool_tag(pool))
        histograms = self._hist_cache.get(key)
        if histograms is None:
            histograms = self._build_histograms(pool)
            self._hist_cache[key] = histograms
        return histograms

    @staticmethod
    def _repair(
        samples: list[int],
        histograms: list[tuple[list[int], list[int]]],
        pool: tuple[int, ...],
        rng: random.Random,
        k: int,
    ) -> list[int]:
        """Sort-repair ``samples`` into ``k`` distinct values.

        Duplicate slots are resampled from their own histogram (max 20
        rounds); if collisions stubbornly persist the remaining slots are
        filled deterministically with unused pool values so the contract
        (``k`` distinct numbers) always holds.
        """
        tries = 0
        while len(set(samples)) < k and tries < 20:
            for value, count in Counter(samples).items():
                if count > 1:
                    dup_indices = [i for i, x in enumerate(samples) if x == value]
                    for i in dup_indices[1:]:
                        values, weights = histograms[i]
                        samples[i] = rng.choices(values, weights=weights, k=1)[0]
            tries += 1
        if len(set(samples)) < k:
            used: set[int] = set()
            kept: list[int] = []
            for value in samples:
                if value not in used:
                    kept.append(value)
                    used.add(value)
            unused = [n for n in pool if n not in used]
            rng.shuffle(unused)
            for value in unused:
                if len(kept) >= k:
                    break
                kept.append(value)
                used.add(value)
            samples = kept
        return samples

    # ------------------------------------------------------------------
    # Prediction
    # ------------------------------------------------------------------

    def predict(self, date=None, candidate_pool=None):
        """Return the next slot-sampled ticket for ``date``.

        Each of the ``k`` slots is drawn independently from its empirical
        marginal, then the sample set is repaired to ``k`` distinct
        numbers and sorted.  Successive calls for the same date use an
        incrementing counter in the seed, so the tickets differ.

        When ``candidate_pool`` is given the histograms are restricted to
        the pool and every output number stays inside it.  Raises
        ``ValueError`` when the pool is smaller than ``number_predict``.
        """
        if candidate_pool is not None:
            pool = tuple(sorted({int(n) for n in candidate_pool}))
            if len(pool) < self.number_predict:
                raise ValueError(f"candidate pool too small: {len(pool)} < {self.number_predict}")
        else:
            pool = tuple(range(self.min_val, self.max_val + 1))
            if len(pool) < self.number_predict:  # pragma: no cover - defensive
                raise ValueError(f"number range too small: {len(pool)} < {self.number_predict}")

        histograms = self._histograms(pool)
        counter_key = (str(date), self._pool_tag(pool), int(self.number_predict))
        idx = self._call_counter.get(counter_key, 0)
        self._call_counter[counter_key] = idx + 1

        rng = random.Random(f"slotsample|{date}|{idx}")
        k = int(self.number_predict)
        samples = [rng.choices(values, weights=weights, k=1)[0] for values, weights in histograms]
        samples = self._repair(samples, histograms, pool, rng, k)
        return sorted(samples)
