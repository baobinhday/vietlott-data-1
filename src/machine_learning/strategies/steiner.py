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
    ):
        super().__init__(df, time_predict, min_val, max_val)
        self.lookback_days = lookback_days
        self._triples: List[Tuple[int, int, int]] = self._build_partial_steiner()
        self.df_sorted: pd.DataFrame = df.sort_values("date").reset_index(drop=True)
        self._pair_freq_cache: Dict[date, Dict[Tuple[int, int], int]] = {}
        self._top_pairs_cache: Dict[Tuple[date, int], List[Tuple[Tuple[int, int, int], Tuple[int, int, int]]]] = {}
        self._call_counter: int = 0

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
    # PredictModel interface
    # ------------------------------------------------------------------

    def predict(self, date: date) -> List[int]:
        """Predict 6 numbers as the i-th best pair of disjoint Steiner triples."""
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
        return sorted(set(t1) | set(t2))
