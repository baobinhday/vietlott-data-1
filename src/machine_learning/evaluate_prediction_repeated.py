#!/usr/bin/env python
"""
Repeated backtest evaluator for Vietlott prediction strategies across multiple products (5/35, 6/45, 6/55).

Runs the prediction generator N times (default N=20) for specified product(s) and computes average financial metrics:
- Average Total Cost (VND)
- Average Total Gain (VND)
- Average Net Profit (VND)
- Average ROI (%)

Usage:
    uv run vietlott-eval-repeated -p 6/45 -n 20
    uv run vietlott-eval-repeated -p all -n 20
"""

from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Type

import click
from loguru import logger

from machine_learning.render_prediction_535 import Power535PredictionSummaryGenerator
from machine_learning.render_prediction_645 import Power645PredictionSummaryGenerator
from machine_learning.render_prediction_655 import HybridPredictionSummaryGenerator
from machine_learning.render_prediction_base import BasePowerPredictionSummaryGenerator

PRODUCT_GENERATORS: Dict[str, Type[BasePowerPredictionSummaryGenerator]] = {
    "5/35": Power535PredictionSummaryGenerator,
    "535": Power535PredictionSummaryGenerator,
    "6/45": Power645PredictionSummaryGenerator,
    "645": Power645PredictionSummaryGenerator,
    "6/55": HybridPredictionSummaryGenerator,
    "655": HybridPredictionSummaryGenerator,
}


def evaluate_product(generator_cls: Type[BasePowerPredictionSummaryGenerator], runs: int) -> str:
    """Evaluate a single product generator N times and return formatted markdown table."""
    generator = generator_cls()
    display_name = generator.PRODUCT_DISPLAY
    logger.info(f"Bắt đầu chạy mô phỏng {display_name} trong {runs} lần...")

    df = generator._load_lottery_data()
    if df.is_empty():
        logger.error(f"Không có dữ liệu cho {display_name}.")
        return f"### {display_name}\n\n> Không có dữ liệu.\n"

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
        logger.info(f"[{display_name}] --- Lượt chạy {run_idx}/{runs} ---")
        results = generator._build_and_run_strategies(df_pd)
        for name, _tpd, model in results:
            cost, gain, profit = model.revenue()
            roi = (profit / cost * 100) if cost > 0 else 0.0
            stats[name]["cost"].append(cost)
            stats[name]["gain"].append(gain)
            stats[name]["profit"].append(profit)
            stats[name]["roi"].append(roi)

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
    header = f"## 📊 Thống Kê Trung Bình Performance {display_name} ({runs} Lượt Chạy)\n"
    table_header = "| Rank | Strategy | Total Cost (VND) | Total Gain (VND) | Net Profit (VND) | ROI |"
    sep = "|------|----------|-----------------|-----------------|-----------------|-----|"
    lines = [header, table_header, sep]

    for i, (name, cost, gain, profit, roi) in enumerate(summary_rows):
        lines.append(f"| {medals[i]} {i + 1:2d} | {name} | {cost:,.0f} | {gain:,.0f} | {profit:,.0f} | {roi:.2f}% |")

    return "\n".join(lines) + "\n"


@click.command()
@click.option(
    "--product",
    "-p",
    type=click.Choice(["5/35", "535", "6/45", "645", "6/55", "655", "all"], case_sensitive=False),
    default="5/35",
    help="Sản phẩm Vietlott cần đánh giá (5/35, 6/45, 6/55 hoặc 'all'). Mặc định: 5/35",
)
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
def main(product: str, runs: int, output: Path | None) -> None:
    """Chạy backtest Vietlott N lần và thống kê kết quả trung bình cho sản phẩm lựa chọn."""
    if product.lower() == "all":
        targets = ["5/35", "6/45", "6/55"]
    else:
        targets = [product]

    markdown_results = []
    for p in targets:
        gen_cls = PRODUCT_GENERATORS[p]
        res = evaluate_product(gen_cls, runs)
        markdown_results.append(res)

    full_output = "\n\n".join(markdown_results)
    print("\n" + full_output)

    if output:
        output.write_text(full_output, encoding="utf-8")
        logger.info(f"Đã lưu kết quả thống kê vào file: {output.absolute()}")


if __name__ == "__main__":
    main()
