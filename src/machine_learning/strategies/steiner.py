"""
Steiner system-based prediction strategy.

Builds a partial Steiner system S(t, k, v) (t-wise-disjoint k-subsets) over
the number range and selects ``number_predict`` numbers by combining the
top-scoring structural units based on historical co-occurrence.

Default systems per Vietlott product
------------------------------------

* ``power_535`` → S(2, 3, 35) — pick 5 numbers from pair-disjoint triples
* ``power_645`` → S(2, 3, 45) — pick 6 numbers from pair-disjoint triples
* ``power_655`` → S(2, 3, 55) — pick 6 numbers from pair-disjoint triples

The ``(t, k, v)`` triple is fully customisable via constructor arguments
or by setting ``steiner_system`` on the product's :class:`ProductConfig`.
When ``t == 2`` and ``k == 3`` the strategy operates as a Steiner triple
system (STS); other valid (t, k, v) combinations work via the same greedy
algorithm and may be partial systems.
"""

import math
import random
from collections import OrderedDict
from datetime import date
from itertools import combinations
from typing import Dict, List, Optional, Sequence, Tuple

import pandas as pd

from machine_learning.strategies.base import PredictModel


class SteinerStrategy(PredictModel):
    """
    Steiner system-based lottery prediction.

    Decomposes ``[min_val, min_val + v - 1]`` into ``k``-element blocks
    such that every ``t``-element sub-tuple appears in at most one block
    (a partial Steiner system S(t, k, v)).  Returns ``number_predict``
    numbers by greedily combining the top-scoring blocks ranked by
    historical co-occurrence of their internal pairs.

    Parameters
    ----------
    df:
        Historical lottery data.
    time_predict:
        Number of tickets generated per draw during backtest.
    min_val, max_val:
        Inclusive number range.
    t:
        Strength of the Steiner system — the size of sub-tuple that must
        be covered by at most one block.  ``2`` (default) means every
        pair appears in at most one block.  Only ``t == 2`` is currently
        used for ticket assembly, but the parameter is stored for
        completeness and future extensions.
    k:
        Block size — the number of elements in each Steiner block.
        ``3`` (default) gives a Steiner triple system.  Values up to
        ``number_predict`` are supported.
    v:
        Number of points in the design.  Defaults to ``max_val``
        (the pool size).  Must satisfy ``min_val + k <= v <= max_val``.
    lookback_days:
        Only use draws from the last ``lookback_days`` days for pair
        co-occurrence.  ``None`` to use all history.
    filter_consecutive:
        (k=3 only) Reject blocks containing adjacent consecutive numbers.
    filter_same_decade:
        (k=3 only) Reject blocks where all 3 numbers fall in the same decade.
    """

    # Default Steiner system per product (consumed by ``apply_product_config``).
    # Other products auto-derive S(2, 3, max_value) when no default is set.
    DEFAULT_STEINER_SYSTEM: Dict[str, Tuple[int, int, int]] = {
        "power_535": (2, 3, 35),
        "power_645": (2, 3, 45),
        "power_655": (2, 3, 55),
    }

    def __init__(
        self,
        df: pd.DataFrame,
        time_predict: int = 1,
        min_val: int = PredictModel.POWER_655_MIN_VAL,
        max_val: int = PredictModel.POWER_655_MAX_VAL,
        lookback_days: Optional[int] = 365,
        filter_consecutive: bool = True,
        filter_same_decade: bool = True,
        t: int = 2,
        k: int = 3,
        v: Optional[int] = None,
    ):
        super().__init__(df, time_predict, min_val, max_val)
        if t < 1:
            raise ValueError(f"Steiner strength t must be >= 1, got {t}")
        if k < t:
            raise ValueError(f"Block size k={k} must be >= t={t}")
        pool_size = self.max_val - self.min_val + 1
        if k > pool_size:
            raise ValueError(f"Block size k={k} is larger than the number range ({pool_size})")

        self.lookback_days = lookback_days
        self.filter_consecutive = filter_consecutive
        self.filter_same_decade = filter_same_decade
        self.t = t
        self.k = k
        # v defaults to the pool size; v <= 0 is treated as "use default".
        # Must be a positive integer in [k, max_val].
        self.v = v if (v is not None and v > 0) else self.max_val
        if self.v < k:
            raise ValueError(f"Steiner v={self.v} must be >= k={k}")
        if self.v < self.min_val:
            raise ValueError(f"Steiner v={self.v} must be >= min_val={self.min_val}")

        self._blocks: List[Tuple[int, ...]] = self._build_partial_steiner()
        self.df_sorted: pd.DataFrame = df.sort_values("date").reset_index(drop=True)
        self._pair_freq_cache: Dict[date, Dict[Tuple[int, int], int]] = {}
        self._top_tickets_cache: Dict[Tuple[date, int], List[List[int]]] = {}
        # Bounded LRU cache for the on-pool Steiner triple decomposition.
        # Keyed by ``(frozenset(pool), k, t)`` so repeated calls with the
        # same pool skip the O(n³) greedy reconstruction.  Bounded to
        # ``_max_pool_cache`` entries (~768 KB at the default size of 256).
        self._pool_blocks_cache: "OrderedDict[Tuple[frozenset, int, int], List[Tuple[int, ...]]]" = OrderedDict()
        self._max_pool_cache: int = 256
        self._call_counter: int = 0

    # ------------------------------------------------------------------
    # Steiner system metadata
    # ------------------------------------------------------------------

    @property
    def steiner_system(self) -> Tuple[int, int, int]:
        """Return the ``(t, k, v)`` triple describing this strategy's Steiner system."""
        return (self.t, self.k, self.v)

    @classmethod
    def default_steiner_system(cls, product_name: str) -> Optional[Tuple[int, int, int]]:
        """Return the default ``(t, k, v)`` triple for a Vietlott product, if any.

        ``None`` when no default is registered — callers should derive
        ``v`` from the product's ``max_value`` and use ``(2, 3, v)``.
        """
        return cls.DEFAULT_STEINER_SYSTEM.get(product_name)

    def set_steiner_system(self, t: int, k: int, v: Optional[int] = None) -> "SteinerStrategy":
        """Reconfigure this instance with a new ``(t, k, v)`` Steiner system.

        Rebuilds the Steiner blocks and clears all internal caches so
        subsequent ``predict`` / ``predict_from_pool`` calls operate on
        the new design.  Returns ``self`` for chaining — designed to be
        called from :meth:`PredictModel.apply_product_config`.

        Parameters
        ----------
        t:
            Strength (>= 1).
        k:
            Block size (>= t).
        v:
            Number of points.  ``None`` keeps the current value.
        """
        if t < 1:
            raise ValueError(f"Steiner strength t must be >= 1, got {t}")
        if k < t:
            raise ValueError(f"Block size k={k} must be >= t={t}")
        pool_size = self.max_val - self.min_val + 1
        if k > pool_size:
            raise ValueError(f"Block size k={k} is larger than the number range ({pool_size})")
        new_v = self.v if (v is None or v <= 0) else v
        if new_v < k:
            raise ValueError(f"Steiner v={new_v} must be >= k={k}")
        if new_v < self.min_val:
            raise ValueError(f"Steiner v={new_v} must be >= min_val={self.min_val}")

        self.t = t
        self.k = k
        self.v = new_v
        self._blocks = self._build_partial_steiner()
        self._pair_freq_cache.clear()
        self._top_tickets_cache.clear()
        self._pool_blocks_cache.clear()
        # Note: ``_call_counter`` is intentionally preserved so the
        # existing ``predict()`` rotation continues from where it left
        # off across product reconfigurations.
        return self

    @classmethod
    def is_valid_steiner_v(cls, v: int, k: int = 3) -> bool:
        """Check if a full S(2, k, v) Steiner system can exist.

        For S(2, 3, v) a full Steiner triple system exists iff
        ``v ≡ 1 or 3 (mod 6)``.  For other k the divisibility check is
        ``v * (v - 1) % (k * (k - 1)) == 0`` and ``v - 1 % (k - 1) == 0``.

        This is a necessary condition only — even when it holds, a full
        Steiner system may not have a known explicit construction.
        """
        if k == 3:
            return v % 6 in (1, 3)
        if v < k:
            return False
        return (v * (v - 1)) % (k * (k - 1)) == 0 and (v - 1) % (k - 1) == 0

    @staticmethod
    def is_valid_triple(
        triple: Tuple[int, int, int],
        filter_consecutive: bool = True,
        filter_same_decade: bool = True,
    ) -> bool:
        """
        Check if a triple satisfies structural filters.

        Parameters
        ----------
        triple:
            Tuple of 3 numbers (a, b, c).
        filter_consecutive:
            If True, rejects triples containing adjacent consecutive numbers (b - a == 1 or c - b == 1).
        filter_same_decade:
            If True, rejects triples where all 3 numbers are in the same decade (a // 10 == b // 10 == c // 10).
        """
        a, b, c = sorted(triple)
        if filter_consecutive and ((b - a == 1) or (c - b == 1)):
            return False
        if filter_same_decade and ((a // 10) == (b // 10) == (c // 10)):
            return False
        return True

    @staticmethod
    def _is_valid_block(
        block: Tuple[int, ...],
        k: int,
        filter_consecutive: bool,
        filter_same_decade: bool,
    ) -> bool:
        """Apply structural filters to a ``k``-element block.

        For ``k == 3`` the original triple-specific filters apply.  For
        other ``k`` the block is accepted as long as its elements are
        sorted and distinct.
        """
        if k == 3 and len(block) == 3:
            return SteinerStrategy.is_valid_triple(
                block, filter_consecutive=filter_consecutive, filter_same_decade=filter_same_decade
            )
        return len(set(block)) == len(block) == k

    # ------------------------------------------------------------------
    # Partial Steiner system construction (works for any t, k, v)
    # ------------------------------------------------------------------

    def _build_partial_steiner(self) -> List[Tuple[int, ...]]:
        """Greedy ``t``-wise-disjoint ``k``-block decomposition of ``v`` points.

        The pool of points is ``[min_val, min_val + v - 1]``.  Every
        produced block has exactly ``k`` elements and is stored in sorted
        order so the algorithm is deterministic.

        For ``t == 2`` this is the standard "pairwise-disjoint blocks"
        construction used by the previous Steiner triple system code;
        for ``t == 3`` the algorithm ensures no 3-tuple is covered twice.
        """
        v = self.v
        k = self.k
        t = self.t
        rng = list(range(self.min_val, self.min_val + v))

        blocks: List[Tuple[int, ...]] = []
        covered: set = set()  # frozensets of t-tuples already covered

        # Iterate over the lexicographically earliest uncovered t-tuple,
        # then greedily pick the (k - t) smallest remaining points to
        # form a block that doesn't re-cover any existing t-tuple.
        for anchor in combinations(rng, t):
            anchor_set = frozenset(anchor)
            anchor_sorted = sorted(anchor)
            anchor_val_set = frozenset(anchor_sorted)
            if anchor_val_set in covered:
                continue
            # Pick the (k - t) smallest points in the pool not in the anchor.
            extras: List[int] = []
            for n in rng:
                if n in anchor_set:
                    continue
                # Accept n only if every t-tuple that includes n and t-1
                # members of the partial block (anchor + already-picked
                # extras) is currently uncovered.
                conflict = False
                block_vals = anchor_sorted + extras + [n]
                for tup in combinations(block_vals, t):
                    if frozenset(tup) in covered:
                        conflict = True
                        break
                if conflict:
                    continue
                extras.append(n)
                if len(extras) == k - t:
                    break
            if len(extras) < k - t:
                # No way to complete this anchor into a full block of size k.
                continue
            block = tuple(sorted(anchor_sorted + extras))
            blocks.append(block)
            for tup in combinations(block, t):
                covered.add(frozenset(tup))

        return blocks

    # ------------------------------------------------------------------
    # Pair co-occurrence
    # ------------------------------------------------------------------

    def _pair_freq(self, target_date: date) -> Dict[Tuple[int, int], int]:
        """Pair co-occurrence count using draws strictly before target_date."""
        if target_date in self._pair_freq_cache:
            return self._pair_freq_cache[target_date]

        past = self.df_sorted[self.df_sorted["date"] < target_date]
        if self.lookback_days is not None and not past.empty:
            cutoff = target_date - pd.Timedelta(days=self.lookback_days)
            past = past[past["date"] >= cutoff]

        freq: Dict[Tuple[int, int], int] = {}
        for result in past["result"]:
            nums = sorted(int(n) for n in self._main_numbers(result))
            for a, b in combinations(nums, 2):
                key = (min(a, b), max(a, b))
                freq[key] = freq.get(key, 0) + 1

        self._pair_freq_cache[target_date] = freq
        return freq

    @staticmethod
    def _score_block(block: Sequence[int], freq: Dict[Tuple[int, int], int]) -> int:
        """Sum of pair-frequencies for all pairs in ``block``."""
        score = 0
        for a, b in combinations(sorted(block), 2):
            score += freq.get((min(a, b), max(a, b)), 0)
        return score

    # ------------------------------------------------------------------
    # Top-K candidate tickets (each = up to number_predict numbers from disjoint blocks)
    # ------------------------------------------------------------------

    def _scored_blocks(self, target_date: date) -> List[Tuple[int, int, Tuple[int, ...]]]:
        """Return all blocks (after structural filters) ranked by pair-score desc."""
        freq = self._pair_freq(target_date)
        if self.filter_consecutive or self.filter_same_decade:
            blocks = [
                b
                for b in self._blocks
                if self._is_valid_block(b, self.k, self.filter_consecutive, self.filter_same_decade)
            ]
        else:
            blocks = list(self._blocks)
        scored = [(self._score_block(b, freq), idx, b) for idx, b in enumerate(blocks)]
        scored.sort(key=lambda x: (-x[0], x[1]))
        return scored

    def _top_tickets(self, target_date: date, k: int) -> List[List[int]]:
        """Return up to ``k`` candidate tickets ordered by combined Steiner score desc.

        Each ticket is a union of :func:`_blocks_per_ticket` disjoint
        Steiner blocks.  Cached per (date, k) so multiple hybrid wrappers
        sharing one Steiner instance only pay the O(B²) cost once per date.
        """
        cache_key = (target_date, k)
        if cache_key in self._top_tickets_cache:
            return self._top_tickets_cache[cache_key]

        scored = self._scored_blocks(target_date)
        if not scored:
            self._top_tickets_cache[cache_key] = []
            return []

        blocks_per_ticket = self._blocks_per_ticket()
        result: List[List[int]] = []
        seen: set = set()
        for i, (_, _, b1) in enumerate(scored):
            if len(result) >= k:
                break
            ticket_nums: set = set(b1)
            units_left = blocks_per_ticket - 1
            for j, (_, _, b2) in enumerate(scored):
                if units_left == 0:
                    break
                if j == i:
                    continue
                if set(b2) & ticket_nums:
                    continue
                ticket_nums |= set(b2)
                units_left -= 1
            ticket = sorted(ticket_nums)[: self.number_predict]
            if len(ticket) != self.number_predict:
                continue
            key = tuple(ticket)
            if key in seen:
                continue
            seen.add(key)
            result.append(ticket)

        self._top_tickets_cache[cache_key] = result
        return result

    def _blocks_per_ticket(self) -> int:
        """Number of disjoint blocks needed to cover ``number_predict`` slots."""
        if self.k <= 0:
            return 1
        return max(1, math.ceil(self.number_predict / self.k))

    def get_top_tickets(self, target_date: date, k: int) -> List[List[int]]:
        """
        Return up to ``k`` candidate tickets ordered by combined Steiner score desc.

        Each ticket is the union of :func:`_blocks_per_ticket` disjoint
        Steiner blocks.  Used by :class:`~machine_learning.strategies.hybrid.HybridStrategy`
        to feed Steiner-proposed candidates to other strategies for voting.
        """
        return self._top_tickets(target_date, k=k)

    def get_top_numbers(self, target_date: date, k: int = 15) -> List[int]:
        """
        Return a pool of up to ``max(k, number_predict)`` unique numbers from
        the top Steiner candidates.

        Used by HybridStrategy as a constrained candidate set for voters
        to pick from using their own algorithm.  Ensures at least
        ``number_predict`` unique numbers (the minimum required for a
        valid ticket) are always returned.
        """
        effective_k = max(k, self.number_predict)
        tickets = self._top_tickets(target_date, k=max(3, (effective_k + self.k - 1) // self.k))
        seen: set = set()
        result: List[int] = []
        for ticket in tickets:
            for n in ticket:
                if n not in seen:
                    seen.add(n)
                    result.append(n)
                    if len(result) >= effective_k:
                        return result
        # Pad with remaining numbers from the Steiner pool if still short.
        for n in range(self.min_val, self.min_val + self.v):
            if n not in seen:
                result.append(n)
                seen.add(n)
                if len(result) >= effective_k:
                    break
        return result

    # ------------------------------------------------------------------
    # Constrained Steiner on a custom pool (used by InverseHybridStrategy)
    # ------------------------------------------------------------------

    @staticmethod
    def _build_steiner_on_pool(pool: List[int], k: int = 3, t: int = 2) -> List[Tuple[int, ...]]:
        """Greedy ``t``-wise-disjoint ``k``-block decomposition of a custom pool.

        ``pool`` must be a list of distinct integers.  Returned blocks
        are sorted ascending so the algorithm is deterministic.  This
        is the on-pool counterpart of :meth:`_build_partial_steiner` and
        supports any ``(t, k)`` combination.
        """
        sorted_pool = sorted(set(pool))
        n = len(sorted_pool)
        if n < k:
            return []
        if t < 1 or k < t or k > n:
            return []
        blocks: List[Tuple[int, ...]] = []
        covered: set = set()  # frozensets of t-tuples already covered

        rng = list(range(n))
        for anchor in combinations(rng, t):
            anchor_set = frozenset(anchor)
            anchor_sorted = sorted(anchor)
            anchor_vals = [sorted_pool[i] for i in anchor_sorted]
            anchor_val_set = frozenset(anchor_vals)
            if anchor_val_set in covered:
                continue
            extras: List[int] = []
            for ni in rng:
                if ni in anchor_set:
                    continue
                block_vals = anchor_vals + [sorted_pool[j] for j in extras] + [sorted_pool[ni]]
                conflict = False
                for tup in combinations(block_vals, t):
                    if frozenset(tup) in covered:
                        conflict = True
                        break
                if conflict:
                    continue
                extras.append(ni)
                if len(extras) == k - t:
                    break
            if len(extras) < k - t:
                continue
            block = tuple(sorted(anchor_vals + [sorted_pool[j] for j in extras]))
            blocks.append(block)
            for tup in combinations(block, t):
                covered.add(frozenset(tup))
        return blocks

    def _build_steiner_on_pool_cached(self, pool: List[int], k: int = 3, t: int = 2) -> List[Tuple[int, ...]]:
        """LRU-cached wrapper around :meth:`_build_steiner_on_pool`.

        The on-pool decomposition is ``O(n³)`` and depends only on the
        pool contents and the ``(k, t)`` parameters — it is independent
        of ``target_date`` and historical data.  Repeated backtest rows
        that receive the same pool from the proposer (common across
        adjacent dates) therefore hit the cache and skip the
        reconstruction.  Bounded to ``_max_pool_cache`` entries to keep
        memory fixed; the oldest entry is evicted on overflow (LRU).
        """
        key = (frozenset(pool), k, t)
        cached = self._pool_blocks_cache.get(key)
        if cached is not None:
            self._pool_blocks_cache.move_to_end(key)
            return cached
        blocks = self._build_steiner_on_pool(pool, k=k, t=t)
        self._pool_blocks_cache[key] = blocks
        if len(self._pool_blocks_cache) > self._max_pool_cache:
            self._pool_blocks_cache.popitem(last=False)
        return blocks

    def _pool_pair_freq(self, target_date: date, pool: List[int]) -> Dict[Tuple[int, int], int]:
        """Pair co-occurrence counts for pairs drawn from ``pool`` only.

        Reuses the cached :meth:`_pair_freq` and filters keys to those
        whose two endpoints are both in ``pool``.  This keeps historical
        computation amortised across many constrained-pool calls.
        """
        full = self._pair_freq(target_date)
        pool_set = set(pool)
        return {k: v for k, v in full.items() if k[0] in pool_set and k[1] in pool_set}

    def predict_from_pool(
        self,
        target_date: date,
        pool: List[int],
        coverage: int = 3,
        number_predict: Optional[int] = None,
    ) -> List[int]:
        """Pick ``number_predict`` numbers from ``pool`` using Steiner blocks.

        For ``k == 3`` (the default) the structural unit adapts to
        ``number_predict``:

        ===========  =========================  ==================================
        number_predict  Steiner structure         example
        ===========  =========================  ==================================
        3            1 triple                   [a, b, c]
        4            1 triple + 1 singleton     [a, b, c, d]
        5            1 triple + 1 disjoint pair [a, b, c, d, e]
        6            2 disjoint triples         [a, b, c, d, e, f]
        ===========  =========================  ==================================

        For other ``k`` the ticket is the union of enough disjoint blocks
        to cover ``number_predict`` slots.

        Parameters
        ----------
        target_date:
            Date for which to generate the prediction.
        pool:
            Candidate pool of distinct numbers (e.g. the 15 numbers
            proposed by another strategy).  Need not be sorted.
        coverage:
            Number of disjoint candidate tickets to produce.  The i-th
            call (modulo coverage) returns the i-th ranked ticket,
            allowing ``time_predict`` to diversify.
        number_predict:
            Number of distinct numbers in the returned ticket.  When
            ``None`` (default), uses ``self.number_predict``.  Pass an
            explicit value when the caller has a different ticket size
            than this Steiner instance (e.g. a 5/35 hybrid driving a
            steiner built with the default 6/55 size).

        Returns
        -------
        Sorted list of ``number_predict`` numbers drawn from ``pool``.
        """
        if number_predict is None:
            number_predict = self.number_predict
        sorted_pool = sorted(set(pool))
        if len(sorted_pool) < number_predict:
            # Not enough candidates — return whatever we have, padded
            # with sequential numbers from the full range if needed.
            needed = number_predict - len(sorted_pool)
            padded = (
                list(sorted_pool) + [n for n in range(self.min_val, self.max_val + 1) if n not in sorted_pool][:needed]
            )
            return sorted(padded)[:number_predict]

        pool_freq = self._pool_pair_freq(target_date, sorted_pool)

        # Fast path for k=3 — use the original unit-based decomposer.
        if self.k == 3:
            triples = self._build_steiner_on_pool_cached(sorted_pool, k=3, t=self.t)
            if not triples:
                return sorted(sorted_pool)[:number_predict]

            # Special case: number_predict <= 2 has no Steiner triple to
            # anchor on, so we just pick the highest-frequency pair /
            # singleton from the pool.
            if number_predict <= 2:
                unit = self._best_disjoint_unit(set(), [], pool_freq, number_predict, sorted_pool)
                if not unit:
                    return sorted(sorted_pool)[:number_predict]
                # Pad to number_predict when the pool has few candidates.
                if len(unit) < number_predict:
                    for n in sorted_pool:
                        if n not in unit:
                            unit.add(n)
                        if len(unit) >= number_predict:
                            break
                return sorted(unit)[:number_predict]

            units = self._decompose_into_units(number_predict)
            scored_triples = [(self._score_block(t, pool_freq), idx, t) for idx, t in enumerate(triples)]
            scored_triples.sort(key=lambda x: (-x[0], x[1]))

            steiner_tickets: List[Tuple[int, ...]] = []
            seen: set = set()
            for _, _, t1 in scored_triples:
                if len(steiner_tickets) >= coverage:
                    break
                ticket_nums: set = set(t1)
                success = True
                for unit_size in units[1:]:
                    unit_set = self._best_disjoint_unit(ticket_nums, triples, pool_freq, unit_size, sorted_pool)
                    if not unit_set:
                        success = False
                        break
                    ticket_nums |= unit_set
                if not success or len(ticket_nums) != number_predict:
                    continue
                ticket = tuple(sorted(ticket_nums))
                if ticket in seen:
                    continue
                seen.add(ticket)
                steiner_tickets.append(ticket)

            # Top up with random samples from the pool when Steiner can't
            # produce enough distinct tickets to satisfy the requested
            # coverage.  See the general-k path below for the same logic.
            random_tickets: List[Tuple[int, ...]] = []
            if len(steiner_tickets) < coverage:
                needed = coverage - len(steiner_tickets)
                for _ in range(needed):
                    if len(sorted_pool) <= number_predict:
                        sample = tuple(sorted(random.sample(sorted_pool, len(sorted_pool))))
                    else:
                        sample = tuple(sorted(random.sample(sorted_pool, number_predict)))
                    if sample in seen:
                        continue
                    seen.add(sample)
                    random_tickets.append(sample)
                    if len(random_tickets) >= needed:
                        break
                while len(random_tickets) < needed:
                    fallback = tuple(sorted_pool[:number_predict])
                    if fallback in seen:
                        for offset in range(1, len(sorted_pool)):
                            cand = tuple(sorted(sorted_pool[offset : offset + number_predict]))
                            if cand not in seen:
                                fallback = cand
                                break
                    seen.add(fallback)
                    random_tickets.append(fallback)

            tickets = steiner_tickets + random_tickets
            if not tickets:
                return sorted(sorted_pool)[:number_predict]

            idx = self._call_counter
            self._call_counter += 1
            return list(tickets[idx % len(tickets)])

        # General-k path: greedily pick disjoint blocks until we cover number_predict slots.
        blocks = self._build_steiner_on_pool_cached(sorted_pool, k=self.k, t=self.t)
        if not blocks:
            return sorted(sorted_pool)[:number_predict]

        scored = [(self._score_block(b, pool_freq), idx, b) for idx, b in enumerate(blocks)]
        scored.sort(key=lambda x: (-x[0], x[1]))

        blocks_per_ticket = max(1, math.ceil(number_predict / self.k))
        steiner_tickets: List[Tuple[int, ...]] = []
        seen: set = set()
        for _, _, b1 in scored:
            if len(steiner_tickets) >= coverage:
                break
            ticket_nums: set = set(b1)
            units_left = blocks_per_ticket - 1
            for _, _, b2 in scored:
                if units_left == 0:
                    break
                if set(b2) & ticket_nums:
                    continue
                ticket_nums |= set(b2)
                units_left -= 1
            ticket = tuple(sorted(ticket_nums))[:number_predict]
            if len(ticket) != number_predict:
                continue
            if ticket in seen:
                continue
            seen.add(ticket)
            steiner_tickets.append(ticket)

        # When the Steiner system can't produce enough disjoint blocks to
        # satisfy the requested coverage (e.g. restrictive t/k values on a
        # small pool), top up with random samples drawn from the pool.
        # Each random ticket is a uniform sample of ``number_predict``
        # elements from the pool — they preserve the proposer's signal
        # (the pool) while breaking the Steiner cycle so the caller
        # always gets the requested number of distinct tickets.
        random_tickets: List[Tuple[int, ...]] = []
        if len(steiner_tickets) < coverage:
            needed = coverage - len(steiner_tickets)
            for _ in range(needed):
                if len(sorted_pool) <= number_predict:
                    sample = tuple(sorted(random.sample(sorted_pool, len(sorted_pool))))
                else:
                    sample = tuple(sorted(random.sample(sorted_pool, number_predict)))
                if sample in seen:
                    continue
                seen.add(sample)
                random_tickets.append(sample)
                if len(random_tickets) >= needed:
                    break
            # If random sampling still produced duplicates (very small
            # pool), pad with sorted-prefix of the pool as a last resort.
            while len(random_tickets) < needed:
                fallback = tuple(sorted_pool[:number_predict])
                if fallback in seen:
                    # Shift by one to get a distinct tuple.
                    for offset in range(1, len(sorted_pool)):
                        cand = tuple(sorted(sorted_pool[offset : offset + number_predict]))
                        if cand not in seen:
                            fallback = cand
                            break
                seen.add(fallback)
                random_tickets.append(fallback)

        # The combined ticket list is ranked: all Steiner-ranked tickets
        # first, then random fallbacks.  The internal call counter cycles
        # through this combined list so successive calls return distinct
        # tickets until the coverage is exhausted.
        tickets = steiner_tickets + random_tickets
        if not tickets:
            return sorted(sorted_pool)[:number_predict]

        idx = self._call_counter
        self._call_counter += 1
        return list(tickets[idx % len(tickets)])

    # ------------------------------------------------------------------
    # Structural-unit helpers (used by predict_from_pool, k=3 path)
    # ------------------------------------------------------------------

    @staticmethod
    def _decompose_into_units(n: int) -> List[int]:
        """Decompose ``n`` into a sequence of Steiner unit sizes (3, 2, 1).

        Prefers 3-unit (triple) > 2-unit (pair) > 1-unit (singleton) so
        the resulting ticket is as "Steiner-flavoured" as possible.

        Examples
        --------
        >>> SteinerStrategy._decompose_into_units(3)
        [3]
        >>> SteinerStrategy._decompose_into_units(4)
        [3, 1]
        >>> SteinerStrategy._decompose_into_units(5)
        [3, 2]
        >>> SteinerStrategy._decompose_into_units(6)
        [3, 3]
        >>> SteinerStrategy._decompose_into_units(7)
        [3, 3, 1]
        """
        if n < 1:
            return []
        units: List[int] = []
        while n >= 3:
            units.append(3)
            n -= 3
        if n == 2:
            units.append(2)
        elif n == 1:
            units.append(1)
        return units

    def _best_disjoint_unit(
        self,
        used: set,
        triples: List[Tuple[int, ...]],
        freq: Dict[Tuple[int, int], int],
        unit_size: int,
        pool: List[int],
    ) -> set:
        """Find the best (highest-scoring) Steiner unit of ``unit_size``
        that is pair-disjoint from ``used``.

        * ``unit_size == 3`` — best disjoint triple from the partial
          Steiner system.  Score = sum of the triple's 3 internal
          pair-frequencies (delegates to :meth:`_score_block`).
        * ``unit_size == 2`` — best disjoint pair.  Iterates over all
          pairs in ``pool`` (not just those in triples) since a pair
          may be the chosen unit even when it never appeared inside a
          Steiner triple.
        * ``unit_size == 1`` — best singleton.  Score = sum of the
          number's pair-frequencies with every number in ``used``; if
          ``used`` is empty, falls back to the singleton with the
          highest sum of pair-frequencies with the rest of the pool.

        Returns an empty set if no disjoint unit can be found.
        """
        if unit_size == 3:
            best: Optional[Tuple[int, ...]] = None
            best_score = -1
            for t in triples:
                if set(t) & used:
                    continue
                s = self._score_block(t, freq)
                if s > best_score:
                    best_score = s
                    best = t
            return set(best) if best is not None else set()

        if unit_size == 2:
            best_pair: Optional[Tuple[int, int]] = None
            best_score = -1
            for i, a in enumerate(pool):
                if a in used:
                    continue
                for b in pool[i + 1 :]:
                    if b in used:
                        continue
                    s = freq.get((a, b), 0)
                    if s > best_score:
                        best_score = s
                        best_pair = (a, b)
            return set(best_pair) if best_pair is not None else set()

        if unit_size == 1:
            if not used:
                # No anchor — pick the singleton with the highest
                # aggregate pair-freq with the rest of the pool.
                best_n: Optional[int] = None
                best_score = -1
                for n in pool:
                    s = sum(freq.get((min(n, m), max(n, m)), 0) for m in pool if m != n)
                    if s > best_score:
                        best_score = s
                        best_n = n
                return {best_n} if best_n is not None else set()
            scores: Dict[int, int] = {}
            for n in pool:
                if n in used:
                    continue
                s = sum(freq.get((min(n, a), max(n, a)), 0) for a in used)
                scores[n] = s
            if not scores:
                return set()
            return {max(scores, key=lambda k: scores[k])}

        return set()

    # ------------------------------------------------------------------
    # PredictModel interface
    # ------------------------------------------------------------------

    def filter_pool(self, target_date, pool: List[int], k: int, coverage: int = 1) -> List[int]:
        """Filter a candidate pool using Steiner's native ``predict_from_pool``.

        Returns exactly ``k`` numbers from ``pool`` structured as Steiner
        blocks (or fallback if the pool or Steiner system is too small).

        Parameters
        ----------
        target_date:
            Date for which to generate the prediction.
        pool:
            Candidate pool of distinct numbers to draw from.
        k:
            Desired number of output numbers.
        coverage:
            How many distinct tickets to build internally.  Successive
            calls rotate through the ``coverage`` ranked tickets via the
            internal call counter.  Increase this when the caller wants
            more than one distinct ticket (e.g. ``coverage =
            ticket_count`` from the pipeline).
        """
        if k >= len(pool):
            return sorted(set(pool))
        picked = self.predict_from_pool(target_date, pool=list(pool), coverage=max(1, int(coverage)), number_predict=k)
        return sorted(set(picked))

    def predict(self, date: date, candidate_pool: Optional[List[int]] = None) -> List[int]:
        """Predict numbers as the i-th best union of disjoint Steiner blocks.

        Returns ``self.number_predict`` numbers by unioning
        :func:`_blocks_per_ticket` disjoint Steiner blocks and slicing
        the result.  Works for any product — 5/35 returns 5, 6/55 and
        6/45 return 6, regardless of the block size ``k``.
        """
        if candidate_pool is not None:
            return self.predict_from_pool(date, pool=list(candidate_pool), coverage=max(self.time_predict, 1))

        tickets = self._top_tickets(date, k=max(self.time_predict, 1))

        if not tickets:
            # Cold-start fallback: take the first number_predict sorted
            # numbers from the union of blocks.
            nums: List[int] = []
            for blk in self._blocks:
                for n in blk:
                    if n not in nums:
                        nums.append(n)
                    if len(nums) >= self.number_predict:
                        break
                if len(nums) >= self.number_predict:
                    break
            # Pad with sequential numbers if still short
            n = self.min_val
            while len(nums) < self.number_predict and n <= self.max_val:
                if n not in nums:
                    nums.append(n)
                n += 1
            return sorted(nums[: self.number_predict])

        idx = self._call_counter
        self._call_counter += 1
        return tickets[idx % len(tickets)]
