"""
Hybrid prediction strategy.

Combines a Steiner ``proposer`` (which generates a pool of top-K candidate
numbers via Steiner triples) with a ``voter`` strategy that runs its own
algorithm constrained to that pool.  Each voter produces a different output
(matching its standalone behaviour) because each uses its own generation
logic on the same Steiner pool.
"""

from datetime import date
from typing import List

from machine_learning.strategies.base import PredictModel
from machine_learning.strategies.steiner import SteinerStrategy


class HybridStrategy(PredictModel):
    """
    A two-stage strategy: Steiner proposes a number pool, a voter picks 6.

    For each ``predict(date)`` call:

    1. The Steiner proposer returns up to ``top_k`` distinct numbers (the
       "pool") by extracting unique numbers from its top-ranked disjoint
       Steiner triples.
    2. The voter strategy's own ``predict`` is called with ``candidate_pool``
       set to the Steiner pool, so it generates 6 numbers using its native
       algorithm constrained to that pool.
    3. The voter's 6 numbers are returned.

    Parameters
    ----------
    base:
        The voter strategy (any ``PredictModel`` subclass).  Its
        ``min_val``/``max_val``/``ticket_price``/``prices``/``number_predict``
        are inherited by the hybrid so reports and scoring stay consistent.
    steiner:
        The Steiner proposer (``SteinerStrategy`` instance).
    top_k:
        Size of the Steiner candidate number pool.
    time_predict:
        Number of tickets per draw during backtest.
    """

    def __init__(
        self,
        base: PredictModel,
        steiner: SteinerStrategy,
        top_k: int = 10,
        time_predict: int = 1,
    ):
        super().__init__(steiner.df, time_predict, base.min_val, base.max_val)
        self.base = base
        self.steiner = steiner
        self.top_k = top_k
        # Mirror voter identity for downstream consumers
        self.ticket_price = base.ticket_price
        self.prices = dict(base.prices)
        self.number_predict = base.number_predict

    def predict(self, target_date: date, candidate_pool=None) -> List[int]:
        """Pick numbers using the voter's own algorithm on a Steiner pool.

        The hybrid uses Steiner to propose a pool of top-K candidate numbers,
        then delegates to the voter strategy's own ``predict`` with
        ``candidate_pool`` set to that pool. The voter runs its original
        algorithm constrained to the pool, so each hybrid produces a
        different output (matching standalone behavior).

        The result is sliced to ``self.number_predict`` to ensure the hybrid
        always returns the configured count, even when the voter's default
        ``number_predict`` differs (e.g. Power 5/35 with voter default 6).
        """
        pool = self.steiner.get_top_numbers(target_date, self.top_k)
        if not pool:
            result = self.steiner.predict(target_date)
        else:
            result = self.base.predict(target_date, candidate_pool=pool)
        return sorted(result)[: self.number_predict]
