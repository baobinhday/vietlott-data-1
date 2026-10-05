"""Sales-free jackpot rollover timing signal for Power 6/45 and Power 6/55.

Vietlott does not publish ticket-sales data, so the timing signal is derived
purely from the crawled per-draw prize data: whether the top jackpot rolled
over (``winners_count == 0``), how large the current pool has grown relative
to its published minimum, and how many consecutive draws it has carried.
"""

from typing import Any

from loguru import logger

from vietlott.config.prizes import _load_prizes_index

# Published minimum jackpot (VND) for each supported product.
ROLLOVER_MIN: dict[str, int] = {
    "power_645": 12_000_000_000,
    "power_655": 30_000_000_000,
}

# Tier name that carries the top jackpot pool for each product.
JACKPOT_TIER: dict[str, str] = {
    "power_645": "Jackpot",
    "power_655": "Jackpot 1",
}

# Pool-size thresholds expressed as a multiple of ROLLOVER_MIN.
_WARM_MULTIPLE: float = 1.5
_HOT_MULTIPLE: float = 2.5

# Consecutive no-winner thresholds.
_WARM_STREAK: int = 3
_HOT_STREAK: int = 6


def _unknown_state(product: str) -> dict[str, Any]:
    """Return the neutral signal used when prize data is unavailable."""
    return {
        "product": product,
        "latest_draw_id": None,
        "jackpot_value": 0,
        "jackpot_winners": 0,
        "streak": 0,
        "multiple_of_min": 0.0,
        "level": "unknown",
    }


def _canonical_draw_id(raw: str) -> str:
    """Fold the loader's integer aliases ("1568") onto the padded form ("01568")."""
    if raw.isdigit():
        return f"{int(raw):05d}"
    return raw


def _sort_key(draw_id: str) -> tuple[int, Any]:
    """Sort numeric draw ids numerically and any others lexicographically."""
    if draw_id.isdigit():
        return (0, int(draw_id))
    return (1, draw_id)


def get_rollover_state(product: str) -> dict[str, Any]:
    """Compute the rollover timing signal for ``product``.

    Reads the per-draw prize index, takes the latest draw by draw id, then
    walks backwards counting consecutive draws whose jackpot tier had zero
    winners (the rollover streak).  The level is:

    * ``"hot"`` when the pool is at least 2.5× the minimum or the streak is
      at least 6,
    * ``"warm"`` when the pool is at least 1.5× the minimum or the streak is
      at least 3,
    * ``"cold"`` otherwise,
    * ``"unknown"`` when the product is unsupported or prize data is empty.

    Never raises; missing or malformed data yields the ``"unknown"`` state.
    """
    if product not in ROLLOVER_MIN or product not in JACKPOT_TIER:
        return _unknown_state(product)

    try:
        index = _load_prizes_index(product)
    except Exception as exc:  # pragma: no cover - defensive, loader never raises today
        logger.warning("rollover: failed to load prize index for {}: {}", product, exc)
        return _unknown_state(product)

    if not index:
        return _unknown_state(product)

    # The loader stores several aliases per draw; fold them onto one id.
    draws: dict[str, dict[str, dict[str, int]]] = {}
    for raw_id, tiers in index.items():
        draws.setdefault(_canonical_draw_id(str(raw_id)), tiers)

    ordered = sorted(draws.items(), key=lambda item: _sort_key(item[0]))
    if not ordered:
        return _unknown_state(product)

    tier_name = JACKPOT_TIER[product]
    min_value = ROLLOVER_MIN[product]

    latest_draw_id, latest_tiers = ordered[-1]
    latest_jackpot = latest_tiers.get(tier_name, {})
    jackpot_value = int(latest_jackpot.get("prize_value", 0))
    jackpot_winners = int(latest_jackpot.get("winners_count", 0))

    streak = 0
    for _, tiers in reversed(ordered):
        tier = tiers.get(tier_name)
        winners = int(tier.get("winners_count", 0)) if tier else 0
        if winners != 0:
            break
        streak += 1

    multiple = jackpot_value / min_value if min_value else 0.0
    if multiple >= _HOT_MULTIPLE or streak >= _HOT_STREAK:
        level = "hot"
    elif multiple >= _WARM_MULTIPLE or streak >= _WARM_STREAK:
        level = "warm"
    else:
        level = "cold"

    return {
        "product": product,
        "latest_draw_id": latest_draw_id,
        "jackpot_value": jackpot_value,
        "jackpot_winners": jackpot_winners,
        "streak": streak,
        "multiple_of_min": multiple,
        "level": level,
    }


def should_play(product: str) -> bool:
    """Return True when the rollover signal recommends playing ``product``."""
    return get_rollover_state(product)["level"] in ("warm", "hot")
