"""Pure-Python service layer for the Vietlott Strategy Builder API.

No FastAPI imports — can be unit-tested without spinning up a server.
"""

from datetime import date, timedelta
from typing import Any

import pandas as pd
import pendulum
from loguru import logger

from machine_learning.render_prediction_base import BasePowerPredictionSummaryGenerator
from machine_learning.strategies import (
    ColdNumbersStrategy,
    InverseHybridStrategy,
    InverseHybridTrioStrategy,
    SteinerStrategy,
)
from machine_learning.strategies.base import PredictModel
from machine_learning.strategies.pipeline import PipelineStrategy
from machine_learning.strategies.registry import list_strategies
from vietlott.config.products import get_config, product_config_map
from vietlott.web_api.data_loader import load_product_dataframe

# ---------------------------------------------------------------------------
# Ticket price per product (VND).  All Vietlott products are 10 000 VND/ticket.
# ---------------------------------------------------------------------------
_TICKET_PRICES: dict[str, int] = {
    "power_655": 10000,
    "power_645": 10000,
    "power_535": 10000,
    "keno": 10000,
    "3d": 10000,
    "3d_pro": 10000,
    "bingo18": 10000,
}


# TODO(v1): Replace base default prize tables with per-product prize_fn tables.
#   Power 6/55: 6=30B, 5+special=3B, 5=40M, 4=500K, 3=50K
#   Power 6/45: 6=~12B (variable), 5=... (similar structure, no special)
#   Power 5/35: 5+special=6B, 4+special=5M, 3+special=50K, 5=40M, 4=200K, 3=30K
def _lookup_ticket_price(product: str) -> int:
    """Return the per-ticket price in VND for *product*."""
    return _TICKET_PRICES.get(product, 10000)


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------


def _validate_date_range(date_from: date | None, date_to: date | None) -> None:
    """Raise ``ValueError`` if *date_from* > *date_to*."""
    if date_from is not None and date_to is not None and date_from > date_to:
        raise ValueError("date_from must not be after date_to")


def get_strategies_metadata() -> list[dict]:
    """Return strategy metadata list from the registry (JSON-safe)."""
    return list_strategies()


def get_product_info(name: str) -> dict:
    """Return product configuration as a flat dict.

    Raises ``ValueError`` if *name* is not registered.
    """
    config = get_config(name)
    return {
        "name": config.name,
        "min": config.min_value,
        "max": config.max_value,
        "size_output": config.size_output,
        "has_special": config.has_special,
        "special_min": config.special_min,
        "special_max": config.special_max,
        "special_count": config.special_count,
        "ticket_price": _lookup_ticket_price(name),
        "interval_days": config.interval.days if config.interval else None,
    }


def get_all_products() -> list[str]:
    """Return a list of all registered product names."""
    return sorted(product_config_map.keys())


def compute_next_draw_date(name: str, today: date | None = None) -> date:
    """Return the next scheduled draw date for *name* after *today*.

    If *today* is ``None``, uses the current UTC date.
    """
    if today is None:
        today = pendulum.now("UTC").date()
    config = get_config(name)
    df = load_product_dataframe(name)
    last_date: date = df["date"].max().date()  # type: ignore[union-attr]
    interval: timedelta = config.interval

    next_date = last_date + interval
    while next_date < today:
        next_date += interval

    return next_date


# ---------------------------------------------------------------------------
# Core operations
# ---------------------------------------------------------------------------


def _normalize_group_dict(g: dict) -> dict:
    """Normalise a single group dict (old or new format) to the new format.

    This is the dict-based counterpart of ``GroupSpec.normalized()`` for
    use when only plain dicts (e.g. from ``model_dump()``) are available.
    """
    from vietlott.web_api.schemas import GroupSpec

    return GroupSpec(**g).normalized()


def _build_pipeline_spec(
    pipeline_dict: dict,
    ticket_count: int | None = None,
) -> dict:
    """Normalise a pipeline spec dict so it is compatible with
    ``PipelineStrategy``.

    Converts Pydantic model dicts into the flat dict format expected by
    the engine, normalising each group through ``_normalize_group_dict``
    for backward compatibility with the old single-strategy format.
    """
    groups = [_normalize_group_dict(g) for g in pipeline_dict["groups"]]
    spec: dict[str, Any] = {
        "product": pipeline_dict["product"],
        "groups": groups,
        "combiner": pipeline_dict.get("combiner", {"method": "concatenate"}),
        "post_filters": pipeline_dict.get("post_filters", {}),
        "ticket_count": ticket_count if ticket_count is not None else pipeline_dict.get("ticket_count", 1),
    }
    return spec


def generate_tickets(
    pipeline_dict: dict,
    target_date: date | None = None,
) -> dict:
    """Generate tickets for a pipeline spec.

    Returns a dict matching ``GenerateResponse`` shape.
    """
    product: str = pipeline_dict["product"]
    df: pd.DataFrame = load_product_dataframe(product)

    spec = _build_pipeline_spec(pipeline_dict)
    ticket_count: int = spec["ticket_count"]

    # Resolve target date.
    if target_date is None:
        target_date = compute_next_draw_date(product)

    # Build pipeline and generate.
    pipeline = PipelineStrategy(df, spec)
    from vietlott.config.prizes import get_prize_fn

    pipeline.prize_fn = get_prize_fn(product)
    # Convert to pd.Timestamp for compatibility with datetime64[us] columns.
    ts_target = pd.Timestamp(target_date)
    tickets = pipeline.generate_tickets(ts_target, ticket_count=ticket_count)

    price = _lookup_ticket_price(product)
    total_cost = len(tickets) * price

    # Build a simple pool summary per group.
    pool_summary: list[dict] = []
    for g in spec["groups"]:
        first_step = g["strategies"][0] if g["strategies"] else {}
        pool_summary.append(
            {
                "name": g.get("name", "Group"),
                "strategy": first_step.get("strategy", ""),
                "picked_from_pool": first_step.get("pool_size", 0),
            }
        )

    return {
        "product": product,
        "target_date": target_date,
        "tickets": tickets,
        "total_cost_vnd": total_cost,
        "pool_summary": pool_summary,
    }


def run_backtest(
    pipeline_dict: dict,
    date_from: date | None = None,
    date_to: date | None = None,
    ticket_count: int | None = None,
) -> dict:
    """Run a full backtest for a pipeline spec.

    When ``ticket_count`` is ``None`` (default), the pipeline's own
    ``ticket_count`` is used.  Pass an explicit value to override.

    Returns a dict matching ``BacktestResponse`` shape.
    """
    _validate_date_range(date_from, date_to)
    product: str = pipeline_dict["product"]
    df: pd.DataFrame = load_product_dataframe(product)

    spec = _build_pipeline_spec(pipeline_dict)
    # Resolve ticket_count: explicit > pipeline > 1.
    if ticket_count is None:
        ticket_count = spec.get("ticket_count", 1)
    # Override the spec's ticket_count so PipelineStrategy uses it.
    spec["ticket_count"] = ticket_count

    pipeline = PipelineStrategy(df, spec)
    from vietlott.config.prizes import get_prize_fn

    pipeline.prize_fn = get_prize_fn(product)

    # Convert to pd.Timestamp for compatibility with datetime64[us] columns.
    bt_date_from = pd.Timestamp(date_from) if date_from is not None else None
    bt_date_to = pd.Timestamp(date_to) if date_to is not None else None
    pipeline.backtest(date_from=bt_date_from, date_to=bt_date_to)
    eval_result = pipeline.evaluate()
    cost, gain, profit = pipeline.revenue()

    # Determine date range actually used.
    bt_df = pipeline.df_backtest
    if bt_df is None or bt_df.empty:
        logger.warning("Backtest produced no results for product={}", product)
        return {
            "product": product,
            "date_from": date_from or date.today(),
            "date_to": date_to or date.today(),
            "draws": 0,
            "tickets_per_draw": ticket_count,
            "total_tickets": 0,
            "total_revenue_vnd": 0,
            "net_profit_vnd": 0,
            "roi": 0.0,
            "matches_distribution": {},
            "best_match": 0,
            "avg_match": 0.0,
            "per_draw": [],
        }

    actual_date_from: date = bt_df["date"].min().date()  # type: ignore[union-attr]
    actual_date_to: date = bt_df["date"].max().date()  # type: ignore[union-attr]
    num_draws: int = len(bt_df)

    # Build matches distribution and per-draw details.
    eval_df = pipeline.df_backtest_evaluate
    count_correct_num = eval_result.get("count_correct_num", pd.Series(dtype=int))
    matches_distribution: dict[int, int] = {int(k): int(v) for k, v in count_correct_num.items()}
    best_match: int = int(max(matches_distribution.keys())) if matches_distribution else 0

    # Average match: weighted average of main_match across all exploded rows.
    total_matches_raw = eval_df["main_match"].sum() if eval_df is not None else 0
    total_rows: int = len(eval_df) if eval_df is not None else 0
    total_matches: int = int(total_matches_raw)  # type: ignore[arg-type]
    avg_match: float = round(total_matches / total_rows, 4) if total_rows > 0 else 0.0

    # Build per_draw list.
    price_per_ticket = _lookup_ticket_price(product)
    per_draw: list[dict] = []
    cumulative_profit: int = 0

    for _, row in bt_df.iterrows():
        draw_date: date = row["date"].date()  # type: ignore[union-attr]
        actual: list[int] = [int(n) for n in row["result"]]  # type: ignore[arg-type]
        metadata_list: list[dict] = row.get("predict_metadata", [])
        if not isinstance(metadata_list, list):
            metadata_list = []

        # Aggregate over all predictions for this draw.
        all_tickets: list[list[int]] = []
        draw_cost: int = 0
        total_prize: int = 0
        best_main: int = -1
        best_prize: int = 0
        best_ticket: list[int] | None = None

        for md in metadata_list:
            draw_cost += price_per_ticket
            raw_main_match = md.get("main_match", 0)
            raw_special_match = md.get("special_match", 0)
            main_match: int = int(raw_main_match)
            special_match: int = int(raw_special_match)
            # Prefer the crawled per-draw prize (actual jackpot etc.),
            # fall back to the hardcoded baseline when missing.
            from vietlott.config.prizes import get_actual_prize_for_draw

            draw_id_raw = row.get("id") if hasattr(row, "get") else None
            prize: int = int(get_actual_prize_for_draw(product, draw_id_raw, main_match, special_match))
            total_prize += prize

            # Collect the predicted ticket (key is "predicted", not "predict").
            raw_ticket = md.get(PredictModel.col_predict)
            if raw_ticket:
                ticket_nums = [int(n) for n in raw_ticket]
                if ticket_nums not in all_tickets:
                    all_tickets.append(ticket_nums)

            # Track best match (with prize tiebreaker).
            # Start best_main at -1 so the very first entry always triggers.
            if main_match > best_main or (main_match == best_main and prize > best_prize):
                best_main = main_match
                best_prize = prize
                if raw_ticket:
                    best_ticket = [int(n) for n in raw_ticket]

        cumulative_profit += total_prize - draw_cost

        per_draw.append(
            {
                "date": str(draw_date),
                "ticket": best_ticket if best_ticket else [],
                "tickets": all_tickets if all_tickets else [],
                "actual": actual,
                "matches": int(best_main),
                "prize_vnd": int(total_prize),
                "cumulative_profit_vnd": int(cumulative_profit),
            }
        )

    # Ensure all values are native Python types for JSON serialisation.
    cost_native = int(cost)
    gain_native = int(gain)
    profit_native = int(profit)
    roi: float = round((profit_native / cost_native) * 100, 4) if cost_native > 0 else 0.0

    return {
        "product": product,
        "date_from": actual_date_from,
        "date_to": actual_date_to,
        "draws": int(num_draws),
        "tickets_per_draw": int(ticket_count),
        "total_tickets": int(num_draws) * int(ticket_count),
        "total_cost_vnd": cost_native,
        "total_revenue_vnd": gain_native,
        "net_profit_vnd": profit_native,
        "roi": float(roi),
        "matches_distribution": matches_distribution,
        "best_match": int(best_match),
        "avg_match": float(avg_match),
        "per_draw": per_draw,
    }


# ---------------------------------------------------------------------------
# POST /api/predict — next-draw prediction via the ML strategy machinery
# (Phase 1 of the web-adapter migration; TS spec: web/src/lib/predict.ts)
# ---------------------------------------------------------------------------

# Display names per product (spec: web/src/lib/config.ts PRODUCTS.*.display).
_PRODUCT_DISPLAY: dict[str, str] = {
    "power_535": "Power 5/35",
    "power_645": "Power 6/45",
    "power_655": "Power 6/55",
    "keno": "Keno",
    "3d": "Max 3D",
    "3d_pro": "Max 3D Pro",
    "bingo18": "Bingo 18",
}

TRIO_STRATEGY_LABEL: str = "Inverse Hybrid: Trio (Cold + PairFreq + Pattern)"

_DEFAULT_STRATEGY_LABEL: str = "Inverse Hybrid: Cold Numbers → Steiner"

# Default prediction config (spec: web/src/lib/backtest.ts::defaultBacktestConfig).
_DEFAULT_PREDICT_CONFIG: dict[str, Any] = {
    "strategy": None,
    "tpd": 2,
    "cold": {"lookback_days": 365, "selection_weight": 0.7},
    "steiner": {
        "lookback_days": 365,
        "filter_consecutive": True,
        "filter_same_decade": True,
        "t": 2,
        "k": 3,
        "v": None,
    },
    "inverse": {"top_k": 15},
    "specials": {"top_n": 4, "mode": "markov_steiner", "lookback_draws": 60, "offset_draws": 30},
    "dd_filter": {"enabled": True, "threshold": 15_000_000_000},
    "date_from": None,
    "date_to": None,
}


def _merge_request_config(config: dict | None) -> dict:
    """Shallow-merge a request config over the TS defaults.

    Mirrors the TS route handler's ``{...default, ...body.config}``.
    NOTE: sub-configs are merged per-key (deep-ish) rather than replaced
    wholesale — a superset of the TS spread semantics; partial
    sub-configs are accepted.
    """
    merged: dict[str, Any] = {**_DEFAULT_PREDICT_CONFIG}
    cfg_in: dict[str, Any] = dict(config or {})
    requested_strategy = cfg_in.pop("strategy", None) or merged["strategy"]
    for key, value in cfg_in.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = {**merged[key], **value}
        else:
            merged[key] = value
    merged["strategy"] = requested_strategy
    tpd = int(merged["tpd"])
    if tpd < 1:
        raise ValueError(f"tpd must be >= 1, got {tpd}")
    return merged


def _build_prediction_strategy(product: str, product_cfg: Any, df: pd.DataFrame, merged: dict):
    """Build + configure the strategy chain shared by predict & flat-backtest.

    Builds a Steiner picker plus either the Inverse-Hybrid (Cold →
    Steiner) or the Inverse-Hybrid Trio strategy per the request config
    (spec: ``web/src/lib/predict.ts``), applies the product config /
    prize table and hooks the frequency specials picker for products
    requiring an explicit special pick (Power 5/35).
    """
    tpd: int = int(merged["tpd"])
    steiner_conf = merged["steiner"]
    steiner = SteinerStrategy(
        df,
        time_predict=1,
        min_val=product_cfg.min_value,
        max_val=product_cfg.max_value,
        lookback_days=int(steiner_conf["lookback_days"]),
        filter_consecutive=bool(steiner_conf["filter_consecutive"]),
        filter_same_decade=bool(steiner_conf["filter_same_decade"]),
        t=int(steiner_conf["t"]),
        k=int(steiner_conf["k"]),
        v=steiner_conf["v"],
    )

    top_k_default: int = int(merged["inverse"]["top_k"])
    # Widen the proposer pool for no-special products (6/45, 6/55): the
    # tickets are the raw TPD predictions, so a larger pool gives the
    # pairwise-overlap diversity filter enough distinct candidates.
    top_k = top_k_default if product_cfg.special_pick_required else max(top_k_default, tpd * 2 + 4)

    strategy_label: str = merged["strategy"] or _DEFAULT_STRATEGY_LABEL
    if TRIO_STRATEGY_LABEL.lower() in strategy_label.lower():
        strategy = InverseHybridTrioStrategy(
            df,
            steiner=steiner,
            top_k=top_k,
            time_predict=tpd,
        )
    else:
        cold_conf = merged["cold"]
        proposer = ColdNumbersStrategy(
            df,
            time_predict=tpd,
            min_val=product_cfg.min_value,
            max_val=product_cfg.max_value,
            lookback_days=int(cold_conf["lookback_days"]),
            strategy_type="cold",
            selection_weight=float(cold_conf["selection_weight"]),
        )
        strategy = InverseHybridStrategy(
            proposer=proposer,
            steiner=steiner,
            top_k=top_k,
            coverage=tpd,
            time_predict=tpd,
        )

    from vietlott.config.prizes import get_prize_fn

    strategy.apply_product_config(product_cfg)
    strategy.prize_fn = get_prize_fn(product)

    # Frequency specials picker (only when the product requires an explicit
    # special pick — i.e. Power 5/35).  Reuses the render machinery's picker.
    if product_cfg.special_pick_required:
        specials_conf = merged["specials"]
        picker = BasePowerPredictionSummaryGenerator.__new__(BasePowerPredictionSummaryGenerator)
        picker._apply_frequency_specials(
            strategy,
            top_n=int(specials_conf["top_n"]),
            lookback_draws=int(specials_conf["lookback_draws"]),
            offset_draws=int(specials_conf["offset_draws"]),
            mode=str(specials_conf["mode"]),
        )
    return strategy


def _overlap_diverse_tickets(strategy: Any, ts_target: pd.Timestamp, count: int, size_output: int) -> list[list[int]]:
    """Select ``size_output``-number tickets with bounded pairwise overlap.

    Greedy filter: a candidate is kept only when it shares at most
    ``size_output - 2`` numbers with every already-kept ticket (for 6-number
    products that rejects tickets sharing 5 or more numbers). On failure to
    fill the count, up to ``max(20, count * 5)`` resample attempts are made;
    if the pool is still too small the threshold relaxes once to
    ``size_output - 1``, then strict set-distinctness, and finally any
    distinct ticket. Always returns exactly ``count`` tickets.
    """
    kept: list[list[int]] = []
    kept_sets: list[set[int]] = []
    seen: set[frozenset[int]] = set()

    def accepts(cand_set: set[int], max_overlap: int) -> bool:
        return all(len(cand_set & s) <= max_overlap for s in kept_sets)

    max_resamples: int = max(20, count * 5)
    for max_overlap in (size_output - 2, size_output - 1):
        attempts: int = 0
        while len(kept) < count:
            if attempts >= max_resamples and kept:
                break
            cand: list[int] = [int(n) for n in strategy.predict(ts_target)]
            cand_set: set[int] = set(cand)
            attempts += 1
            if len(cand_set) < size_output or cand in kept or frozenset(cand_set) in seen:
                if len(kept) < count:
                    continue
                break
            if len(kept) >= count:
                break
            if accepts(cand_set, max_overlap):
                kept.append(cand)
                kept_sets.append(cand_set)
                seen.add(frozenset(cand_set))
        if len(kept) >= count:
            break

    # Final fallback — accept any strict-distinct (as a set) ticket.
    fallback_attempts: int = 0
    while len(kept) < count and fallback_attempts < max_resamples:
        fallback_attempts += 1
        cand = [int(n) for n in strategy.predict(ts_target)]
        cand_set = set(cand)
        key = frozenset(cand_set)
        if len(cand_set) < size_output or (key in seen and len(kept) > 0):
            continue
        kept.append(cand)
        kept_sets.append(cand_set)
        seen.add(key)
    # Degenerate pool (strategy keeps echoing one ticket): pad with clones so
    # the ``count`` contract holds.
    while len(kept) < count:
        logger.warning(
            "predict_tickets: diversity pool exhausted for {}-number tickets; padding with a clone", size_output
        )
        kept.append(list(kept[-1]))
    return kept[:count]


def predict_tickets(product: str, config: dict | None = None, target_date: date | None = None) -> dict:
    """Generate next-draw prediction tickets with the ML strategy machinery.

    Mirrors ``web/src/lib/predict.ts::generatePrediction``: builds a
    Steiner picker plus either the Inverse-Hybrid (Cold → Steiner) or the
    Inverse-Hybrid Trio strategy, applies frequency-based specials for
    products with an explicit special pick (Power 5/35), then emits
    ``tpd × top_n_specials`` tickets for the target draw.

    Data strictly before ``target_date`` is used by the strategies (their
    lookback masks are ``date < target_date``); when ``target_date`` is
    ``None`` the next scheduled draw date is computed via
    :func:`compute_next_draw_date`.

    Returns a dict matching ``PredictResponse`` (snake_case keys).

    Raises
    ------
    ValueError
        Unknown product or invalid strategy configuration.
    FileNotFoundError
        If the product's NDJSON data file is missing.
    """
    product_cfg = get_config(product)
    df_full: pd.DataFrame = load_product_dataframe(product)

    merged: dict[str, Any] = _merge_request_config(config)
    tpd: int = int(merged["tpd"])

    # Resolve target date and restrict strategies to data strictly BEFORE it.
    if target_date is None:
        target_date = compute_next_draw_date(product)
    ts_target = pd.Timestamp(target_date)
    df = df_full[df_full["date"] < ts_target].reset_index(drop=True)
    if df.empty:
        raise ValueError(f"No historical data strictly before target_date={target_date}")

    # Build the strategy chain (spec: web/src/lib/predict.ts).
    strategy = _build_prediction_strategy(product, product_cfg, df, merged)
    # TPD main predictions. For no-special products (6/45, 6/55) the mains
    # are the tickets themselves, so apply a pairwise-overlap diversity
    # filter to avoid near-duplicate tickets.
    if product_cfg.special_pick_required:
        main_tickets: list[list[int]] = [strategy.predict(ts_target) for _ in range(tpd)]
    else:
        main_tickets = _overlap_diverse_tickets(strategy, ts_target, count=tpd, size_output=product_cfg.size_output)
    # Specials — wheel generated for the next draw (empty for no-special
    # products such as Power 6/45).
    specials: list[int | None] = (
        [int(s) for s in strategy.predict_special(ts_target)] if product_cfg.special_pick_required else []
    )

    # Cartesian product: every (main, special) combination becomes a ticket.
    special_list: list[int | None] = specials if specials else [None]
    tickets: list[dict] = []
    coverage = 1
    for main in main_tickets:
        for special in special_list:
            tickets.append(
                {
                    "predicted": [int(n) for n in main],
                    "predicted_special": special,
                    "coverage": coverage,
                }
            )
            coverage += 1

    # Most recent draw strictly before target (TS: draws[0], newest-first).
    previous_draw: dict | None = None
    last = df.iloc[-1]
    previous_draw = {
        "date": str(pd.Timestamp(last["date"]).date()),
        "id": str(last["id"]),
        "result": [int(n) for n in last["result"]],
    }

    return {
        "product": product,
        "product_display": _PRODUCT_DISPLAY.get(product, product),
        "strategy": merged["strategy"] or _DEFAULT_STRATEGY_LABEL,
        "config": merged,
        "previous_draw": previous_draw,
        "tickets": tickets,
        "generated_at": pendulum.now("UTC").isoformat(),
    }


# ---------------------------------------------------------------------------
# POST /api/ev — expected-value estimation (spec: web/src/lib/ev.ts)
# ---------------------------------------------------------------------------

POWER_535_JACKPOT_BASE: int = 6_000_000_000
POWER_535_SPLIT_THRESHOLD: int = 12_000_000_000
POWER_535_SHARE_JACKPOT: float = 0.55
POWER_535_NUM_SPECIALS: int = 12
POWER_535_NUM_MAINS: int = 35
POWER_535_NUM_PICKS: int = 5
_POWER_535_C5: int = 324_632  # C(35, 5)
_POWER_535_TOTAL_TICKETS: int = _POWER_535_C5 * POWER_535_NUM_SPECIALS  # 3,895,584

POWER_535_TIER_PROBS: dict[str, float] = {
    "jackpot": 1 / _POWER_535_TOTAL_TICKETS,
    "nhat": 11 / _POWER_535_TOTAL_TICKETS,
    "nhi": (5 * 30) / _POWER_535_TOTAL_TICKETS,
    "ba": (5 * 30 * 11) / _POWER_535_TOTAL_TICKETS,
    "tu": (10 * 435) / _POWER_535_TOTAL_TICKETS,
    "nam": (10 * 435 * 11) / _POWER_535_TOTAL_TICKETS,
    "khuyen_khich": ((10 * 4_060 + 5 * 27_405) * 1) / _POWER_535_TOTAL_TICKETS,
}

# Standard (non-split) per-winner amounts.  Nhất→Năm reuse the
# ``POWER_535_STANDARD_PV`` table from vietlott.config.prizes.
POWER_535_FIXED_TIERS: dict[str, int] = {
    "nhat": 10_000_000,
    "nhi": 5_000_000,
    "ba": 500_000,
    "tu": 100_000,
    "nam": 30_000,
    "khuyen_khich": 10_000,
}

_TIER_DISPLAY: dict[str, str] = {
    "nhat": "Giải Nhất",
    "nhi": "Giải Nhì",
    "ba": "Giải Ba",
    "tu": "Giải Tư",
    "nam": "Giải Năm",
    "khuyen_khich": "Giải Khuyến Khích",
}

_DD_NAME = "Giải Độc Đắc"
_ZERO_WINNERS: dict[str, float] = {
    "jackpot": 0.0,
    "nhat": 0.0,
    "nhi": 0.0,
    "ba": 0.0,
    "tu": 0.0,
    "nam": 0.0,
    "khuyen_khich": 0.0,
}


def _split_payout_for_tier(tier: str, jackpot_next: int, expected_other_winners: float) -> float:
    """Expected payout of one lower-tier win under the 5/35 split rule.

    ``payout = standardPv + (1/6 × J) / (E[w] + 1)`` with a ``1/3 × J``
    bonus for Giải Nhất.  See ``web/src/lib/ev.ts::splitPayoutForTier``.
    """
    standard_pv = POWER_535_FIXED_TIERS[tier]
    tier_share = jackpot_next / 6
    w_sim = expected_other_winners + 1
    base_bonus = jackpot_next / 3 if tier == "nhat" else 0.0
    return standard_pv + (tier_share + base_bonus) / w_sim


def _estimate_draw_revenue(
    tiers: dict[str, dict[str, int]],
    prev_tiers: dict[str, dict[str, int]] | None,
    jackpot_base: int,
) -> dict[str, int | bool | float]:
    """Back-calc jackpot / revenue / tickets for one observed draw."""
    dd = tiers.get(_DD_NAME)
    jackpot_value = dd["prize_value"] if dd else 0
    jackpot_winners = dd["winners_count"] if dd else 0
    has_jackpot_winner = jackpot_winners > 0

    carryover = jackpot_base
    if not has_jackpot_winner and prev_tiers is not None:
        prev_dd = prev_tiers.get(_DD_NAME)
        carryover = prev_dd["prize_value"] if prev_dd else jackpot_base

    fresh_contribution = max(0, jackpot_value - carryover)
    revenue = fresh_contribution / POWER_535_SHARE_JACKPOT
    tickets = max(0, revenue / 10_000)
    return {
        "jackpot_value": int(jackpot_value),
        "jackpot_winners": int(jackpot_winners),
        "has_jackpot_winner": has_jackpot_winner,
        "carryover": int(carryover),
        "fresh_contribution": int(fresh_contribution),
        "revenue": int(revenue),
        "tickets": tickets,
    }


def _mean_winners(recent: list[dict[str, dict[str, dict[str, int]]]]) -> dict[str, float]:
    """Mean winners per tier across the recent draws (new-first slice)."""
    if not recent:
        return dict(_ZERO_WINNERS)
    totals = dict(_ZERO_WINNERS)
    tier_names = {"jackpot": _DD_NAME, **_TIER_DISPLAY}
    for tiers in recent:
        for key, prize_name in tier_names.items():
            info = tiers.get(prize_name)
            totals[key] += info["winners_count"] if info else 0
    n = len(recent)
    return {k: v / n for k, v in totals.items()}


def _project_next_draw(recent: list[dict], jackpot_base: int, n: int = 10) -> dict:
    """Project the next draw's Jackpot / revenue / tickets (ev.ts::projectNextDraw)."""
    slice_ = recent[:n]
    if not slice_:
        return {
            "expected_next_jackpot": jackpot_base,
            "expected_revenue": 0,
            "expected_tickets": 0,
            "avg_tickets_last_n": 0,
            "sample_size": 0,
            "confidence": "low",
            "avg_jackpot_winners_last_n": 0.0,
            "expected_winners": dict(_ZERO_WINNERS),
            "split_mode": False,
        }

    estimates = [
        _estimate_draw_revenue(
            slice_[i]["tiers"], slice_[i + 1]["tiers"] if i + 1 < len(slice_) else None, jackpot_base
        )
        for i in range(len(slice_))
    ]
    avg_tickets = sum(e["tickets"] for e in estimates) / len(estimates)
    avg_revenue = sum(e["revenue"] for e in estimates) / len(estimates)
    avg_jackpot_winners = sum(e["jackpot_winners"] for e in estimates) / len(estimates)
    expected_winners = _mean_winners([d["tiers"] for d in slice_])

    last = slice_[0]
    last_dd = last["tiers"].get(_DD_NAME)
    last_j = last_dd["prize_value"] if last_dd else jackpot_base
    last_has_winner = (last_dd["winners_count"] if last_dd else 0) > 0
    base_for_next = jackpot_base if last_has_winner else last_j
    expected_next_jackpot = base_for_next + POWER_535_SHARE_JACKPOT * avg_revenue

    split_mode = expected_next_jackpot > POWER_535_SPLIT_THRESHOLD and avg_jackpot_winners < 0.5
    confidence = "high" if len(slice_) >= 8 and avg_revenue > 0 else ("medium" if len(slice_) >= 3 else "low")

    return {
        "expected_next_jackpot": int(round(expected_next_jackpot)),
        "expected_revenue": int(round(avg_revenue)),
        "expected_tickets": int(round(avg_tickets)),
        "avg_tickets_last_n": int(round(avg_tickets)),
        "sample_size": len(slice_),
        "confidence": confidence,
        "avg_jackpot_winners_last_n": round(avg_jackpot_winners, 2),
        "expected_winners": expected_winners,
        "split_mode": bool(split_mode),
    }


def compute_ev(
    product: str,
    num_tickets: int = 8,
    jackpot_base: int | None = None,
    history_limit: int = 10,
    history_end_id: str | None = None,
    tier_mode: str = "fixed",
) -> dict:
    """Compute per-ticket EV from crawled prize data (spec: ``web/src/lib/ev.ts``).

    Reads ``data/<product>_prizes.jsonl`` through the existing prize
    loaders and computes ``EV = Σ P(tier) × E[payout] − ticket_price``
    for Power 5/35 combinatorics, plus the next-draw Jackpot projection
    and split-mode detection.

    Returns a dict matching ``EvResponse`` (snake_case keys).

    Raises
    ------
    ValueError
        Unknown product, ``history_end_id`` not found, or fewer than 2
        usable draws with prize data.
    """
    from vietlott.config.prizes import _load_prizes_index

    if jackpot_base is None:
        jackpot_base = POWER_535_JACKPOT_BASE
    num_tickets = max(1, min(200, int(num_tickets)))
    history_limit = max(2, min(50, int(history_limit)))
    tier_mode = "historical_mean" if tier_mode == "historical_mean" else "fixed"

    df = load_product_dataframe(product)
    prize_index = _load_prizes_index(product)

    # Attach prizes by draw id, newest-first.
    rows: list[dict] = []
    for _, row in df.iterrows():
        draw_id = str(row["id"])
        tiers = prize_index.get(draw_id)
        if not tiers:
            continue
        rows.append({"id": draw_id, "date": pd.Timestamp(row["date"]), "tiers": tiers})
    rows.sort(key=lambda r: r["date"], reverse=True)

    if history_end_id is not None:
        idx = next((i for i, r in enumerate(rows) if r["id"] == history_end_id), None)
        if idx is None:
            raise ValueError(f"history_end_id={history_end_id} not found")
        rows = rows[idx : idx + history_limit]
    else:
        rows = rows[:history_limit]

    if len(rows) < 2:
        raise ValueError(f"Cần ít nhất 2 kỳ có dữ liệu giải để ước lượng EV. Hiện có {len(rows)} kỳ.")

    projection = _project_next_draw(rows, jackpot_base, 10)
    expected_next_jackpot = projection["expected_next_jackpot"]
    expected_winners = projection["expected_winners"]
    split_mode = projection["split_mode"]
    jack_w = expected_winners["jackpot"]

    mean_payouts: dict[str, float] = {}
    if tier_mode == "historical_mean":
        for key in POWER_535_FIXED_TIERS:
            tier_name = _TIER_DISPLAY[key]
            total = sum(r["tiers"].get(tier_name, {"prize_value": 0})["prize_value"] for r in rows)
            mean_payouts[key] = total / len(rows) if rows else 0.0

    # Jackpot tier: add 1 hypothetical winner to get our share.
    jackpot_payout = expected_next_jackpot / max(1, jack_w + 1)

    lower_tiers = ["nhat", "nhi", "ba", "tu", "nam"]
    lower_payouts: dict[str, dict] = {}
    for key in lower_tiers:
        w = expected_winners[key]
        if split_mode:
            lower_payouts[key] = {
                "payout": _split_payout_for_tier(key, expected_next_jackpot, w),
                "split_adjusted": True,
                "w": w,
            }
        elif tier_mode == "historical_mean":
            lower_payouts[key] = {"payout": mean_payouts.get(key, 0.0), "split_adjusted": False, "w": w}
        else:
            lower_payouts[key] = {"payout": float(POWER_535_FIXED_TIERS[key]), "split_adjusted": False, "w": w}

    tier_rows = [
        ("jackpot", "Giải Độc Đắc", jackpot_payout, POWER_535_TIER_PROBS["jackpot"], False, jack_w),
    ]
    for key in lower_tiers:
        info = lower_payouts[key]
        tier_rows.append(
            (key, _TIER_DISPLAY[key], info["payout"], POWER_535_TIER_PROBS[key], info["split_adjusted"], info["w"])
        )
    tier_rows.append(
        (
            "khuyen_khich",
            "Giải Khuyến Khích",
            float(POWER_535_FIXED_TIERS["khuyen_khich"]),
            POWER_535_TIER_PROBS["khuyen_khich"],
            False,
            expected_winners["khuyen_khich"],
        )
    )

    breakdown = [
        {
            "tier": key,
            "display_name": display,
            "probability": p,
            "expected_payout": int(round(payout)),
            "ev": p * payout,
            "split_adjusted": split_adj,
            "expected_other_winners": round(w, 2),
        }
        for key, display, payout, p, split_adj, w in tier_rows
    ]

    ev_per_ticket = sum(b["ev"] for b in breakdown) - 10_000
    total_ev = ev_per_ticket * num_tickets

    return {
        "product": product,
        "display": _PRODUCT_DISPLAY.get(product, product),
        "ticket_price": _lookup_ticket_price(product),
        "jackpot_base": int(jackpot_base),
        "history_sample_size": len(rows),
        "history_end_id": rows[0]["id"] if rows else None,
        "tier_mode": tier_mode,
        "ev_per_ticket": ev_per_ticket,
        "total_ev": total_ev,
        "num_tickets": num_tickets,
        "breakdown": breakdown,
        "projection": projection,
    }


# ---------------------------------------------------------------------------
# GET /api/draws — raw draw (and optional prize) history
# (Phase 2 of the web-adapter migration; TS spec: web/src/lib/data.ts)
# ---------------------------------------------------------------------------


def _result_to_draw_shapes(result: Any) -> list[int] | dict[str, Any]:
    """Normalize a draw's raw ``result`` into a JSON-safe draw shape.

    Power-family draws use a plain int list; other products (e.g. Vietlott
    3D) store ``{prize_name: [codes]}`` dicts — those are kept verbatim so
    `/api/draws` never crashes on them; the Power-family UI never renders
    them.
    """
    if isinstance(result, (list, tuple)):
        try:
            return [int(n) for n in result]
        except (TypeError, ValueError):
            return list(result)
    return result


def get_draws(product: str, limit: int = 20, include_prizes: bool = False) -> dict:
    """Return the draw history for *product*, newest-first.

    Mirrors the TS route handler (``web/src/app/api/draws/route.ts``):
    reads the product NDJSON, sorts newest-first (date desc, then id
    desc), applies ``limit`` (1..200) and optionally attaches the prize
    tiers per draw from ``data/<product>_prizes.jsonl``.

    Returns a dict matching ``DrawsResponse`` (camelCase on output).

    Raises
    ------
    ValueError
        Unknown product.
    FileNotFoundError
        If the product's NDJSON data file is missing.
    """
    product_cfg = get_config(product)
    limit = max(1, min(200, int(limit)))

    df: pd.DataFrame = load_product_dataframe(product)
    # Skip rows whose ``result`` is a prize-tier dict rather than a plain
    # number list — some products (3d, 3d_pro) store ``{prize: [codes]}``
    # instead of a list.  polars→pandas may hand us numpy arrays here (not
    # list/tuple), so test on "not dict / not str" rather than isinstance(list).
    usable = df[[not isinstance(r, (dict, str)) for r in df["result"]]]
    total: int = len(usable)
    # Newest first: date desc, then id desc (matches web/src/lib/data.ts).
    usable = usable.sort_values(by=["date", "id"], ascending=[False, False], kind="stable").head(limit)

    prize_index: dict[str, dict[str, dict[str, int]]] | None = None
    if include_prizes:
        from vietlott.config.prizes import _load_prizes_index

        prize_index = _load_prizes_index(product)

    draws: list[dict] = []
    for _, row in usable.iterrows():
        draw: dict[str, Any] = {
            "date": pd.Timestamp(row["date"]).date().isoformat(),
            "id": str(row["id"]),
            "result": _result_to_draw_shapes(row["result"]),
        }
        pt = row.get("process_time")
        if pt is not None and pd.notna(pt):
            draw["process_time"] = str(pt)
        if prize_index is not None:
            tiers = prize_index.get(draw["id"])
            draw["prizes"] = _prize_tiers_from_index(tiers) if tiers else None
        draws.append(draw)

    return {
        "product": product,
        "display": _PRODUCT_DISPLAY.get(product, product),
        "total": int(total),
        "draws": draws,
    }


def _prize_tiers_from_index(tiers: dict[str, dict[str, int]]) -> list[dict]:
    """Convert the normalized prize index entry into the raw tier-array shape.

    Output rows are ``{prize_name, prize_value, winners_count}`` with
    integer values — the FE parser accepts both the original string
    form and numeric form.
    """
    return [
        {"prize_name": name, "prize_value": info["prize_value"], "winners_count": info["winners_count"]}
        for name, info in tiers.items()
    ]


# ---------------------------------------------------------------------------
# POST /api/backtest/strategy — flat backtest over the UI flat config
# (Phase 2; TS spec: web/src/lib/backtest.ts runStrategyBacktest)
# ---------------------------------------------------------------------------

BEST_THRESHOLD: int = 3


def run_strategy_backtest(product: str, config: dict | None = None) -> dict:
    """Backtest the flat UI config (Inverse-Hybrid chain) draw by draw.

    Mirrors ``web/src/lib/backtest.ts::runStrategyBacktest``: builds the
    same strategy chain as :func:`predict_tickets`, restricts work to
    ``date_from``/``date_to`` and (for Power 5/35) to draws whose
    Độc Đắc jackpot exceeds ``ddFilter.threshold``, scores every
    (predicted, special) wheel combination against each draw using the
    crawled prize data, and aggregates into the ``BacktestSummary``
    shape the UI consumes.

    Returns a dict matching ``StrategyBacktestResponse`` (snake_case keys).

    Raises
    ------
    ValueError / FileNotFoundError
        Unknown product, invalid config or missing data file.
    """
    from vietlott.config.prizes import _load_prizes_index, get_actual_prize_for_draw, get_prize_fn

    product_cfg = get_config(product)
    df: pd.DataFrame = load_product_dataframe(product)

    merged = _merge_request_config(config)
    tpd: int = int(merged["tpd"])

    strategy = _build_prediction_strategy(product, product_cfg, df, merged)

    # Date-range filter (spec: TS ``config.dateFrom / config.dateTo``).
    working = df
    date_from = merged.get("date_from")
    date_to = merged.get("date_to")
    if date_from:
        working = working[working["date"] >= pd.Timestamp(date_from)]
    if date_to:
        working = working[working["date"] <= pd.Timestamp(date_to)]

    # Độc Đắc filter: draws whose jackpot > threshold (5/35 only).
    prize_index = _load_prizes_index(product)
    eligible_ids: set[str] | None = None
    dd_conf = merged["dd_filter"]
    if bool(dd_conf["enabled"]) and product == "power_535":
        eligible_ids = {
            draw_id
            for draw_id, tiers in prize_index.items()
            if tiers.get(_DD_NAME, {"prize_value": 0})["prize_value"] > int(dd_conf["threshold"])
        }
        if eligible_ids:
            working = working[[str(did) in eligible_ids for did in working["id"]]]

    price = _lookup_ticket_price(product)
    rows: list[dict] = []
    total_cost = 0
    total_gain = 0

    for _, row in working.iterrows():
        ts = pd.Timestamp(row["date"])
        result_actual = [int(n) for n in row["result"]]
        draw_id = str(row["id"])
        for i in range(tpd):
            predicted = strategy.predict(ts)
            specials = strategy.predict_special(ts)
            special_list: list[int | None] = [int(s) for s in specials] if specials else [None]
            for si, sp in enumerate(special_list):
                main_match, special_match = PredictModel._compare_list(
                    predicted,
                    sp,
                    result_actual,
                    has_special=product_cfg.has_special,
                    special_position=product_cfg.special_position,
                    special_pick_required=product_cfg.special_pick_required,
                    main_count=product_cfg.size_output,
                )
                is_correct = main_match == product_cfg.size_output
                if product == "power_535":
                    # Crawled per-draw prize data (incl. split rule) wins.
                    gain = get_actual_prize_for_draw(product, draw_id, int(main_match), int(special_match))
                else:
                    gain = int(strategy._prize_for(int(main_match), int(special_match)))
                rows.append(
                    {
                        "date": ts.date().isoformat(),
                        "draw_id": draw_id,
                        "predicted": [int(n) for n in predicted],
                        "predicted_special": sp,
                        "result": result_actual,
                        "main_match": int(main_match),
                        "special_match": int(special_match),
                        "gain": int(gain),
                        "is_correct": bool(is_correct),
                        "predict_idx": i,
                        "special_idx": si,
                    }
                )
                total_cost += price
                total_gain += int(gain)

    match_distribution: dict[int, int] = {}
    special_hits = 0
    for r in rows:
        match_distribution[r["main_match"]] = match_distribution.get(r["main_match"], 0) + 1
        if r["special_match"] > 0:
            special_hits += 1

    draw_set = {r["draw_id"] for r in rows}
    total_draws = len(draw_set)
    total_predictions = len(rows)
    net_profit = total_gain - total_cost
    roi = (net_profit / total_cost) * 100 if total_cost > 0 else 0.0

    best_results = sorted(
        (r for r in rows if r["main_match"] >= BEST_THRESHOLD),
        key=lambda r: (-r["main_match"], -r["special_match"], r["date"]),
    )

    # Yearly breakdown (spec: TS ``yearlyBreakdown``).
    by_year: dict[int, dict] = {}
    for r in rows:
        year = int(r["date"][:4])
        yb = by_year.setdefault(year, {"draws": set(), "predictions": 0, "gain": 0})
        yb["draws"].add(r["draw_id"])
        yb["predictions"] += 1
        yb["gain"] += r["gain"]
    yearly = []
    for year in sorted(by_year):
        v = by_year[year]
        cost = v["predictions"] * price
        profit = v["gain"] - cost
        yearly.append(
            {
                "year": year,
                "draws": len(v["draws"]),
                "predictions": v["predictions"],
                "cost": cost,
                "gain": v["gain"],
                "profit": profit,
                "roi": (profit / cost) * 100 if cost > 0 else 0.0,
            }
        )

    prize_fn = get_prize_fn(product)  # kept for parity with TS imports
    assert prize_fn is not None
    return {
        "total_cost": total_cost,
        "total_gain": total_gain,
        "net_profit": net_profit,
        "roi": roi,
        "total_draws": total_draws,
        "total_predictions": total_predictions,
        "match_distribution": match_distribution,
        "special_hits": special_hits,
        "best_threshold": BEST_THRESHOLD,
        "eligible_draws": len(draw_set) if eligible_ids else total_draws,
        "best_results": best_results,
        "yearly_breakdown": yearly,
        "all_rows": rows,
    }
