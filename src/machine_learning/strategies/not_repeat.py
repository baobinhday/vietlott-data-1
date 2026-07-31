import random
from datetime import date, timedelta
from typing import List

import pandas as pd

from machine_learning.strategies.base import PredictModel


class NotRepeatStrategy(PredictModel):
    """
    Strategy that avoids recently drawn numbers based on the assumption
    that numbers are less likely to repeat in consecutive draws.
    """

    def __init__(
        self,
        df: pd.DataFrame,
        time_predict: int = 1,
        min_val: int = PredictModel.POWER_655_MIN_VAL,
        max_val: int = PredictModel.POWER_655_MAX_VAL,
        lookback_days: int = 30,
        avoid_weight: float = 0.7,
    ):
        """
        Initialize NotRepeatStrategy.

        Args:
            df: Historical lottery data
            time_predict: Number of predictions per date
            min_val: Minimum number value
            max_val: Maximum number value
            lookback_days: Number of days to look back for recent numbers
            avoid_weight: Probability of avoiding recently drawn numbers (0-1)
        """
        super().__init__(df, time_predict, min_val, max_val)
        self.lookback_days = lookback_days
        self.avoid_weight = avoid_weight
        self._recent_cache: dict = {}
        self._prepare_historical_data()

    def _prepare_historical_data(self):
        """Prepare historical data for quick lookups."""
        self.df_sorted = self.df.sort_values("date").reset_index(drop=True)
        # Build date→results mapping without iterrows.
        self.date_to_results = {
            d: self._main_numbers(r) for d, r in zip(self.df_sorted["date"], self.df_sorted["result"])
        }

    def _get_recent_numbers(self, target_date: date) -> set:
        """
        Get numbers that appeared in recent draws before the target date.

        Results are cached per target_date.
        """
        if target_date in self._recent_cache:
            return self._recent_cache[target_date]

        recent_numbers = set()
        start_date = target_date - timedelta(days=self.lookback_days)

        for draw_date, results in self.date_to_results.items():
            if start_date <= draw_date < target_date:
                recent_numbers.update(results)

        self._recent_cache[target_date] = recent_numbers
        return recent_numbers

    def predict(self, target_date: date, candidate_pool: List[int] | None = None) -> List[int]:
        """
        Predict numbers by avoiding recently drawn ones.

        Args:
            target_date: Date for prediction
            candidate_pool: Optional constrained set of numbers to pick from.

        Returns:
            List of predicted numbers
        """
        recent_numbers = self._get_recent_numbers(target_date)
        all_numbers = (
            list(candidate_pool) if candidate_pool is not None else list(range(self.min_val, self.max_val + 1))
        )

        # Separate numbers into recent and non-recent
        non_recent = [n for n in all_numbers if n not in recent_numbers]
        recent = list(recent_numbers)

        predicted = []

        # First, try to select from non-recent numbers
        if len(non_recent) >= self.number_predict:
            predicted = random.sample(non_recent, self.number_predict)
        else:
            # If not enough non-recent numbers, use all non-recent + some recent
            predicted.extend(non_recent)
            remaining_needed = self.number_predict - len(non_recent)

            # Apply avoid_weight probability
            for _ in range(remaining_needed):
                if random.random() > self.avoid_weight and recent:
                    # Choose from recent numbers
                    chosen = random.choice(recent)
                    if chosen not in predicted:
                        predicted.append(chosen)
                        recent.remove(chosen)
                else:
                    # Choose from any remaining numbers
                    available = [n for n in all_numbers if n not in predicted]
                    if available:
                        predicted.append(random.choice(available))

        # Fill remaining slots if needed
        while len(predicted) < self.number_predict:
            available = [n for n in all_numbers if n not in predicted]
            if available:
                predicted.append(random.choice(available))
            else:
                break

        return sorted(predicted)

    def propose_top_numbers(self, target_date, k: int):
        """Propose the ``k`` numbers that have NOT appeared in recent draws.

        Returns numbers ordered by absence-recentness (those absent the
        longest are listed first; ties broken by numeric order).  Falls
        back to the full numeric range when not enough non-recent numbers
        exist.
        """
        recent = self._get_recent_numbers(target_date)
        non_recent = [n for n in range(self.min_val, self.max_val + 1) if n not in recent]
        if len(non_recent) >= k:
            return sorted(non_recent)[:k]
        # Not enough non-recent: pad with the least-recently-seen numbers.
        recent_sorted = sorted(recent)
        return (non_recent + recent_sorted)[:k]
