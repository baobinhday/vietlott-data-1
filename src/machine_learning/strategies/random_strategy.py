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
