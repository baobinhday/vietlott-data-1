from machine_learning.strategies.base import PredictModel


class RandomModel(PredictModel):
    def predict(self, target_date=None, candidate_pool=None):
        import random

        if candidate_pool is not None:
            nums = list(candidate_pool)
        else:
            nums = list(range(self.min_val, self.max_val + 1))
        random.shuffle(nums)

        return sorted(nums[: self.number_predict])

    def propose_top_numbers(self, target_date, k: int):
        """Propose ``k`` deterministic numbers from the range.

        Uses a hash of ``(min_val, max_val, target_date, k)`` so the same
        date always yields the same proposal (useful for backtest
        reproducibility when used as a proposer).
        """
        import random

        seed_key = f"{self.min_val}-{self.max_val}-{target_date}-{k}"
        rng = random.Random(seed_key)
        return sorted(rng.sample(range(self.min_val, self.max_val + 1), k))
