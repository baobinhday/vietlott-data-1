"""
Tests for Power535PredictionSummaryGenerator (render_prediction_535.py).
"""

import random
from datetime import date, timedelta

import pandas as pd
import polars as pl

from machine_learning.render_prediction_535 import Power535PredictionSummaryGenerator


def _make_535_df(n: int = 20, seed: int = 42) -> pd.DataFrame:
    """Generate a synthetic pandas DataFrame matching Power 5/35 schema."""
    rng = random.Random(seed)
    start = date(2023, 1, 1)
    rows = []
    for i in range(n):
        draw_date = start + timedelta(days=i * 2)
        result = sorted(rng.sample(range(1, 36), 5))
        rows.append({"date": draw_date, "result": result, "id": str(i + 1)})
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
            assert tpd == 2
            assert model.min_val == 1
            assert model.max_val == 35
            assert model.number_predict == 5
            assert model.df_backtest is not None
            assert model.df_backtest_evaluate is not None

    def test_roi_comparison_table(self):
        df_pd = _make_535_df(n=5)
        generator = Power535PredictionSummaryGenerator()
        strategies = generator._build_and_run_strategies(df_pd)

        table_md = generator._roi_comparison_table(strategies)
        assert "Strategy Performance Comparison (Power 5/35)" in table_md
        assert "| Rank | Strategy |" in table_md

    def test_generate_prediction_summary_content(self, tmp_path):
        df_pd = _make_535_df(n=5)
        generator = Power535PredictionSummaryGenerator()

        # Mock _load_lottery_data to return mock data as Polars DF
        df_pl = pl.from_pandas(df_pd)
        generator._load_lottery_data = lambda: df_pl

        summary = generator.generate_prediction_summary()
        assert "# 🔮 Vietlott Power 5/35 Prediction Summary" in summary
        assert "Prediction Models" in summary

    def test_save_prediction_summary(self, tmp_path):
        df_pd = _make_535_df(n=5)
        generator = Power535PredictionSummaryGenerator()
        generator._load_lottery_data = lambda: pl.from_pandas(df_pd)

        out_file = tmp_path / "readme_535_test.md"
        generator.save_prediction_summary(output_path=out_file)

        assert out_file.exists()
        content = out_file.read_text(encoding="utf-8")
        assert "Power 5/35 Prediction Summary" in content
