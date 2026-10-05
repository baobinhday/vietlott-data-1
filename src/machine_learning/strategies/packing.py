"""Min-max pairwise overlap packing of lottery tickets.

Builds (2-(v,6,1)) packing designs: N tickets of 6 numbers over 1..max_val
where every number appears on at least one ticket (full coverage), pairwise
ticket overlap is at most 1 (relaxed to 2 only on deadlock, recording the
relaxation), and number degrees are balanced within ±1.  Ticket numbers come
purely from the range — never from historical draw data.
"""

from __future__ import annotations

import math
import random
from collections import Counter

from loguru import logger

from machine_learning.strategies.base import PredictModel


def build_packing(numbers: list[int], ticket_size: int, num_tickets: int, rng: random.Random):
    """Greedy round-robin packing over ``numbers`` into ``num_tickets`` sets of 6.

    Returns ``(tickets, relaxation_used)`` where tickets are sorted lists and
    ``relaxation_used`` is None (overlap <= 1) or 2 when the ≤2 relaxation
    had to be engaged on deadlock.
    """
    tickets: list[list[int]] = [[] for _ in range(num_tickets)]
    pos: dict[int, int] = {x: 0 for x in numbers}
    total = num_tickets * ticket_size
    q, r = divmod(total, len(numbers))
    targets: dict[int, int] = {x: q + (1 if idx < r else 0) for idx, x in enumerate(sorted(numbers))}

    max_overlap = 1
    relaxation_used: int | None = None

    def overlap(a: list[int], b: list[int]) -> int:
        return len(set(a) & set(b))

    for slot in range(total):
        j = slot % num_tickets
        t_j = tickets[j]
        # Candidates that still need occurrences, lowest count first (degree balance).
        cands = [x for x in numbers if pos[x] < targets[x]]
        assert cands, "packing invariant violated: shortfall must exist while slots remain"

        def place(x: int, ovl: int) -> bool:
            # Placement invalid if x already lives on another ticket m and
            # adding it to t_j would push overlap(t_j, m) above ``ovl``.
            for m, t_m in enumerate(tickets):
                if m != j and x in t_m and overlap(t_j, t_m) + 1 > ovl:
                    return False
            t_j.append(x)
            pos[x] += 1
            return True

        # Tier 1: strictly-needed numbers (count below target), requiring overlap <= max_overlap.
        progress = False
        for x in sorted(cands, key=lambda v: (pos[v], v)):
            if x in t_j:
                continue
            if place(x, max_overlap):
                progress = True
                break
        if progress:
            continue
        # Tier 2: relax to overlap <= 2 and record (spec: record which relaxation was used).
        if relaxation_used is None:
            relaxation_used = 2
            logger.warning(f"packing deadlock for {len(numbers)} num / {num_tickets} tickets: relax overlap to <= 2")
            max_overlap = 2
        for x in sorted(cands, key=lambda v: (pos[v], v)):
            if x in t_j:
                continue
            if place(x, max_overlap):
                progress = True
                break
        if progress:
            continue
        # Tier 3: any candidate minimising the resulting max overlap (last-resort progress).
        best_x, best_ovl = None, None
        for x in sorted(cands, key=lambda v: (pos[v], v)):
            if x in t_j:
                continue
            ovl_needed = 1 + max((overlap(t_j, t_m) for m, t_m in enumerate(tickets) if m != j and x in t_m), default=0)
            if best_ovl is None or ovl_needed < best_ovl:
                best_x, best_ovl = x, ovl_needed
        assert best_x is not None
        t_j.append(best_x)
        pos[best_x] += 1

    final = [sorted(t) for t in tickets]
    assert all(len(t) == ticket_size for t in final), "packing: tickets must be full"
    return final, relaxation_used


class PackingScheduler(PredictModel):
    """Rotates a precomputed packing design: full coverage with pairwise overlap ≤ 1.

    Tickets are constructed by :func:`build_packing` from (min_val, max_val,
    ticket count) alone — historical DataFrames are ignored for number
    selection.  ``predict`` hands out the next ticket in rotation so
    ``time_predict`` calls per date walk the whole design; the packing is
    rebuilt only when the product range changes.
    """

    def __init__(
        self,
        df,
        time_predict: int = 1,
        min_val: int = PredictModel.POWER_655_MIN_VAL,
        max_val: int = PredictModel.POWER_655_MAX_VAL,
    ):
        """Create the scheduler; call :meth:`apply_product_config` to bind the product range."""
        super().__init__(df, time_predict=time_predict, min_val=min_val, max_val=max_val)
        self.range_key: tuple | None = None
        self.packing: list[list[int]] = []
        self.relaxation_used: int | None = None
        self._per_date_calls: dict[str, int] = {}
        self._pool_cache: dict[tuple, list[list[int]]] = {}

    def _effective_ticket_count(self, pool_size: int) -> int:
        """Minimum ticket count for full coverage, floored at ``time_predict``."""
        min_for_coverage = math.ceil(pool_size / self.number_predict)
        return max(1, max(self.time_predict, min_for_coverage))

    def _build(self):
        """Rebuild the full-range packing for the current (min_val, max_val, N)."""
        pool_size = self.max_val - self.min_val + 1
        n = max(self.time_predict, math.ceil(pool_size / self.number_predict))
        key = (self.min_val, self.max_val, self.number_predict, n)
        if self.range_key != key:
            rng = random.Random(f"packing|{self.min_val}|{self.max_val}|{self.number_predict}|{n}")
            nums = list(range(self.min_val, self.max_val + 1))
            self.packing, self.relaxation_used = build_packing(nums, self.number_predict, n, rng)
            self.range_key = key
        return self.packing

    def _build_pool(self, pool: list[int]) -> list[list[int]]:
        """Build (and cache) a packing constrained to a candidate pool."""
        key = (self.min_val, self.max_val, self.number_predict, tuple(pool))
        cached = self._pool_cache.get(key)
        if cached is None:
            n = self._effective_ticket_count(len(pool))
            rng = random.Random(f"packingpool|{self.min_val}|{self.max_val}|{self.number_predict}|{len(pool)}")
            tickets, _relax = build_packing(sorted(pool), self.number_predict, n, rng)
            self._pool_cache[key] = cached = tickets
        return cached

    def predict(self, date=None, candidate_pool=None):
        """Return the next ticket in the rotation for this date (deterministic per call order)."""
        if candidate_pool is not None:
            pool = sorted({int(n) for n in candidate_pool})
            if len(pool) < self.number_predict:
                raise ValueError(f"candidate pool too small: {len(pool)} < {self.number_predict}")
            packing = self._build_pool(pool)
        else:
            packing = self._build()
        key = str(date)
        idx = self._per_date_calls.get(key, 0)
        self._per_date_calls[key] = idx + 1
        return sorted(packing[idx % len(packing)])

    @classmethod
    def stats(cls, tickets) -> Counter:
        """Return per-number occurrence counts across the given tickets (test helper)."""
        counts: Counter = Counter()
        for t in tickets:
            counts.update(t)
        return counts
