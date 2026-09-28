"""
Tests for Power535PredictionSummaryGenerator (render_prediction_535.py).
"""

import random
from datetime import date, timedelta

import pandas as pd
import polars as pl

from machine_learning.render_prediction_535 import Power535PredictionSummaryGenerator


def _make_535_df(n: int = 20, seed: int = 42) -> pd.DataFrame:
    """Generate a synthetic pandas DataFrame matching Power 5/35 schema.

    Each row has 5 main numbers + 1 special (số đặc biệt in 1..12), matching
    the real Power 5/35 result format consumed by ``apply_product_config``.
    """
    rng = random.Random(seed)
    start = date(2023, 1, 1)
    rows = []
    for i in range(n):
        draw_date = start + timedelta(days=i * 2)
        mains = sorted(rng.sample(range(1, 36), 5))
        special = rng.randint(1, 12)
        rows.append({"date": draw_date, "result": mains + [special], "id": str(i + 1)})
    return pd.DataFrame(rows)


class TestPower535PredictionSummaryGenerator:
    def test_init(self):
        generator = Power535PredictionSummaryGenerator()
        assert generator.min_val == 1
        assert generator.max_val == 35
        assert generator.number_predict == 5

    def test_build_and_run_strategies(self):
        df_pd = _make_535_df(n=10)
        generator = Power535PredictionSummaryGenerator()

        strategies = generator._build_and_run_strategies(df_pd)
        assert len(strategies) > 0

        for name, tpd, model in strategies:
            assert tpd == generator.TPD
            assert model.min_val == 1
            assert model.max_val == 35
            assert model.number_predict == 5
            assert model.df_backtest is not None
            assert model.df_backtest_evaluate is not None

    def test_hot_specials_top_4(self):
        """5/35 should use only the top-4 hot specials, not wheel through 1..12.

        With TPD=2 mains × 4 hot specials = 8 tickets per draw (down from 24).
        """
        # 500 draws of synthetic data (≈ 2.7 years at 1 draw / 2 days) so the
        # lookback window is fully populated for the vast majority of rows.
        df_pd = _make_535_df(n=500)
        generator = Power535PredictionSummaryGenerator()
        strategies = generator._build_and_run_strategies(df_pd)

        assert generator.SPECIALS_TOP_N == 4

        for name, tpd, model in strategies:
            assert model.special_pick_required is True
            assert model.df_backtest is not None
            assert model.df_backtest_evaluate is not None

            # Once the lookback is full, predict_special returns at most 4
            # specials and they're all in 1..12.
            specials = model.predict_special(date(2024, 6, 1))
            assert isinstance(specials, list)
            assert len(specials) <= 4
            assert all(1 <= s <= 12 for s in specials)

            # Almost every draw should give exactly 2 × 4 = 8 rows.  Only the
            # very first draws (lookback still filling) deviate, so the total
            # is at most 12 × tpd = 24 above the perfect-draw total.
            draws = len(model.df_backtest)
            rows = len(model.df_backtest_evaluate)
            expected_full = draws * tpd * 4
            # First draw uses the full [1..12] fallback → +tpd×8 extra rows.
            # Allow a small slack for that.
            assert rows <= expected_full + tpd * 8, (
                f"{name}: too many rows ({rows}), expected ≤ {expected_full + tpd * 8}"
            )
            # And we should have a clear reduction from the old 24-per-draw
            # baseline.
            old_baseline = draws * tpd * 12
            assert rows < old_baseline, f"{name}: should be < {old_baseline} rows (old 24/draw baseline), got {rows}"

    def test_hot_specials_picks_most_frequent(self):
        """The picked specials should be the most frequent in the lookback.

        Builds a dataset with skewed frequency distribution, then asserts the
        hot picker returns the high-frequency specials (7, 5, 11) and excludes
        the low-frequency ones (1, 2) once the lookback has data.
        """
        # 40 draws with controlled frequency:
        #   7 → 15 times (hottest), 5 → 12 times, 11 → 8 times,
        #   4 → 3 times, 1 → 1 time, 2 → 1 time
        special_pool = [7] * 15 + [5] * 12 + [11] * 8 + [4] * 3 + [1] * 1 + [2] * 1
        assert len(special_pool) == 40

        df_rows = []
        rng = random.Random(7)
        start = date(2024, 1, 1)
        for i, special in enumerate(special_pool):
            draw_date = start + timedelta(days=i * 2)
            mains = sorted(rng.sample(range(1, 36), 5))
            df_rows.append({"date": draw_date, "result": mains + [special], "id": str(i)})

        df_pd = pd.DataFrame(df_rows)
        generator = Power535PredictionSummaryGenerator()

        from machine_learning.strategies import HotNumbersStrategy

        strat = HotNumbersStrategy(df_pd, time_predict=1, min_val=1, max_val=35)
        strat.apply_product_config(generator.config)
        generator._apply_hot_specials(strat, top_n=4, lookback_days=365)
        picked = strat.predict_special(date(2025, 1, 1))
        assert 7 in picked, f"special 7 (hottest, 15x) should be picked, got {picked}"
        assert 5 in picked, f"special 5 (2nd, 12x) should be picked, got {picked}"
        assert 11 in picked, f"special 11 (3rd, 8x) should be picked, got {picked}"
        assert 1 not in picked, f"special 1 (rare, 1x) should be excluded, got {picked}"
        assert 2 not in picked, f"special 2 (rare, 1x) should be excluded, got {picked}"
        assert len(picked) == 4

    def test_cold_specials_picks_least_frequent(self):
        """The picked cold specials should be the least frequent in the lookback."""
        special_pool = [7] * 15 + [5] * 12 + [11] * 8 + [4] * 3 + [1] * 1 + [2] * 1
        df_rows = []
        rng = random.Random(7)
        start = date(2024, 1, 1)
        for i, special in enumerate(special_pool):
            draw_date = start + timedelta(days=i * 2)
            mains = sorted(rng.sample(range(1, 36), 5))
            df_rows.append({"date": draw_date, "result": mains + [special], "id": str(i)})

        df_pd = pd.DataFrame(df_rows)
        generator = Power535PredictionSummaryGenerator()

        from machine_learning.strategies import ColdNumbersStrategy

        strat = ColdNumbersStrategy(df_pd, time_predict=1, min_val=1, max_val=35)
        strat.apply_product_config(generator.config)
        generator._apply_frequency_specials(strat, top_n=4, lookback_draws=365, mode="cold")
        picked = strat.predict_special(date(2025, 1, 1))
        # 1 and 2 appear only 1x, 3, 6, 8, 9, 10, 12 appear 0x. So cold should pick 0x or 1x numbers.
        assert 7 not in picked, f"special 7 (hottest, 15x) should NOT be picked, got {picked}"
        assert 5 not in picked, f"special 5 (2nd hottest, 12x) should NOT be picked, got {picked}"
        assert len(picked) == 4

    def test_roi_comparison_table(self):
        df_pd = _make_535_df(n=5)
        generator = Power535PredictionSummaryGenerator()
        strategies = generator._build_and_run_strategies(df_pd)

        table_md = generator._roi_comparison_table(strategies)
        assert f"Strategy Performance Comparison ({generator.PRODUCT_DISPLAY})" in table_md
        assert "| Rank | Strategy |" in table_md

    def test_yearly_breakdown_table(self):
        """Yearly breakdown should aggregate per-year and include a Total row."""
        df_pd = _make_535_df(n=20)
        generator = Power535PredictionSummaryGenerator()
        strategies = generator._build_and_run_strategies(df_pd)

        name, tpd, model = strategies[0]
        table_md = generator._yearly_breakdown_table(model)

        # Header + Total row
        assert "| Year | Draws | Predictions |" in table_md
        assert "| **Total** |" in table_md
        # Synthetic data starts 2023-01-01 → at least one 2023 row
        assert "| 2023 |" in table_md
        # Net profit / ROI cells present
        assert "Net Profit (VND)" in table_md
        assert "ROI |" in table_md

    def test_yearly_breakdown_table_empty(self):
        """No backtest data → friendly placeholder instead of a crash."""
        from types import SimpleNamespace

        from machine_learning.strategies.base import PredictModel

        generator = Power535PredictionSummaryGenerator()
        model = SimpleNamespace(
            df_backtest=None,
            df_backtest_evaluate=None,
            prize_fn=None,
            ticket_price=PredictModel.ticket_price,
            prices=PredictModel.prices,
        )
        out = generator._yearly_breakdown_table(model)
        assert "No evaluation data available" in out

    def test_generate_prediction_summary_content(self, tmp_path):
        df_pd = _make_535_df(n=5)
        generator = Power535PredictionSummaryGenerator()

        # Mock _load_lottery_data to return mock data as Polars DF
        df_pl = pl.from_pandas(df_pd)
        generator._load_lottery_data = lambda: df_pl

        summary = generator.generate_prediction_summary()
        assert f"# 🔮 Vietlott {generator.PRODUCT_DISPLAY} Prediction Summary" in summary
        assert "Prediction Models" in summary

    def test_save_prediction_summary(self, tmp_path):
        df_pd = _make_535_df(n=5)
        generator = Power535PredictionSummaryGenerator()
        generator._load_lottery_data = lambda: pl.from_pandas(df_pd)

        out_file = tmp_path / "readme_535_test.md"
        generator.save_prediction_summary(output_path=out_file)

        assert out_file.exists()
        content = out_file.read_text(encoding="utf-8")
        assert generator.PRODUCT_DISPLAY in content
