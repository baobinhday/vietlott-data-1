"""
Steiner triple system-based prediction strategy.

Builds a partial Steiner triple system (pair-disjoint 3-subsets) over the
number range and selects 6 numbers by finding two disjoint triples with
the highest combined historical pair co-occurrence.
"""

from datetime import date
from itertools import combinations
from typing import Dict, List, Optional, Tuple

import pandas as pd

from machine_learning.strategies.base import PredictModel


class SteinerStrategy(PredictModel):
    """
    Steiner triple system-based lottery prediction.

    Decomposes ``[min_val, max_val]`` into 3-element triples (a partial
    Steiner system: every pair appears in at most one triple) and returns
    6 numbers by selecting the two disjoint triples with the highest sum
    of historical pair co-occurrence.

    Parameters
    ----------
    df:
        Historical lottery data.
    time_predict:
        Number of tickets generated per draw during backtest.
    min_val, max_val:
        Inclusive number range.
    lookback_days:
        Only use draws from the last ``lookback_days`` days for pair
        co-occurrence.  ``None`` to use all history.
    """

    def __init__(
        self,
        df: pd.DataFrame,
        time_predict: int = 1,
        min_val: int = PredictModel.POWER_655_MIN_VAL,
        max_val: int = PredictModel.POWER_655_MAX_VAL,
        lookback_days: Optional[int] = 365,
        filter_consecutive: bool = True,
        filter_same_decade: bool = True,
    ):
        super().__init__(df, time_predict, min_val, max_val)
        self.lookback_days = lookback_days
        self.filter_consecutive = filter_consecutive
        self.filter_same_decade = filter_same_decade
        self._triples: List[Tuple[int, int, int]] = self._build_partial_steiner()
        self.df_sorted: pd.DataFrame = df.sort_values("date").reset_index(drop=True)
        self._pair_freq_cache: Dict[date, Dict[Tuple[int, int], int]] = {}
        self._top_pairs_cache: Dict[Tuple[date, int], List[Tuple[Tuple[int, int, int], Tuple[int, int, int]]]] = {}
        self._call_counter: int = 0

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

    # ------------------------------------------------------------------
    # Partial Steiner triple system construction
    # ------------------------------------------------------------------

    def _build_partial_steiner(self) -> List[Tuple[int, int, int]]:
        """Greedy pair-disjoint triple decomposition of [min_val, max_val]."""
        v = self.max_val - self.min_val + 1
        triples: List[Tuple[int, int, int]] = []
        covered: set = set()

        for a in range(v):
            for b in range(a + 1, v):
                pair = (a, b)
                if pair in covered:
                    continue
                # Find the smallest c > b that keeps (a,c), (b,c) uncovered
                for c in range(b + 1, v):
                    p1 = (a, c)
                    p2 = (b, c)
                    if p1 in covered or p2 in covered:
                        continue
                    triples.append((a + self.min_val, b + self.min_val, c + self.min_val))
                    covered.add(pair)
                    covered.add(p1)
                    covered.add(p2)
                    break

        return triples

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
            nums = sorted(int(n) for n in result)
            for a, b in combinations(nums, 2):
                key = (min(a, b), max(a, b))
                freq[key] = freq.get(key, 0) + 1

        self._pair_freq_cache[target_date] = freq
        return freq

    @staticmethod
    def _score_triple(triple: Tuple[int, int, int], freq: Dict[Tuple[int, int], int]) -> int:
        a, b, c = sorted(triple)
        return freq.get((a, b), 0) + freq.get((a, c), 0) + freq.get((b, c), 0)

    # ------------------------------------------------------------------
    # Top-K disjoint pairs of triples
    # ------------------------------------------------------------------

    def _top_disjoint_pairs(self, target_date: date, k: int) -> List[Tuple[Tuple[int, int, int], Tuple[int, int, int]]]:
        """Return up to k disjoint (T1, T2) pairs ordered by combined score desc.

        Results are cached per (date, k) so multiple HybridStrategy wrappers
        sharing one Steiner instance only pay the O(T²) cost once per date.
        """
        cache_key = (target_date, k)
        if cache_key in self._top_pairs_cache:
            return self._top_pairs_cache[cache_key]

        freq = self._pair_freq(target_date)
        triples = self._triples
        if self.filter_consecutive or self.filter_same_decade:
            triples = [t for t in triples if self.is_valid_triple(t, self.filter_consecutive, self.filter_same_decade)]

        if not triples:
            self._top_pairs_cache[cache_key] = []
            return []

        scored = [(self._score_triple(t, freq), idx, t) for idx, t in enumerate(triples)]
        # Sort by score desc; use index as tie-breaker for determinism
        scored.sort(key=lambda x: (-x[0], x[1]))

        # Greedy: pick the first triple, then the best disjoint partner for it
        result: List[Tuple[Tuple[int, int, int], Tuple[int, int, int]]] = []
        for i, (_, _, t1) in enumerate(scored):
            if len(result) >= k:
                break
            set1 = set(t1)
            best_partner: Optional[Tuple[int, int, int]] = None
            best_partner_score = -1
            for _, _, t2 in scored:
                if t2 is t1 or set(t2) & set1:
                    continue
                s = self._score_triple(t2, freq)
                if s > best_partner_score:
                    best_partner_score = s
                    best_partner = t2
            if best_partner is None:
                continue
            result.append((t1, best_partner))

        self._top_pairs_cache[cache_key] = result
        return result

    def get_top_tickets(self, target_date: date, k: int) -> List[List[int]]:
        """
        Return up to k candidate tickets ordered by combined Steiner pair-score desc.

        Each ticket is the union of 2 disjoint Steiner triples.  Used by
        :class:`~machine_learning.strategies.hybrid.HybridStrategy` to feed
        Steiner-proposed candidates to other strategies for voting.
        """
        pairs = self._top_disjoint_pairs(target_date, k=k)
        return [sorted(set(t1) | set(t2)) for t1, t2 in pairs]

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
        # Take the top 3 disjoint pair tickets (18 numbers), slice to k unique
        pairs = self._top_disjoint_pairs(target_date, k=max(3, (effective_k + 5) // 6))
        seen: set = set()
        result: List[int] = []
        for t1, t2 in pairs:
            for n in set(t1) | set(t2):
                if n not in seen:
                    seen.add(n)
                    result.append(n)
                    if len(result) >= effective_k:
                        return result
        # Pad with remaining numbers if still short
        for n in range(self.min_val, self.max_val + 1):
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
    def _build_steiner_on_pool(pool: List[int]) -> List[Tuple[int, int, int]]:
        """Greedy pair-disjoint triple decomposition of a custom pool.

        ``pool`` must be a list of distinct integers.  Returned triples
        are sorted ascending so the algorithm is deterministic.
        """
        sorted_pool = sorted(set(pool))
        n = len(sorted_pool)
        if n < 3:
            return []
        triples: List[Tuple[int, int, int]] = []
        covered: set = set()
        for a in range(n):
            for b in range(a + 1, n):
                pair = (a, b)
                if pair in covered:
                    continue
                for c in range(b + 1, n):
                    p1 = (a, c)
                    p2 = (b, c)
                    if p1 in covered or p2 in covered:
                        continue
                    triples.append((sorted_pool[a], sorted_pool[b], sorted_pool[c]))
                    covered.add(pair)
                    covered.add(p1)
                    covered.add(p2)
                    break
        return triples

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
        """Pick ``number_predict`` numbers from ``pool`` using Steiner triples.

        The structural unit adapts to ``number_predict`` (defaults to
        ``self.number_predict``) so the same method works for any
        Vietlott product:

        ===========  =========================  ==================================
        number_predict  Steiner structure         example
        ===========  =========================  ==================================
        3            1 triple                   [a, b, c]
        4            1 triple + 1 singleton     [a, b, c, d]
        5            1 triple + 1 disjoint pair [a, b, c, d, e]
        6            2 disjoint triples         [a, b, c, d, e, f]
        ===========  =========================  ==================================

        For 5/35 this method returns 5 numbers natively (1 Steiner triple
        + 1 pair-disjoint pair from another triple), instead of the
        previous behaviour of building 6 numbers and slicing off the
        last.

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

        triples = self._build_steiner_on_pool(sorted_pool)
        if not triples:
            return sorted(sorted_pool)[:number_predict]

        # Decompose number_predict into Steiner units.
        # Example: 5 -> [3, 2]; 6 -> [3, 3]; 4 -> [3, 1]; 3 -> [3]
        units = self._decompose_into_units(number_predict)

        # Sort triples by pair-score for greedy ticket assembly.
        scored_triples = [(self._score_triple(t, pool_freq), idx, t) for idx, t in enumerate(triples)]
        scored_triples.sort(key=lambda x: (-x[0], x[1]))

        tickets: List[Tuple[int, ...]] = []
        seen: set = set()
        for _, _, t1 in scored_triples:
            if len(tickets) >= coverage:
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
            tickets.append(ticket)

        if not tickets:
            return sorted(sorted_pool)[:number_predict]

        idx = self._call_counter
        self._call_counter += 1
        return list(tickets[idx % len(tickets)])

    # ------------------------------------------------------------------
    # Structural-unit helpers (used by predict_from_pool)
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
        triples: List[Tuple[int, int, int]],
        freq: Dict[Tuple[int, int], int],
        unit_size: int,
        pool: List[int],
    ) -> set:
        """Find the best (highest-scoring) Steiner unit of ``unit_size``
        that is pair-disjoint from ``used``.

        * ``unit_size == 3`` — best disjoint triple from the partial
          Steiner system.  Score = sum of the triple's 3 internal
          pair-frequencies (delegates to :meth:`_score_triple`).
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
            best: Optional[Tuple[int, int, int]] = None
            best_score = -1
            for t in triples:
                if set(t) & used:
                    continue
                s = self._score_triple(t, freq)
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

    def filter_pool(self, target_date, pool: List[int], k: int) -> List[int]:
        """Filter a candidate pool using Steiner's native ``predict_from_pool``.

        Returns exactly ``k`` numbers from ``pool`` structured as Steiner
        triples (or fallback if the pool or Steiner system is too small).
        """
        if k >= len(pool):
            return sorted(set(pool))
        picked = self.predict_from_pool(target_date, pool=list(pool), coverage=3, number_predict=k)
        return sorted(set(picked))

    def predict(self, date: date) -> List[int]:
        """Predict numbers as the i-th best pair of disjoint Steiner triples.

        Returns ``self.number_predict`` numbers (sliced from the 6-element
        union of 2 disjoint triples), so it works for any game — 5/35
        returns 5, 6/55 and 6/45 return 6.
        """
        pairs = self._top_disjoint_pairs(date, k=max(self.time_predict, 1))
        idx = self._call_counter
        self._call_counter += 1

        if not pairs:
            # Cold-start fallback: take the first 6 sorted numbers from the
            # union of triples.
            nums: List[int] = []
            for t in self._triples:
                for n in t:
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

        t1, t2 = pairs[idx % len(pairs)]
        return sorted(set(t1) | set(t2))[: self.number_predict]
