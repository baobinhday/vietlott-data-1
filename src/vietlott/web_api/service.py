"""Pure-Python service layer for the Vietlott Strategy Builder API.

No FastAPI imports — can be unit-tested without spinning up a server.
"""

from datetime import date, timedelta
from typing import Any

import pandas as pd
import pendulum
from loguru import logger

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
            prize: int = int(pipeline._prize_for(main_match, special_match))
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
