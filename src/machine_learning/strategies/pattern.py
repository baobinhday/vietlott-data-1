import random
from collections import Counter
from datetime import date, timedelta
from typing import Any, Dict, List

import pandas as pd

from machine_learning.strategies.base import PredictModel


class PatternStrategy(PredictModel):
    """
    Strategy that analyzes patterns in number distribution and spacing.

    Performance notes
    -----------------
    On the first ``predict()`` call for each unique draw date the strategy
    performs a **single pass** through the relevant historical window to
    compute both spacing patterns and range distribution simultaneously.
    Results are stored in ``_analysis_cache`` so every subsequent call for
    the same date (due to ``time_predict > 1``) returns in O(1).

    Previous implementation issues fixed here:
    * Three separate ``iterrows()`` passes merged into one ``.tolist()`` pass.
    * Range bucket computed with integer division instead of a nested loop.
    * ``odd_even_analysis`` was computed but never used — removed entirely.
    * Per-date caching eliminates ``time_predict - 1`` redundant computations.
    """

    def __init__(
        self,
        df: pd.DataFrame,
        time_predict: int = 1,
        min_val: int = PredictModel.POWER_655_MIN_VAL,
        max_val: int = PredictModel.POWER_655_MAX_VAL,
        lookback_days: int = 180,
        pattern_weight: float = 0.6,
    ):
        """
        Parameters
        ----------
        lookback_days:
            Rolling window (days) used to compute spacing and range statistics.
        pattern_weight:
            Fraction of the ticket filled with pattern-derived numbers.
            The remainder is filled uniformly at random.
        """
        super().__init__(df, time_predict, min_val, max_val)
        self.lookback_days = lookback_days
        self.pattern_weight = pattern_weight
        # Pre-compute range boundaries once (reused for every prediction).
        self._range_size = (max_val - min_val + 1) // 5
        self._ranges = [
            (
                min_val + i * self._range_size,
                min_val + (i + 1) * self._range_size - 1 if i < 4 else max_val,
            )
            for i in range(5)
        ]
        self._analysis_cache: Dict[date, Dict[str, Any]] = {}
        self._prepare_historical_data()

    def _prepare_historical_data(self) -> None:
        self.df_sorted = self.df.sort_values("date")

    def _analyze_patterns(self, target_date: date) -> Dict[str, Any]:
        """
        Single-pass analysis of the lookback window.

        Computes spacing patterns and range distribution in one iteration,
        replacing the three separate ``iterrows()`` methods of the old design.
        """
        start_date = target_date - timedelta(days=self.lookback_days)
        mask = (self.df_sorted["date"] >= start_date) & (self.df_sorted["date"] < target_date)
        results_list: List[List[int]] = [self._main_numbers(r) for r in self.df_sorted.loc[mask, "result"].tolist()]

        if not results_list:
            # Fallback defaults when no history is available.
            return {
                "common_spacings": [(i, 1) for i in range(1, 11)],
                "range_counts": {i: 1 for i in range(5)},
            }

        all_spacings: List[int] = []
        range_counts = [0] * 5

        for nums in results_list:
            sorted_nums = sorted(nums)
            # Spacing gaps between consecutive sorted numbers.
            for i in range(1, len(sorted_nums)):
                all_spacings.append(sorted_nums[i] - sorted_nums[i - 1])
            # Range bucket via integer division — O(1) per number.
            for num in sorted_nums:
                bucket = min((num - self.min_val) // self._range_size, 4)
                range_counts[bucket] += 1

        return {
            "common_spacings": Counter(all_spacings).most_common(10),
            "range_counts": {i: range_counts[i] for i in range(5)},
        }

    def _generate_pattern_based_numbers(
        self, analysis: Dict[str, Any], available: List[int] | None = None
    ) -> List[int]:
        """Generate numbers from pre-computed pattern analysis.

        When *available* is provided the original range-based / spacing logic
        is skipped and the method falls back to ``random.sample(available, self.number_predict)``.
        """
        if available is not None:
            return sorted(random.sample(available, min(self.number_predict, len(available))))

        range_counts = analysis["range_counts"]
        total_counts = sum(range_counts.values())
        range_probs = [range_counts[i] / total_counts if total_counts > 0 else 0.2 for i in range(5)]

        selected_range = random.choices(range(5), weights=range_probs)[0]
        range_start, range_end = self._ranges[selected_range]
        predicted = [random.randint(range_start, range_end)]

        common_spacings = [s[0] for s in analysis["common_spacings"][:5]] or [1, 2, 3, 4, 5]

        while len(predicted) < self.number_predict:
            last_num = predicted[-1]
            spacing = random.choice(common_spacings)

            candidates = []
            if last_num + spacing <= self.max_val:
                candidates.append(last_num + spacing)
            if last_num - spacing >= self.min_val:
                candidates.append(last_num - spacing)

            valid_candidates = [c for c in candidates if c not in predicted]
            if valid_candidates:
                predicted.append(random.choice(valid_candidates))
            else:
                avail = [n for n in range(self.min_val, self.max_val + 1) if n not in predicted]
                if avail:
                    predicted.append(random.choice(avail))
                else:
                    break

        return sorted(predicted)

    def predict(self, target_date: date, candidate_pool: List[int] | None = None) -> List[int]:
        """
        Predict numbers based on pattern analysis.

        Analysis for ``target_date`` is computed at most once and cached;
        repeated calls with the same date (``time_predict > 1``) skip
        re-computation entirely.

        When *candidate_pool* is provided the pattern analysis is bypassed
        and numbers are sampled uniformly from the pool.
        """
        available = list(candidate_pool) if candidate_pool is not None else None

        if available is not None:
            return sorted(random.sample(available, min(self.number_predict, len(available))))

        if target_date not in self._analysis_cache:
            self._analysis_cache[target_date] = self._analyze_patterns(target_date)
        analysis = self._analysis_cache[target_date]

        pattern_count = int(self.number_predict * self.pattern_weight)
        random_count = self.number_predict - pattern_count

        predicted: List[int] = []

        if pattern_count > 0:
            pattern_numbers = self._generate_pattern_based_numbers(analysis)
            predicted.extend(pattern_numbers[:pattern_count])

        if random_count > 0:
            avail = [n for n in range(self.min_val, self.max_val + 1) if n not in predicted]
            if len(avail) >= random_count:
                predicted.extend(random.sample(avail, random_count))
            else:
                predicted.extend(avail)

        return sorted(predicted[: self.number_predict])

    def propose_top_numbers(self, target_date, k: int):
        """Propose the ``k`` numbers weighted by range-bucket popularity.

        Each range bucket (5 equal sub-ranges of ``[min_val, max_val]``)
        contributes a share of the proposal proportional to its observed
        draw frequency.  Within a bucket, numbers are selected
        uniformly at random using a deterministic per-date seed.
        """
        import random

        if target_date not in self._analysis_cache:
            self._analysis_cache[target_date] = self._analyze_patterns(target_date)
        analysis = self._analysis_cache[target_date]

        range_counts = analysis["range_counts"]
        total = sum(range_counts.values())
        if total == 0:
            return list(range(self.min_val, min(self.min_val + k, self.max_val + 1)))

        # Number of picks per bucket proportional to its count.
        per_bucket: list = [max(1, round(k * range_counts[i] / total)) for i in range(5)]
        # Adjust to total k (account for rounding drift).
        drift = k - sum(per_bucket)
        for i in range(abs(drift)):
            per_bucket[i % 5] += 1 if drift > 0 else -1

        rng = random.Random(f"pattern-{target_date}-{k}")
        chosen: list = []
        for i, (lo, hi) in enumerate(self._ranges):
            bucket_pool = list(range(lo, hi + 1))
            if not bucket_pool:
                continue
            take = min(per_bucket[i], len(bucket_pool))
            chosen.extend(rng.sample(bucket_pool, take))
        # Pad/trim to exactly k.
        if len(chosen) < k:
            for n in range(self.min_val, self.max_val + 1):
                if n not in chosen:
                    chosen.append(n)
                if len(chosen) == k:
                    break
        return sorted(chosen[:k])
