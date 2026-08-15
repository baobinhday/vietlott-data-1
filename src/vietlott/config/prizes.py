"""Prize evaluation rules for Vietlott lottery products."""

import json
from functools import lru_cache
from pathlib import Path
from typing import Callable

# Type definition for a prize calculation function: (main_match, special_match) -> prize_in_vnd
PrizeFn = Callable[[int, int], int]

# Project root (src/vietlott/config/prizes.py -> ../../..)
DATA_DIR: Path = Path(__file__).resolve().parents[3] / "data"

# Map product key -> on-disk file stem for the prize NDJSON.
PRODUCT_FILE_MAP: dict[str, str] = {
    "power_535": "power535",
    "power_645": "power645",
    "power_655": "power655",
}

# Ordered (main_match, special_match) -> prize_name used by Vietlott
# for each product.  The first matching entry wins, so more specific
# (main_match, special_match) pairs must come before more generic ones.
# The "Giải Khuyến Khích" / "Khuyến khích" tier for power_535 is handled
# separately because it covers every (m>=1, s==1) that did not match a
# higher tier.
PRIZE_NAME_MAP: dict[str, list[tuple[int, int, str]]] = {
    "power_535": [
        (5, 1, "Giải Độc Đắc"),
        (5, 0, "Giải Nhất"),
        (4, 1, "Giải Nhì"),
        (4, 0, "Giải Ba"),
        (3, 1, "Giải Tư"),
        (3, 0, "Giải Năm"),
    ],
    "power_645": [
        (6, 0, "Jackpot"),
        (5, 0, "Giải Nhất"),
        (4, 0, "Giải Nhì"),
        (3, 0, "Giải Ba"),
    ],
    "power_655": [
        (6, 0, "Jackpot 1"),
        (5, 1, "Jackpot 2"),
        (5, 0, "Giải Nhất"),
        (4, 0, "Giải Nhì"),
        (3, 0, "Giải Ba"),
    ],
}

# power_535: any (main_match >= 1, special_match == 1) that did not win
# a higher tier falls into the consolation prize.
_POWER_535_CONSOLATION_NAMES: tuple[str, ...] = (
    "Giải Khuyến Khích",
    "Giải Khuyến khích",
    "Khuyến Khích",
    "Khuyến khích",
)

# ---------------------------------------------------------------------------
# Power 5/35 split rules (per product owner)
# ---------------------------------------------------------------------------
# When the Độc Đắc jackpot exceeds the threshold AND has no winner in a
# given draw, Vietlott redistributes the jackpot pool to the lower tiers
# in fixed proportions:
#   * 1/3 of the jackpot → Giải Nhất
#   * 1/6 of the jackpot → each of Giải Nhì, Giải Ba, Giải Tư, Giải Năm
#   * Giải Khuyến Khích is NOT part of the split
# This means a backtest ticket that matches one of those tiers in such a
# draw sees an "augmented" pool (standard + DD contribution) which the
# simulation must account for.
POWER_535_SPLIT_THRESHOLD: int = 12_000_000_000  # 12B (per product owner)

# Per-tier "standard" per-winner amount used as the base for the split
# simulation.  These are the same values returned by
# ``_prize_for_power_535`` and match the prize_value seen in non-split
# draws.
POWER_535_STANDARD_PV: dict[str, int] = {
    "Giải Nhất": 10_000_000,
    "Giải Nhì": 5_000_000,
    "Giải Ba": 500_000,
    "Giải Tư": 100_000,
    "Giải Năm": 30_000,
}


def _parse_vnd(value: str | int | float) -> int:
    """Parse a Vietlott prize string ("6.315.905.000") into an int (VND)."""
    if isinstance(value, (int, float)):
        return int(value)
    cleaned = str(value).strip().replace(".", "").replace(",", "").replace(" ", "")
    if not cleaned:
        return 0
    return int(cleaned)


def _parse_winners_count(value: str | int | float | None) -> int:
    """Parse a Vietlott winners_count string ("1.589") into an int."""
    if value is None:
        return 0
    if isinstance(value, (int, float)):
        return int(value)
    cleaned = str(value).strip().replace(".", "").replace(",", "").replace(" ", "")
    if not cleaned:
        return 0
    return int(cleaned)


def _lookup_prize_name(product: str, main_match: int, special_match: int) -> str | None:
    """Return the Vietlott prize name for (main_match, special_match), or None."""
    for m, s, name in PRIZE_NAME_MAP.get(product, []):
        if m == main_match and s == special_match:
            return name
    if product == "power_535" and special_match == 1 and 0 <= main_match <= 2:
        return _POWER_535_CONSOLATION_NAMES[0]
    return None


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
    if special_match == 1 and main_match >= 0:
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


# ---------------------------------------------------------------------------
# Per-draw prize lookup backed by data/<product>_prizes.jsonl
# ---------------------------------------------------------------------------


def _normalize_prize_record(product: str, record: dict) -> dict[str, dict[str, int]]:
    """Return a ``{prize_name: {"prize_value": int, "winners_count": int}}`` dict.

    Tolerant of the multiple spellings Vietlott uses ("Giải Khuyến Khích"
    vs "Giải Khuyến khích") by folding names to a canonical key.
    """
    out: dict[str, dict[str, int]] = {}
    for p in record.get("prizes", []):
        name = (p.get("prize_name") or "").strip()
        value = _parse_vnd(p.get("prize_value", 0))
        winners = _parse_winners_count(p.get("winners_count", 0))
        out[name] = {"prize_value": value, "winners_count": winners}
        # Fold power_535 consolation names onto the canonical form so
        # lookups do not need to know the exact spelling.
        if product == "power_535" and name in _POWER_535_CONSOLATION_NAMES:
            out[_POWER_535_CONSOLATION_NAMES[0]] = {"prize_value": value, "winners_count": winners}
    return out


@lru_cache(maxsize=8)
def _load_prizes_index(product: str) -> dict[str, dict[str, dict[str, int]]]:
    """Load data/<product>_prizes.jsonl into ``{draw_id: {prize_name: {pv, w}}}``.

    Cached per product.  Returns an empty dict if the file is missing.
    """
    stem = PRODUCT_FILE_MAP.get(product)
    if not stem:
        return {}
    path = DATA_DIR / f"{stem}_prizes.jsonl"
    if not path.exists():
        return {}
    index: dict[str, dict[str, dict[str, int]]] = {}
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            draw_id = record.get("id")
            if draw_id is None:
                continue
            raw_id = str(draw_id).strip()
            norm = _normalize_prize_record(product, record)
            index[raw_id] = norm
            try:
                val = int(raw_id)
                index[str(val)] = norm
                index[f"{val:05d}"] = norm
            except ValueError:
                pass
    return index


def clear_prizes_cache() -> None:
    """Clear the in-memory prize index cache (useful for tests)."""
    _load_prizes_index.cache_clear()


def get_actual_prize_for_draw(
    product: str,
    draw_id: str | int | None,
    main_match: int,
    special_match: int,
) -> int:
    """Return the actual prize (VND) for a given draw from the crawled data.

    Behaviour
    ---------
    * Falls back to :func:`get_prize_fn` (hardcoded baseline) when the
      draw is not present in the prize file, when the product has no
      prize file, or when the matching tier name cannot be resolved.
    * For ``power_535``, applies the official Vietlott split rule:

      1. **Trigger** – Độc Đắc > 12B AND Độc Đắc has 0 winners in this
         draw.  Per the official rules, the trigger also requires
         "consecutive" prior draws without a Độc Đắc winner and the
         split itself fires at the 2nd session (21:00) of the day
         after the trigger.  The current implementation uses a
         simplified per-draw check (DD > 12B AND w=0 in the current
         draw), which captures the main idea of the rule but may
         over-fire for the first draw that crosses 12B without prior
         rollover history.  Verified against the actual 5/35 data: 16
         split events all happen in sess=2, and the simplified rule
         correctly identifies those (the 19 sess=2 triggers that the
         simplified rule would over-fire on are first-crossing draws
         where the data shows no augmentation yet).

      2. **Distribution** – the entire Độc Đắc pool is split as:
         ``Giải Nhất: 1/3``, each of ``Giải Nhì / Ba / Tư / Năm: 1/6``,
         ``Giải Khuyến Khích: 0``.

      3. **Redistribution** – if a tier in the above list has 0 winners
         in this draw, its share is cumulatively added and divided
         equally among the remaining tiers (with ``w > 0``).

      4. **Our ticket** is the +1 winner in its matching tier.  The
         per-winner prize is ``(w_sim * standard_pv + effective_share)
         / w_sim`` where ``w_sim`` includes our +1 and the
         redistribution is recomputed with the hypothetical
         ``w_sim`` count.

      For non-split draws or non-matching tiers, the data's
      ``prize_value`` is used directly with the +1 simulation.

    * For ``power_645`` / ``power_655`` (and any other product), returns
      ``prize_value`` directly without the +1-winner simulation.
    """
    fallback = PRODUCT_PRIZE_MAP.get(product, _prize_for_power_655)
    if draw_id is None:
        return fallback(main_match, special_match)

    index = _load_prizes_index(product)
    draw_id_str = str(draw_id).strip()
    prizes = index.get(draw_id_str)
    if not prizes:
        try:
            val = int(draw_id_str)
            prizes = index.get(str(val)) or index.get(f"{val:05d}")
        except ValueError:
            pass
    if not prizes:
        return fallback(main_match, special_match)

    prize_name = _lookup_prize_name(product, main_match, special_match)
    if prize_name is None:
        return fallback(main_match, special_match)

    # Try the resolved name first, then any consolation alias.
    tier_info = prizes.get(prize_name)
    if tier_info is None and product == "power_535":
        for alias in _POWER_535_CONSOLATION_NAMES:
            if alias in prizes:
                tier_info = prizes[alias]
                break
    if tier_info is None:
        return fallback(main_match, special_match)

    pv = int(tier_info["prize_value"])
    w = int(tier_info["winners_count"])

    if product != "power_535":
        return pv

    # --- power_535: full simulation with 1/3-1/6 split + redistribution ---
    # Độc Đắc match (5 main + 1 special).
    if main_match == 5 and special_match == 1:
        dd = prizes.get("Giải Độc Đắc")
        if dd is None:
            return fallback(main_match, special_match)
        dd_w = int(dd["winners_count"])
        dd_v = int(dd["prize_value"])
        if dd_w == 0:
            return dd_v  # We are the only winner, take the whole pool.
        return int(dd_v * dd_w / (dd_w + 1))

    # Consolation (Khuyến Khích) is always 10K per winner, not part of split.
    if prize_name in _POWER_535_CONSOLATION_NAMES:
        return 10_000

    # Lower-tier match.  Detect split event.
    dd = prizes.get("Giải Độc Đắc")
    is_split = False
    dd_v = 0
    if dd is not None:
        dd_v = int(dd["prize_value"])
        dd_w = int(dd["winners_count"])
        nhi_info = prizes.get("Giải Nhì", {})
        nhi_v = int(nhi_info.get("prize_value", 0))
        is_split = dd_v > POWER_535_SPLIT_THRESHOLD and dd_w == 0 and nhi_v > POWER_535_STANDARD_PV["Giải Nhì"]

    if not is_split or prize_name not in POWER_535_STANDARD_PV:
        # Non-split (or no Độc Đắc info): use the data's prize_value directly
        return pv

    # Split case.  Build the hypothetical winners_count (with our +1)
    # and apply the redistribution rule.
    split_tiers: tuple[str, ...] = (
        "Giải Nhất",
        "Giải Nhì",
        "Giải Ba",
        "Giải Tư",
        "Giải Năm",
    )
    tier_w_sim: dict[str, int] = {}
    for t in split_tiers:
        if t == prize_name:
            tier_w_sim[t] = w + 1  # our ticket is the +1 winner
        else:
            t_data = prizes.get(t, {})
            tier_w_sim[t] = int(t_data.get("winners_count", 0))

    # Base shares of the Độc Đắc pool.
    shares: dict[str, int] = {
        "Giải Nhất": dd_v // 3,
        "Giải Nhì": dd_v // 6,
        "Giải Ba": dd_v // 6,
        "Giải Tư": dd_v // 6,
        "Giải Năm": dd_v // 6,
    }

    # Redistribution: zero-winner tiers' shares go to the remaining tiers
    # (with w_sim > 0) in equal parts.
    zero_tiers = [t for t, ws in tier_w_sim.items() if ws == 0]
    non_zero_tiers = [t for t, ws in tier_w_sim.items() if ws > 0]
    for zt in zero_tiers:
        if non_zero_tiers:
            per_tier = shares[zt] // len(non_zero_tiers)
            for nzt in non_zero_tiers:
                shares[nzt] += per_tier
            shares[zt] = 0
        # If all five tiers are zero, the share is unclaimed.

    # Per-winner prize for our tier: (w_sim * standard + share) / w_sim.
    standard_pv = POWER_535_STANDARD_PV[prize_name]
    our_share = shares[prize_name]
    w_sim = tier_w_sim[prize_name]
    total_pool = w_sim * standard_pv + our_share
    return int(total_pool / w_sim)
