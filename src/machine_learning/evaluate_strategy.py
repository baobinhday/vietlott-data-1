"""
HƯỚNG DẪN SỬ DỤNG SCRIPT ĐÁNH GIÁ CHIẾN THUẬT (EVALUATE STRATEGY CLI)
----------------------------------------------------------------------
Script này cho phép bạn đánh giá tỷ lệ bao phủ (Coverage) và tỷ lệ trúng thưởng
của các chiến thuật dự đoán Vietlott với kích thước tập số K (candidate set) tùy chỉnh.

1. CÁCH ĐẠY SCRIPT
==================
Có 2 cách chạy lệnh từ thư mục gốc của project:

Cách 1: Sử dụng command CLI (Khuyên dùng)
    uv run vietlott-evaluate [CÁC THAM SỐ]

Cách 2: Chạy trực tiếp file Python
    uv run python src/machine_learning/evaluate_strategy.py [CÁC THAM SỐ]


2. BẢNG THAM SỐ TÙY CHỈNH (OPTIONS)
===================================
-p, --product       [6/55|6/45|5/35]
                    Loại hình Vietlott cần đánh giá (Mặc định: 6/55)

-k, --k INTEGER     Kích thước tập số K muốn generate.
                    Có thể truyền nhiều lần -k để kiểm tra nhiều tập K cùng lúc.
                    Ví dụ: -k 10 -k 15 -k 20 -k 25 -k 30
                    (Mặc định: 10, 15, 20)

-s, --strategy      [pair_frequency|hot_numbers|cold_numbers|exponential_decay|not_repeat|long_absence|markov_chain|all]
                    Chiến thuật cần kiểm tra (Mặc định: pair_frequency).
                    Chọn 'all' để đánh giá toàn bộ các chiến thuật.

-r, --runs INTEGER  Số lần mô phỏng Monte Carlo ngẫu nhiên độc lập (Mặc định: 50 lần).
                    Tăng số lần chạy giúp kết quả trung bình ổn định và chính xác hơn.

-n, --test-draws    Số kỳ quay lịch sử gần nhất dùng để thực hiện backtest (Mặc định: 100 kỳ).

--help              Hiển thị hướng dẫn tra cứu tham số nhanh.


3. VÍ DỤ SỬ DỤNG THỰC TẾ
========================
Ví dụ 1: Kiểm tra thuật toán Pair Frequency trên Power 6/55 cho các tập K = 12, 18, 25, 30 số
    uv run vietlott-evaluate -p 6/55 -s pair_frequency -k 12 -k 18 -k 25 -k 30

Ví dụ 2: Kiểm tra thuật toán Hot Numbers trên Mega 6/45 với 100 lần chạy ngẫu nhiên Monte Carlo
    uv run vietlott-evaluate -p 6/45 -s hot_numbers -k 15 -k 20 -r 100

Ví dụ 3: So sánh tất cả chiến thuật (strategy = all) trên Vietlott 5/35
    uv run vietlott-evaluate -p 5/35 -s all -k 10 -k 15 -k 20
"""

import math
from collections import Counter, defaultdict
from datetime import timedelta
from pathlib import Path

import click
import numpy as np
import pandas as pd
from loguru import logger

PRODUCTS = {
    "6/55": {"file": "data/power655.jsonl", "max_val": 55, "draw_size": 6},
    "6/45": {"file": "data/power645.jsonl", "max_val": 45, "draw_size": 6},
    "5/35": {"file": "data/power535.jsonl", "max_val": 35, "draw_size": 5},
}

STRATEGIES = [
    "pair_frequency",
    "hot_numbers",
    "cold_numbers",
    "exponential_decay",
    "not_repeat",
    "long_absence",
    "markov_chain",
    "all",
]


def sample_top_k(
    strategy_name: str, past_results: list, past_dates: list, target_date, k: int, min_val: int, max_val: int
) -> set:
    all_nums = np.arange(min_val, max_val + 1)

    if strategy_name in ("hot_numbers", "pair_frequency"):
        start_date = target_date - timedelta(days=365)
        filtered = [res for res, d in zip(past_results, past_dates) if d >= start_date]
        freq = Counter(n for res in filtered for n in res)
        weights = np.array([max(1, freq[n]) for n in all_nums], dtype=float)
        chosen = np.random.choice(all_nums, size=k, replace=False, p=weights / weights.sum())
        return set(chosen)

    elif strategy_name == "cold_numbers":
        start_date = target_date - timedelta(days=365)
        filtered = [res for res, d in zip(past_results, past_dates) if d >= start_date]
        freq = Counter(n for res in filtered for n in res)
        max_f = max(freq.values()) if freq else 1
        weights = np.array([max(1, max_f - freq[n] + 1) for n in all_nums], dtype=float)
        chosen = np.random.choice(all_nums, size=k, replace=False, p=weights / weights.sum())
        return set(chosen)

    elif strategy_name == "exponential_decay":
        decay_factor = math.log(2) / 90.0
        scores = defaultdict(float)
        for res, d in zip(past_results, past_dates):
            days_diff = (target_date - d).days
            if days_diff >= 0:
                w_val = math.exp(-decay_factor * days_diff)
                for n in res:
                    scores[n] += w_val
        weights = np.array([max(0.1, scores[n]) for n in all_nums], dtype=float)
        chosen = np.random.choice(all_nums, size=k, replace=False, p=weights / weights.sum())
        return set(chosen)

    elif strategy_name == "not_repeat":
        start_date = target_date - timedelta(days=30)
        recent_nums = set(n for res, d in zip(past_results, past_dates) if d >= start_date for n in res)
        weights = np.array([1.0 if n not in recent_nums else 0.2 for n in all_nums], dtype=float)
        chosen = np.random.choice(all_nums, size=k, replace=False, p=weights / weights.sum())
        return set(chosen)

    elif strategy_name == "long_absence":
        last_seen = {}
        for res, d in zip(past_results, past_dates):
            for n in res:
                last_seen[n] = d
        absence = [(target_date - last_seen[n]).days if n in last_seen else 9999 for n in all_nums]
        weights = np.array([max(1, a) for a in absence], dtype=float)
        chosen = np.random.choice(all_nums, size=k, replace=False, p=weights / weights.sum())
        return set(chosen)

    elif strategy_name == "markov_chain":
        start_date = target_date - timedelta(days=365)
        pairs_seq = [(res, d) for res, d in zip(past_results, past_dates) if d >= start_date]
        t_matrix = defaultdict(lambda: defaultdict(float))
        for i in range(len(pairs_seq) - 1):
            for a in pairs_seq[i][0]:
                for b in pairs_seq[i + 1][0]:
                    t_matrix[a][b] += 1.0
        last_draw = past_results[-1] if past_results else []
        scores = [sum(t_matrix[a][b] + 0.5 for a in last_draw) for b in all_nums]
        weights = np.array([max(0.1, s) for s in scores], dtype=float)
        chosen = np.random.choice(all_nums, size=k, replace=False, p=weights / weights.sum())
        return set(chosen)

    return set(np.random.choice(all_nums, size=k, replace=False))


@click.command()
@click.option(
    "--product",
    "-p",
    type=click.Choice(["6/55", "6/45", "5/35"]),
    default="6/55",
    help="Loại hình xổ số Vietlott (mặc định: 6/55)",
)
@click.option(
    "--k",
    "-k",
    type=int,
    multiple=True,
    default=[10, 15, 20],
    help="Số lượng số trong tập candidate K (ví dụ: -k 10 -k 15 -k 20)",
)
@click.option(
    "--strategy",
    "-s",
    type=click.Choice(STRATEGIES),
    default="pair_frequency",
    help="Chiến thuật dự đoán (mặc định: pair_frequency, hoặc 'all' để đánh giá toàn bộ)",
)
@click.option("--runs", "-r", type=int, default=50, help="Số lần chạy ngẫu nhiên Monte Carlo (mặc định: 50 lần)")
@click.option(
    "--test-draws",
    "-n",
    type=int,
    default=100,
    help="Số kỳ quay gần nhất dùng để đánh giá backtest (mặc định: 100 kỳ)",
)
def evaluate(product: str, k: tuple[int, ...], strategy: str, runs: int, test_draws: int) -> None:
    """Đánh giá tỷ lệ bao phủ và xác suất trúng của chiến thuật theo tập K tùy chọn."""
    prod_info = PRODUCTS[product]
    data_path = Path(prod_info["file"])

    if not data_path.exists():
        logger.error(f"Không tìm thấy file dữ liệu: {data_path}")
        return

    df = pd.read_json(data_path, lines=True)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)

    draw_size = prod_info["draw_size"]
    max_val = prod_info["max_val"]

    results_list = [row[:draw_size] for row in df["result"]]
    results_set = [set(row[:draw_size]) for row in df["result"]]
    dates = [d.date() for d in df["date"]]

    n_draws = len(results_list)
    actual_test_draws = min(test_draws, n_draws - 50)
    test_indices = list(range(n_draws - actual_test_draws, n_draws))

    selected_strategies = [s for s in STRATEGIES if s != "all"] if strategy == "all" else [strategy]
    k_list = sorted(list(set(k)))

    click.echo(
        f"\n==================== ĐÁNH GIÁ VIETLOTT {product} (Monte Carlo: {runs} runs x {actual_test_draws} kỳ) ===================="
    )

    for strat in selected_strategies:
        click.echo(f"\n--- Chiến thuật: {strat.upper()} ---")
        for k_val in k_list:
            if k_val < draw_size or k_val > max_val:
                logger.warning(f"K={k_val} không hợp lệ cho {product} (phải nằm trong khoảng [{draw_size}, {max_val}])")
                continue

            total_hits = 0
            cnt_100 = 0
            cnt_3plus = 0
            total_evals = actual_test_draws * runs

            for _ in range(runs):
                for idx in test_indices:
                    past_res = results_list[:idx]
                    past_dt = dates[:idx]
                    t_date = dates[idx]
                    actual = results_set[idx]

                    pred_set = sample_top_k(strat, past_res, past_dt, t_date, k_val, 1, max_val)
                    matches = len(pred_set.intersection(actual))

                    total_hits += matches
                    if matches >= draw_size:
                        cnt_100 += 1
                    if matches >= 3:
                        cnt_3plus += 1

            avg_hits = total_hits / total_evals
            cov_pct = (avg_hits / float(draw_size)) * 100
            pct_100 = (cnt_100 / total_evals) * 100
            pct_3p = (cnt_3plus / total_evals) * 100

            click.echo(
                f"  K={k_val:2d} số: Hits TB = {avg_hits:.3f}/{draw_size} ({cov_pct:5.1f}%) | "
                f"Trúng 100% ({draw_size}/{draw_size}): {cnt_100:4d} lần ({pct_100:6.3f}%) | "
                f"Trúng >=3 số: {pct_3p:5.1f}%"
            )


if __name__ == "__main__":
    evaluate()
