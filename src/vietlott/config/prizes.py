"""Prize evaluation rules for Vietlott lottery products."""

from typing import Callable

# Type definition for a prize calculation function: (main_match, special_match) -> prize_in_vnd
PrizeFn = Callable[[int, int], int]


def _prize_for_power_655(main_match: int, special_match: int) -> int:
    """Prize structure for Power 6/55 (VND)."""
    if main_match == 6:
        return 30_000_000_000  # Jackpot 1 (minimum baseline)
    if main_match == 5 and special_match == 1:
        return 3_000_000_000  # Jackpot 2 (minimum baseline)
    if main_match == 5:
        return 40_000_000  # Giải Nhất
    if main_match == 4:
        return 500_000  # Giải Nhì
    if main_match == 3:
        return 50_000  # Giải Ba
    return 0


def _prize_for_power_645(main_match: int, special_match: int) -> int:
    """Prize structure for Power 6/45 (Mega 6/45) (VND)."""
    if main_match == 6:
        return 12_000_000_000  # Jackpot (minimum baseline)
    if main_match == 5:
        return 10_000_000  # Giải Nhất
    if main_match == 4:
        return 300_000  # Giải Nhì
    if main_match == 3:
        return 30_000  # Giải Ba
    return 0


def _prize_for_power_535(main_match: int, special_match: int) -> int:
    """Prize structure for Power 5/35 (VND)."""
    if main_match == 5 and special_match == 1:
        return 6_000_000_000  # Jackpot (minimum baseline)
    if main_match == 5:
        return 10_000_000  # Giải Nhất
    if main_match == 4 and special_match == 1:
        return 5_000_000  # Giải Nhì
    if main_match == 4:
        return 500_000  # Giải Ba
    if main_match == 3 and special_match == 1:
        return 100_000  # Giải Tư
    if main_match == 3:
        return 30_000  # Giải Năm
    if special_match == 1 and main_match >= 1:
        return 10_000  # Giải Khuyến khích
    return 0


def _prize_for_keno(main_match: int, special_match: int) -> int:
    """Prize structure for Keno (Bậc 6 default) (VND)."""
    if main_match == 6:
        return 12_500_000
    if main_match == 5:
        return 450_000
    if main_match == 4:
        return 40_000
    if main_match == 3:
        return 10_000
    return 0


def _prize_for_3d(main_match: int, special_match: int) -> int:
    """Prize structure for Max 3D (VND)."""
    if main_match >= 6:
        return 1_000_000
    if main_match == 5:
        return 350_000
    if main_match == 4:
        return 210_000
    if main_match == 3:
        return 100_000
    if main_match == 2:
        return 40_000
    if main_match == 1:
        return 10_000
    return 0


def _prize_for_3d_pro(main_match: int, special_match: int) -> int:
    """Prize structure for Max 3D Pro (VND)."""
    if main_match >= 6:
        return 2_000_000_000
    if main_match == 5:
        return 40_000_000
    if main_match == 4:
        return 10_000_000
    if main_match == 3:
        return 4_000_000
    if main_match == 2:
        return 1_000_000
    if main_match == 1:
        return 100_000
    return 0


def _prize_for_bingo18(main_match: int, special_match: int) -> int:
    """Prize structure for Bingo 18 (VND)."""
    if main_match >= 3:
        return 120_000
    if main_match == 2:
        return 20_000
    if main_match == 1:
        return 10_000
    return 0


PRODUCT_PRIZE_MAP: dict[str, PrizeFn] = {
    "power_655": _prize_for_power_655,
    "power_645": _prize_for_power_645,
    "power_535": _prize_for_power_535,
    "keno": _prize_for_keno,
    "3d": _prize_for_3d,
    "3d_pro": _prize_for_3d_pro,
    "bingo18": _prize_for_bingo18,
}


def get_prize_fn(product_name: str) -> PrizeFn:
    """Return the prize calculation function for a product.

    Defaults to Power 6/55 if the product name is unknown.
    """
    return PRODUCT_PRIZE_MAP.get(product_name, _prize_for_power_655)
