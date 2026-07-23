"""
Inverse hybrid prediction strategy.

This is the structural mirror of :class:`machine_learning.strategies.hybrid.HybridStrategy`.

Direction comparison
--------------------
* ``HybridStrategy``     — Steiner proposes a top-K pool, a *voter* picks
                            ``number_predict`` numbers from that pool using
                            its own algorithm.
* ``InverseHybridStrategy`` — A *proposer* strategy (any ``PredictModel``
                              subclass) outputs a top-K candidate pool
                              (default ``K = 15``), and Steiner picks
                              ``number_predict`` numbers from that pool
                              using its pair-disjoint triple decomposition
                              with the requested coverage (default 3
                              disjoint triple-pairs).

Use case
--------
The original hybrid trusts Steiner to narrow the search space but
delegates final selection to a frequency / co-occurrence / absence signal.
The inverse hybrid flips this: trust the proposer's signal to narrow the
search space, but require the final 6-number ticket to satisfy the
*structural* constraint that it decomposes into two pair-disjoint Steiner
triples.  The resulting tickets always come from the proposer's pool, but
their internal pair structure is screened for high historical pair
co-occurrence.
"""

from typing import List

from machine_learning.strategies.base import PredictModel
from machine_learning.strategies.steiner import SteinerStrategy


class InverseHybridStrategy(PredictModel):
    """
    A two-stage strategy: a proposer picks a 15-number pool, Steiner picks 6.

    For each ``predict(date)`` call:

    1. The proposer's :meth:`PredictModel.propose_top_numbers` is invoked
       with ``k = top_k`` to obtain a sorted pool of candidate numbers
       (default size 15).
    2. Steiner decomposes that pool into pair-disjoint triples, scores
       each triple by historical pair co-occurrence within the pool, and
       greedily assembles ``coverage`` disjoint (T1, T2) tickets ordered
       by combined score.
    3. The i-th call (rotated by ``self._call_counter``) returns the
       i-th ticket's 6 numbers as the prediction.

    Parameters
    ----------
    proposer:
        The "voter" strategy acting as the proposer (any
        ``PredictModel`` subclass with a ``propose_top_numbers`` method).
        Its ``min_val``/``max_val``/``ticket_price``/``prices``/
        ``number_predict`` are inherited by the inverse hybrid so reports
        and scoring stay consistent.
    steiner:
        The Steiner picker (``SteinerStrategy`` instance).  Provides the
        pair co-occurrence cache and constrained-pool decomposition.
    top_k:
        Size of the proposer's candidate number pool (default 15).
    coverage:
        Number of disjoint (T1, T2) Steiner-ticket candidates the picker
        generates (default 3).  ``time_predict`` rotates through them.
    time_predict:
        Number of tickets generated per draw during backtest.
    """

    def __init__(
        self,
        proposer: PredictModel,
        steiner: SteinerStrategy,
        top_k: int = 15,
        coverage: int = 3,
        time_predict: int = 1,
    ):
        super().__init__(steiner.df, time_predict, proposer.min_val, proposer.max_val)
        self.proposer = proposer
        self.steiner = steiner
        self.top_k = top_k
        self.coverage = coverage
        # Mirror proposer identity for downstream consumers
        self.ticket_price = proposer.ticket_price
        self.prices = dict(proposer.prices)
        self.number_predict = proposer.number_predict

    def predict(self, target_date, candidate_pool=None) -> List[int]:
        """Pick numbers via Steiner from the proposer's pool.

        Parameters
        ----------
        target_date:
            Date for which to generate the prediction.
        candidate_pool:
            Ignored by the inverse hybrid — the candidate pool is always
            produced by ``self.proposer``.  Present only to satisfy the
            ``PredictModel`` interface.
        """
        del candidate_pool  # unused; the pool is the proposer's output
        try:
            pool = self.proposer.propose_top_numbers(target_date, self.top_k)
        except AttributeError:
            # Fall back to the base-class default if the proposer lacks
            # ``propose_top_numbers`` for any reason.
            pool = PredictModel.propose_top_numbers(self.proposer, target_date, self.top_k)

        if not pool:
            return self.steiner.predict(target_date)

        return self.steiner.predict_from_pool(
            target_date, pool, coverage=self.coverage, number_predict=self.number_predict
        )
