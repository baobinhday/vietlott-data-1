#!/usr/bin/env python
"""
Repeated backtest evaluator for Vietlott Power 5/35 prediction strategies.

Runs the prediction generator N times (default N=20) and computes average financial metrics:
- Average Total Cost (VND)
- Average Total Gain (VND)
- Average Net Profit (VND)
- Average ROI (%)

Usage:
    uv run python src/machine_learning/evaluate_prediction_535_repeated.py -n 20
"""

from collections import defaultdict
from pathlib import Path
from typing import Dict, List

import click
from loguru import logger

from machine_learning.render_prediction_535 import Power535PredictionSummaryGenerator


@click.command()
@click.option(
    "--runs",
    "-n",
    type=int,
    default=20,
    help="Số lần chạy mô phỏng backtest ngẫu nhiên (mặc định: 20 lần)",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    default=None,
    help="Đường dẫn file markdown để ghi bảng kết quả (tùy chọn)",
)
def main(runs: int, output: Path | None) -> None:
    """Chạy backtest Power 5/35 N lần và thống kê kết quả trung bình."""
    logger.info(f"Bắt đầu chạy mô phỏng Power 5/35 trong {runs} lần...")

    generator = Power535PredictionSummaryGenerator()
    df = generator._load_lottery_data()
    if df.is_empty():
        logger.error("Không có dữ liệu cho Power 5/35.")
        return

    df_pd = df.to_pandas()

    stats: Dict[str, Dict[str, List[float]]] = defaultdict(
        lambda: {
            "cost": [],
            "gain": [],
            "profit": [],
            "roi": [],
        }
    )

    for run_idx in range(1, runs + 1):
        logger.info(f"--- Lượt chạy {run_idx}/{runs} ---")
        results = generator._build_and_run_strategies(df_pd)
        for name, _tpd, model in results:
            cost, gain, profit = model.revenue()
            roi = (profit / cost * 100) if cost > 0 else 0.0
            stats[name]["cost"].append(cost)
            stats[name]["gain"].append(gain)
            stats[name]["profit"].append(profit)
            stats[name]["roi"].append(roi)

    # Calculate average metrics per strategy
    summary_rows = []
    for name, data in stats.items():
        avg_cost = sum(data["cost"]) / runs
        avg_gain = sum(data["gain"]) / runs
        avg_profit = sum(data["profit"]) / runs
        avg_roi = sum(data["roi"]) / runs
        summary_rows.append((name, avg_cost, avg_gain, avg_profit, avg_roi))

    # Sort best -> worst by average ROI
    summary_rows.sort(key=lambda x: x[4], reverse=True)

    medals = ["🥇", "🥈", "🥉"] + ["  "] * len(summary_rows)
    header = f"## 📊 Thống Kê Trung Bình Performance Power 5/35 ({runs} Lượt Chạy)\n"
    table_header = "| Rank | Strategy | Total Cost (VND) | Total Gain (VND) | Net Profit (VND) | ROI |"
    sep = "|------|----------|-----------------|-----------------|-----------------|-----|"
    lines = [header, table_header, sep]

    for i, (name, cost, gain, profit, roi) in enumerate(summary_rows):
        lines.append(f"| {medals[i]} {i + 1:2d} | {name} | {cost:,.0f} | {gain:,.0f} | {profit:,.0f} | {roi:.2f}% |")

    markdown_result = "\n".join(lines) + "\n"

    print("\n" + markdown_result)

    if output:
        output.write_text(markdown_result, encoding="utf-8")
        logger.info(f"Đã lưu kết quả thống kê vào file: {output.absolute()}")


if __name__ == "__main__":
    main()
