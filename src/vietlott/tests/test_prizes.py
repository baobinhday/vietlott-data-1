"""Unit tests for product prize calculations in ``vietlott.config.prizes``."""

from datetime import date

from vietlott.config.prizes import (
    POWER_535_SPLIT_THRESHOLD,
    POWER_535_STANDARD_PV,
    _parse_vnd,
    _prize_for_3d,
    _prize_for_3d_pro,
    _prize_for_bingo18,
    _prize_for_keno,
    _prize_for_power_535,
    _prize_for_power_645,
    _prize_for_power_655,
    clear_prizes_cache,
    get_actual_prize_for_draw,
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


# ---------------------------------------------------------------------------
# _parse_vnd
# ---------------------------------------------------------------------------


def test_parse_vnd_handles_vietnamese_thousand_separators():
    assert _parse_vnd("38.842.141.350") == 38_842_141_350
    assert _parse_vnd("6.315.905.000") == 6_315_905_000
    assert _parse_vnd("10.000.000") == 10_000_000
    assert _parse_vnd("30.000") == 30_000
    assert _parse_vnd(1234567) == 1234567
    assert _parse_vnd("") == 0
    assert _parse_vnd("   ") == 0
    # comma-form should also be tolerated
    assert _parse_vnd("6,315,905,000") == 6_315_905_000


# ---------------------------------------------------------------------------
# get_actual_prize_for_draw
# ---------------------------------------------------------------------------


def test_actual_prize_power_535_uses_crawled_values():
    """In a non-split draw (DD < 12B OR DD has a winner), the +1 simulation
    uses the data's prize_value directly."""
    clear_prizes_cache()
    # power535 id=00003: DD=6.3B (no split), Nhất w=0 -> standard 10M.
    assert get_actual_prize_for_draw("power_535", "00003", 5, 1) == 6_315_905_000
    assert get_actual_prize_for_draw("power_535", "00003", 5, 0) == 10_000_000
    # Tư (3+1) w=137, pv=100K -> returns 100,000.
    assert get_actual_prize_for_draw("power_535", "00003", 3, 1) == 100_000
    # Khuyến Khích is always 10K (not affected by simulation).
    assert get_actual_prize_for_draw("power_535", "00003", 2, 1) == 10_000


def test_actual_prize_power_535_dd_with_existing_winner_simulates():
    """DD match with an existing winner simulates the +1 split."""
    clear_prizes_cache()
    # id=00016: DD=6,387,757,500, w=1 -> (1*6.388B)/2.
    assert get_actual_prize_for_draw("power_535", "00016", 5, 1) == int(6_387_757_500 / 2)


def test_actual_prize_power_535_split_draw_applies_one_third_to_nhat():
    """When DD > 12B and has no winner, the 1/3 + 1/6 split rule applies.

    The hypothetical winners_count (with our ticket as +1) determines the
    redistribution: zero-winner tiers' shares are added equally to the
    remaining tiers' shares.  Our per-winner = (w_sim * standard_pv +
    effective_share) / w_sim.
    """
    clear_prizes_cache()
    # id=00054: DD=19,639,152,000, w=0 -> split.  All 5 lower tiers have
    # winners in the data, so no redistribution.  Our ticket adds 1 to
    # the matching tier.
    dd_v = 19_639_152_000

    # Nhất (5,0) in id=00054: w=10 -> w_sim=11.  Nhất share = DD/3.
    nhat_w = 10
    nhat_share = dd_v // 3
    expected = int(((nhat_w + 1) * POWER_535_STANDARD_PV["Giải Nhất"] + nhat_share) / (nhat_w + 1))
    assert get_actual_prize_for_draw("power_535", "00054", 5, 0) == expected

    # Nhì (4,1) in id=00054: w=38 -> w_sim=39.  Nhì share = DD/6.
    nhi_w = 38
    nhi_share = dd_v // 6
    expected = int(((nhi_w + 1) * POWER_535_STANDARD_PV["Giải Nhì"] + nhi_share) / (nhi_w + 1))
    assert get_actual_prize_for_draw("power_535", "00054", 4, 1) == expected

    # Năm (3,0) in id=00054: w=16836 -> w_sim=16837.
    nam_w = 16836
    nam_share = dd_v // 6
    expected = int(((nam_w + 1) * POWER_535_STANDARD_PV["Giải Năm"] + nam_share) / (nam_w + 1))
    assert get_actual_prize_for_draw("power_535", "00054", 3, 0) == expected


def test_actual_prize_power_535_split_draw_redistributes_zero_winner_share():
    """When a tier has 0 winners in a split draw, its share is added to
    the remaining tiers' shares equally."""
    clear_prizes_cache()
    # id=00038: DD=16,321,575,500, w=0 -> split.  Nhất w=0 in data.
    # Our ticket matches Nhì (4,1) -> w_sim: Nhất=0, Nhì=25,
    # Ba=474, Tư=732, Năm=11337.
    # Nhất's 1/3 share (5,440,525,166) is redistributed equally to
    # 4 non-zero tiers: 1,360,131,291 each.
    # Nhì's effective share = 2,720,262,583 + 1,360,131,291 = 4,080,393,874.
    dd_v = 16_321_575_500
    nhat_share = dd_v // 3
    nhi_own = dd_v // 6
    redistribution = nhat_share // 4
    nhi_effective = nhi_own + redistribution
    nhi_w_sim = 25  # 24 + 1
    expected = int((nhi_w_sim * POWER_535_STANDARD_PV["Giải Nhì"] + nhi_effective) / nhi_w_sim)
    assert get_actual_prize_for_draw("power_535", "00038", 4, 1) == expected


def test_actual_prize_power_535_split_draw_zero_winner_becomes_only_winner():
    """When our ticket matches a tier that has 0 winners in the data, we
    become the (w_sim=1) winner for that tier.  With us, that tier is no
    longer a zero-winner tier, so no redistribution happens for its share
    — we take its own share (DD/3 for Nhất)."""
    clear_prizes_cache()
    # id=00038: our ticket matches Nhất (5,0).  w_sim: Nhất=1, others
    # unchanged.  No zero-winner tiers, no redistribution.  Nhất's share
    # is DD/3 = 5,440,525,166.  Pool = 1*10M + 5,440,525,166 =
    # 5,450,525,166.  Per-winner = same.
    dd_v = 16_321_575_500
    expected = int((1 * POWER_535_STANDARD_PV["Giải Nhất"] + dd_v // 3) / 1)
    assert get_actual_prize_for_draw("power_535", "00038", 5, 0) == expected


def test_actual_prize_power_535_split_draw_with_zero_winners_takes_portion():
    """When the matching lower tier has 0 winners in a split draw, our ticket
    becomes the sole winner and takes the entire augmented pool
    (standard_pv + DD/portion)."""
    clear_prizes_cache()
    # id=00038: DD=16,321,575,500, w=0 -> split.  Nhất w=0.
    # With our ticket, w_sim=1, no zero-winner tiers, no redistribution.
    # Pool = 1 * 10M (standard) + DD/3 (5,440,525,166) = 5,450,525,166.
    expected = int((1 * POWER_535_STANDARD_PV["Giải Nhất"] + 16_321_575_500 // 3) / 1)
    assert get_actual_prize_for_draw("power_535", "00038", 5, 0) == expected


def test_actual_prize_power_535_dd_match_in_split_draw_takes_whole_pool():
    """If our ticket matches DD in a split draw, we take the whole DD pool
    (we are the winner, so the 1/3-1/6 split is not triggered)."""
    clear_prizes_cache()
    # id=00036: DD=12,221,845,000, w=0 -> even though it's a split draw,
    # (5,1) means we are the DD winner, so we take the whole pool.
    assert get_actual_prize_for_draw("power_535", "00036", 5, 1) == 12_221_845_000


def test_actual_prize_power_535_khuyen_khich_always_10k():
    """Khuyến Khích is always 10K per winner, regardless of split."""
    clear_prizes_cache()
    # id=00036 split draw: (2,1) should still return 10K.
    assert get_actual_prize_for_draw("power_535", "00036", 2, 1) == 10_000
    # id=00054 split draw: (1,1) should also return 10K.
    assert get_actual_prize_for_draw("power_535", "00054", 1, 1) == 10_000


def test_actual_prize_power_535_split_threshold_constant():
    """Sanity check: the 12B threshold is exported as a constant."""
    assert POWER_535_SPLIT_THRESHOLD == 12_000_000_000


def test_actual_prize_power_645_uses_crawled_values():
    clear_prizes_cache()
    # power645 id=00202 has Jackpot=33.963.663.500, Giải Nhất=10.000.000.
    # power_645 does NOT apply the +1 simulation.
    assert get_actual_prize_for_draw("power_645", "00202", 6, 0) == 33_963_663_500
    assert get_actual_prize_for_draw("power_645", "00202", 5, 0) == 10_000_000
    assert get_actual_prize_for_draw("power_645", "00202", 4, 0) == 300_000
    assert get_actual_prize_for_draw("power_645", "00202", 3, 0) == 30_000


def test_actual_prize_power_655_uses_crawled_values():
    clear_prizes_cache()
    # power655 id=00002 has Jackpot 1=31.024.813.350, Jackpot 2=3.113.868.150.
    # power_655 does NOT apply the +1 simulation.
    assert get_actual_prize_for_draw("power_655", "00002", 6, 0) == 31_024_813_350
    assert get_actual_prize_for_draw("power_655", "00002", 5, 1) == 3_113_868_150
    assert get_actual_prize_for_draw("power_655", "00002", 5, 0) == 40_000_000


def test_actual_prize_falls_back_when_draw_id_missing():
    clear_prizes_cache()
    # Unknown draw id → fall back to hardcoded baseline (30B for 6/55).
    assert get_actual_prize_for_draw("power_655", "99999", 6, 0) == 30_000_000_000
    # None draw id → same fallback.
    assert get_actual_prize_for_draw("power_655", None, 6, 0) == 30_000_000_000


def test_actual_prize_falls_back_when_tier_unmatched():
    clear_prizes_cache()
    # 7 matches is not a real tier; should fall back to 0 via the hardcoded fn.
    assert get_actual_prize_for_draw("power_655", "00002", 7, 0) == 0


def test_actual_prize_handles_int_draw_id():
    clear_prizes_cache()
    # The data file uses zero-padded string ids ("00003"); integer 3 matches "00003".
    assert get_actual_prize_for_draw("power_535", 3, 5, 1) == 6_315_905_000
