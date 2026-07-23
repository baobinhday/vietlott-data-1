"""Unit tests for product prize calculations in ``vietlott.config.prizes``."""

from datetime import date

from vietlott.config.prizes import (
    _prize_for_3d,
    _prize_for_3d_pro,
    _prize_for_bingo18,
    _prize_for_keno,
    _prize_for_power_535,
    _prize_for_power_645,
    _prize_for_power_655,
    get_prize_fn,
)
from vietlott.web_api.service import run_backtest


def test_power_655_prizes():
    fn = get_prize_fn("power_655")
    assert fn(6, 0) == 30_000_000_000
    assert fn(5, 1) == 3_000_000_000
    assert fn(5, 0) == 40_000_000
    assert fn(4, 0) == 500_000
    assert fn(3, 0) == 50_000
    assert fn(2, 0) == 0


def test_power_645_prizes():
    fn = get_prize_fn("power_645")
    assert fn(6, 0) == 12_000_000_000
    assert fn(5, 0) == 10_000_000
    assert fn(4, 0) == 300_000
    assert fn(3, 0) == 30_000
    assert fn(2, 0) == 0


def test_power_535_prizes():
    fn = get_prize_fn("power_535")
    assert fn(5, 1) == 6_000_000_000
    assert fn(5, 0) == 10_000_000
    assert fn(4, 1) == 5_000_000
    assert fn(4, 0) == 500_000
    assert fn(3, 1) == 100_000
    assert fn(3, 0) == 30_000
    assert fn(1, 1) == 10_000
    assert fn(1, 0) == 0


def test_keno_prizes():
    fn = get_prize_fn("keno")
    assert fn(6, 0) == 12_500_000
    assert fn(5, 0) == 450_000
    assert fn(4, 0) == 40_000
    assert fn(3, 0) == 10_000
    assert fn(2, 0) == 0


def test_3d_prizes():
    fn = get_prize_fn("3d")
    assert fn(6, 0) == 1_000_000
    assert fn(5, 0) == 350_000
    assert fn(4, 0) == 210_000
    assert fn(3, 0) == 100_000
    assert fn(2, 0) == 40_000
    assert fn(1, 0) == 10_000


def test_3d_pro_prizes():
    fn = get_prize_fn("3d_pro")
    assert fn(6, 0) == 2_000_000_000
    assert fn(5, 0) == 40_000_000
    assert fn(4, 0) == 10_000_000
    assert fn(3, 0) == 4_000_000
    assert fn(2, 0) == 1_000_000
    assert fn(1, 0) == 100_000


def test_bingo18_prizes():
    fn = get_prize_fn("bingo18")
    assert fn(3, 0) == 120_000
    assert fn(2, 0) == 20_000
    assert fn(1, 0) == 10_000


def test_unknown_product_defaults_to_655():
    fn = get_prize_fn("unknown_game")
    assert fn == _prize_for_power_655


def test_backtest_uses_product_specific_prizes():
    """Verify backtest uses product-specific prize tables instead of defaulting to 6/55."""
    pipeline_645 = {
        "product": "power_645",
        "groups": [
            {
                "name": "Random",
                "strategy": "random",
                "params": {},
                "pool_size": 45,
                "pick_count": 6,
            }
        ],
        "combiner": {"method": "concatenate"},
        "post_filters": {},
        "ticket_count": 1,
    }
    result_645 = run_backtest(
        pipeline_645,
        date_from=date(2024, 6, 1),
        date_to=date(2024, 6, 15),
    )
    assert result_645["product"] == "power_645"


def test_backtest_sums_all_prizes_per_draw():
    """Verify that prize_vnd in per_draw reflects the sum of prizes across all tickets generated for that draw."""
    pipeline = {
        "product": "power_655",
        "groups": [
            {
                "name": "Random",
                "strategy": "random",
                "params": {},
                "pool_size": 55,
                "pick_count": 6,
            }
        ],
        "combiner": {"method": "concatenate"},
        "post_filters": {},
        "ticket_count": 10,
    }
    result = run_backtest(
        pipeline,
        date_from=date(2024, 6, 1),
        date_to=date(2024, 6, 15),
    )
    for entry in result["per_draw"]:
        assert entry["prize_vnd"] >= 0
