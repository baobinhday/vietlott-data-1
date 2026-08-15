from typing import List
import pandas as pd
from machine_learning.strategies.base import PredictModel
from machine_learning.strategies.inverse_hybrid import InverseHybridStrategy
from machine_learning.strategies.frequency import ColdNumbersStrategy
from machine_learning.strategies.pair_frequency import PairFrequencyStrategy
from machine_learning.strategies.pattern import PatternStrategy
from machine_learning.strategies.steiner import SteinerStrategy


class InverseHybridTrioStrategy(PredictModel):
    """
    An ensemble strategy that rotates through 3 top-performing Inverse Hybrid tickets:
    1. Inverse Hybrid: Cold Numbers -> Steiner
    2. Inverse Hybrid: Pair Frequency -> Steiner
    3. Inverse Hybrid: Pattern -> Steiner

    Designed to be used with time_predict=6 to buy exactly 6 main tickets (two of each).
    """

    def __init__(self, df: pd.DataFrame, steiner: SteinerStrategy, top_k: int = 15, time_predict: int = 6):
        # We inherit from PredictModel using steiner's parameters
        super().__init__(steiner.df, time_predict, steiner.min_val, steiner.max_val)

        self.steiner = steiner
        self.top_k = top_k
        self._call_counter = 0

        # Instantiate the three sub-strategies with time_predict=2 (since each generates 2 tickets)
        self.strat_cold = InverseHybridStrategy(
            proposer=ColdNumbersStrategy(
                df, time_predict=2, min_val=self.min_val, max_val=self.max_val, lookback_days=365, selection_weight=0.7
            ),
            steiner=steiner,
            top_k=top_k,
            coverage=2,
            time_predict=2,
        )

        self.strat_pair = InverseHybridStrategy(
            proposer=PairFrequencyStrategy(
                df, time_predict=2, min_val=self.min_val, max_val=self.max_val, lookback_days=365
            ),
            steiner=steiner,
            top_k=top_k,
            coverage=2,
            time_predict=2,
        )

        self.strat_pattern = InverseHybridStrategy(
            proposer=PatternStrategy(
                df, time_predict=2, min_val=self.min_val, max_val=self.max_val, lookback_days=180, pattern_weight=0.6
            ),
            steiner=steiner,
            top_k=top_k,
            coverage=2,
            time_predict=2,
        )

        self.sub_strategies = [self.strat_cold, self.strat_pair, self.strat_pattern]

    def apply_product_config(self, config):
        super().apply_product_config(config)
        for strat in self.sub_strategies:
            strat.apply_product_config(config)
        return self

    def predict(self, target_date, candidate_pool=None) -> List[int]:
        # Rotate through the 3 sub-strategies using the main strategy's call counter
        idx = self._call_counter
        self._call_counter += 1

        # Calculate which ticket of the sub-strategy we are requesting
        ticket_idx = idx // len(self.sub_strategies)

        # Set the shared steiner call counter to ticket_idx so the sub-strategy returns that specific ticket
        self.steiner._call_counter = ticket_idx

        chosen_strat = self.sub_strategies[idx % len(self.sub_strategies)]
        return chosen_strat.predict(target_date, candidate_pool)
