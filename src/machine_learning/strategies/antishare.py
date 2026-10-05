"""Anti-popularity (contrarian) ticket sampler.

Implements the pari-mutuel anti-popularity idea (Haigh 1997 / Lien & Yuan
2014): because many players over-bet "pretty" tickets (birthday numbers,
consecutive runs, balanced representative sets, arithmetic patterns), a
player who deliberately picks unpopular tickets shares the jackpot with
fewer others, raising expected payout while leaving win probability
unchanged.
"""

from __future__ import annotations

import random
from itertools import combinations

from machine_learning.strategies.base import PredictModel


class AntiShareStrategy(PredictModel):
    """Contrarian strategy that samples random tickets and returns the least-popular one.

    The popularity proxy penalises (adds weight to) known over-played
    ticket shapes — birthday-biased numbers <= 31, consecutive runs,
    evenly balanced decade distribution, equally spaced triples, and
    uniform parity — and the strategy deliberately returns the sampled
    ticket with the LOWEST such score while staying deterministic for a
    given (date, call order) so tests and backtests remain reproducible.
    """

    SAMPLE_SIZE = 200
    MAX_RESAMPLE_BATCHES = 25
    BIRTHDAY_CUTOFF = 31
    BIRTHDAY_WEIGHT = 1.6
    RUN_WEIGHT = 1.0
    SPREAD_UNIFORM_WEIGHT = 0.8
    SPREAD_SKEWED_WEIGHT = 0.2
    TRIPLE_WEIGHT = 2.0
    PARITY_WEIGHT = 1.0

    def __init__(
        self,
        df,
        time_predict: int = 1,
        min_val: int = PredictModel.POWER_655_MIN_VAL,
        max_val: int = PredictModel.POWER_655_MAX_VAL,
        lookback_days: int = 365,
    ):
        """Create the strategy; ``lookback_days`` is contract-only and unused by scoring."""
        super().__init__(df, time_predict=time_predict, min_val=min_val, max_val=max_val)
        self.lookback_days = int(lookback_days)
        self._call_counter: dict[str, int] = {}
        self._issued: dict[str, list[tuple[int, ...]]] = {}

    # ------------------------------------------------------------------
    # Popularity proxy
    # ------------------------------------------------------------------

    @property
    def _ticket_size(self) -> int:
        return int(self.number_predict)

    def popularity_score(self, ticket) -> float:
        """Score a sorted ticket by its popularity proxy (lower = less popular)."""
        nums = sorted(set(ticket))
        score = 0.0
        # Birthday bias: day-of-birth numbers (<=31) are over-played (~1.6x,
        # Dutch lotto day-of-birth effect).
        score += sum(self.BIRTHDAY_WEIGHT for n in nums if n <= self.BIRTHDAY_CUTOFF)
        # Consecutive runs: weight scales with run length.
        run = 1
        for a, b in zip(nums, nums[1:]):
            if b - a == 1:
                run += 1
            else:
                if run >= 2:
                    score += self.RUN_WEIGHT * run
                run = 1
        if run >= 2:
            score += self.RUN_WEIGHT * run
        # Balance: representative/evenly spread tickets across decades are
        # over-played; skewed distributions attract less play.
        buckets: dict[int, int] = {}
        for n in nums:
            key = n // 10
            buckets[key] = buckets.get(key, 0) + 1
        distinct = len(buckets)
        spread = distinct - 1
        if max(buckets.values()) > 2:
            score += self.SPREAD_SKEWED_WEIGHT * spread
        else:
            # Thoroughly uniform equation across >= 3 evenly fed buckets.
            if distinct >= 3 and max(buckets.values()) - min(buckets.values()) <= 1:
                score += self.SPREAD_UNIFORM_WEIGHT * spread
            else:
                score += 0.5 * self.SPREAD_UNIFORM_WEIGHT * spread
        # Equally spaced arithmetic triples (1,3,5 / 2,4,6 / 10,20,30 ...).
        for a, b, c in combinations(nums, 3):
            if b - a == c - b and b - a > 0:
                score += self.TRIPLE_WEIGHT
        # All-same parity: mild popularity penalty.
        if all(n % 2 == 0 for n in nums) or all(n % 2 == 1 for n in nums):
            score += self.PARITY_WEIGHT
        return score

    # ------------------------------------------------------------------
    # Prediction
    # ------------------------------------------------------------------

    def _batch_best(self, rng: random.Random, pool: list[int], prior: list[tuple[int, ...]], exclude_close: bool):
        """Sample one batch and return the lowest-popularity admissible ticket."""
        k = self._ticket_size
        best: tuple[int, ...] | None = None
        best_score: float | None = None
        prior_sets = [set(p) for p in prior]
        for _ in range(self.SAMPLE_SIZE):
            t = tuple(sorted(rng.sample(pool, k)))
            t_set = set(t)
            if t_set in prior_sets:
                continue
            if exclude_close and any(len(t_set & ps) == k - 1 for ps in prior_sets):
                continue
            score = self.popularity_score(t)
            if best_score is None or score < best_score:
                best, best_score = t, score
        return best, best_score

    def predict(self, date=None, candidate_pool=None):
        """Return one low-popularity ticket; successive calls differ via internal jitter state."""
        pool = (
            sorted(set(int(n) for n in candidate_pool))
            if candidate_pool is not None
            else list(range(self.min_val, self.max_val + 1))
        )
        k = self._ticket_size
        if len(pool) < k:
            raise ValueError(f"candidate pool too small: {len(pool)} < {k}")
        key = str(date)
        call_idx = self._call_counter.get(key, 0)
        self._call_counter[key] = call_idx + 1
        prior = self._issued.setdefault(key, [])
        # Deterministic per (date, call order) seed with internal jitter.
        rng = random.Random(f"antishare|{self.min_val}|{self.max_val}|{key}|{call_idx}")
        chosen: tuple[int, ...] | None = None
        for _batch in range(self.MAX_RESAMPLE_BATCHES):
            candidate, _score = self._batch_best(rng, pool, prior, exclude_close=True)
            if candidate is not None and set(candidate) not in [set(p) for p in prior]:
                chosen = candidate
                break
        if chosen is None:  # exhausted admissible space: allow distinct-set fallback
            candidate, _score = self._batch_best(rng, pool, prior, exclude_close=False)
            if candidate is not None and set(candidate) not in [set(p) for p in prior]:
                chosen = candidate
        if chosen is None:  # pool structurally exhausted: reuse min violation as-is
            candidate, _score = self._batch_best(rng, pool, prior, exclude_close=False)
            chosen = candidate if candidate is not None else tuple(sorted(rng.sample(pool, k)))
        prior.append(chosen)
        return sorted(chosen)

    def propose_top_numbers(self, target_date, k: int):
        """Propose the least-popular ``k``-subset of the full range (used by hybrid callees)."""
        pool = list(range(self.min_val, self.max_val + 1))
        rng = random.Random(f"antishare|top|{self.min_val}|{self.max_val}|{target_date}|{k}")
        best, best_score = None, None
        for _ in range(self.SAMPLE_SIZE):
            t = tuple(sorted(rng.sample(pool, k)))
            score = self.popularity_score(t)
            if best_score is None or score < best_score:
                best, best_score = t, score
        return sorted(best) if best is not None else []
