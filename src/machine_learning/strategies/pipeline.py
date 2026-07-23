"""
Pipeline prediction strategy.

Combines multiple sub-strategies in a configurable pipeline: each *group*
contains an ordered *chain* of strategies that progressively filter a
candidate pool.  The final pool of each group contributes ``pick_count``
numbers to the ticket.

Chain semantics
===============
- The first strategy step calls ``propose_top_numbers(target_date, pool_size)``
  to build the initial candidate pool.
- Each subsequent step calls ``predict(target_date, candidate_pool=list(pool))``
  and the result is intersected with the current pool (keeping only numbers
  that survive the step).
- **Pool-size control at every step**: when a step has ``pool_size`` set
  (int ≥ 1), the filtered pool is capped or topped-up to exactly that many
  numbers.  When ``pool_size`` is absent / ``None``, the strategy's natural
  output size is used ("auto" mode).
- The final pool is randomly sampled down to ``pick_count`` numbers.

Backward compatibility
======================
A group may be specified in the *old* single-strategy format:

  ``{"strategy": "steiner", "params": {...}, "pool_size": 15, "pick_count": 5}``

This is converted to the unified new format internally:

  ``{"strategies": [{"strategy": "steiner", "params": {...}, "pool_size": 15}], "pick_count": 5}``
"""

import random
from copy import deepcopy
from datetime import date
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
from loguru import logger

from machine_learning.strategies.base import PredictModel
from machine_learning.strategies.registry import get_strategy_class, instantiate
from vietlott.config.products import get_config

_MAX_RETRIES = 50


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _normalize_group(group: dict) -> dict:
    """Accept old (``strategy`` + ``params`` + ``pool_size``) or new
    (``strategies`` list) format and return the new format.

    The returned dict has ``name``, ``strategies`` (list of step dicts),
    and ``pick_count`` keys.
    """
    has_new = "strategies" in group and group["strategies"] is not None
    has_old = "strategy" in group and group["strategy"] is not None

    if has_new:
        # Already in new format — ensure each step carries needed keys.
        steps = []
        for s in group["strategies"]:
            step = dict(s)
            step.setdefault("params", {})
            steps.append(step)
        return {
            "name": group.get("name", "Group"),
            "strategies": steps,
            "pick_count": group.get("pick_count", 1),
        }

    if has_old:
        # Convert old single-strategy format.
        step: dict[str, Any] = {
            "strategy": group["strategy"],
            "params": group.get("params", {}),
        }
        if "pool_size" in group:
            step["pool_size"] = group["pool_size"]
        return {
            "name": group.get("name", "Group"),
            "strategies": [step],
            "pick_count": group.get("pick_count", 1),
        }

    raise ValueError(
        f"Group '{group.get('name', 'unnamed')}' must have either 'strategies' (new format) or 'strategy' (old format)"
    )


def _validate_spec(spec: Any) -> None:
    """Validate the pipeline spec dict structure, raising ``ValueError`` on
    invalid input.  Accepts both old and new group formats."""
    if not isinstance(spec, dict):
        raise ValueError("Pipeline spec must be a dict")
    if "groups" not in spec:
        raise ValueError("Pipeline spec must contain a 'groups' key")
    groups = spec["groups"]
    if not isinstance(groups, list) or len(groups) == 0:
        raise ValueError("Pipeline spec 'groups' must be a non-empty list")

    for i, g in enumerate(groups):
        if not isinstance(g, dict):
            raise ValueError(f"Group {i} must be a dict")

        has_new = "strategies" in g and g["strategies"] is not None
        has_old = "strategy" in g and g["strategy"] is not None

        strategies: List[dict] = []

        if has_new:
            strategies = g["strategies"]
            if not isinstance(strategies, list) or len(strategies) == 0:
                raise ValueError(f"Group {i}: 'strategies' must be a non-empty list")
        elif has_old:
            strategies = [g]
        else:
            raise ValueError(f"Group {i} must have either 'strategies' or 'strategy'")

        for j, step in enumerate(strategies):
            if not isinstance(step, dict) or "strategy" not in step:
                raise ValueError(f"Group {i}, strategy step {j} must have a 'strategy' key")
            try:
                get_strategy_class(step["strategy"])
            except ValueError:
                raise ValueError(f"Group {i}, step {j}: unknown strategy '{step['strategy']}'")
            # Validate pool_size if present (must be int ≥ 1 or None).
            step_ps = step.get("pool_size")
            if step_ps is not None:
                if not isinstance(step_ps, int) or step_ps < 1:
                    raise ValueError(
                        f"Group {i}, step {j}: 'pool_size' must be a positive integer or null, got {step_ps!r}"
                    )

        if "pick_count" not in g:
            raise ValueError(f"Group {i} must contain a 'pick_count' key")
        pick_count = g["pick_count"]
        if not isinstance(pick_count, int) or pick_count < 1:
            raise ValueError(f"Group {i}: 'pick_count' must be a positive integer")

    # Validate post_filters structure if present.
    pf = spec.get("post_filters")
    if pf is not None and not isinstance(pf, dict):
        raise ValueError("Pipeline spec 'post_filters' must be a dict or null")


# ------------------------------------------------------------------
# PipelineStrategy
# ------------------------------------------------------------------


class PipelineStrategy(PredictModel):
    """
    A configurable pipeline strategy that combines multiple sub-strategies
    in chains.

    The pipeline spec defines:

    * **groups** — a list of strategy groups.  Each group carries a
      ``strategies`` list (ordered chain) and a ``pick_count`` (how many
      numbers from the final filtered pool contribute to the ticket).
    * **combiner** — how group picks are assembled (currently only
      ``"concatenate"``).
    * **post_filters** — optional constraints on the final ticket (sum,
      even/odd count bounds).
    * **ticket_count** — how many distinct tickets ``generate_tickets``
      produces per call.

    Parameters
    ----------
    df:
        Historical lottery draw data.
    spec:
        Pipeline specification dictionary (see class docstring for shape).
    time_predict:
        Number of ticket batches per draw during backtest (maps to
        ``ticket_count`` in the pipeline context).
    min_val, max_val:
        Inclusive number range.  Inferred from ``spec["product"]`` when
        not provided explicitly.
    """

    def __init__(
        self,
        df: pd.DataFrame,
        spec: dict,
        time_predict: int = 1,
        min_val: Optional[int] = None,
        max_val: Optional[int] = None,
    ):
        _validate_spec(spec)

        # Normalise groups (old format → new format).
        normalised = deepcopy(spec)
        normalised["groups"] = [_normalize_group(g) for g in spec["groups"]]
        spec = normalised

        # Determine range from product config or explicit args.
        product_name = spec.get("product")
        config = None
        if product_name:
            config = get_config(product_name)
            if min_val is None:
                min_val = config.min_value
            if max_val is None:
                max_val = config.max_value
        if min_val is None:
            min_val = PredictModel.POWER_655_MIN_VAL
        if max_val is None:
            max_val = PredictModel.POWER_655_MAX_VAL

        super().__init__(df, time_predict, min_val, max_val)

        if config is not None:
            self.apply_product_config(config)

        self.spec: dict = spec
        self.groups: List[dict] = spec["groups"]
        self.combiner: dict = spec.get("combiner", {"method": "concatenate"})
        self.post_filters: dict = spec.get("post_filters", {})
        self.ticket_count: int = spec.get("ticket_count", 1)

        # Validate group pick counts.
        total_picks = sum(g["pick_count"] for g in self.groups)
        if total_picks != self.number_predict:
            raise ValueError(
                f"Sum of group pick_counts ({total_picks}) must equal number_predict ({self.number_predict})"
            )

        # Cache instantiated strategies per (group_idx, step_idx).
        self._strategy_cache: Dict[Tuple[int, int], PredictModel] = {}

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def predict(self, target_date: date, candidate_pool: Optional[List[int]] = None) -> List[int]:
        """Generate a single ticket for *target_date*.

        Iterates over each group, runs the strategy chain, picks
        ``pick_count`` distinct numbers (non-overlapping across groups),
        concatenates, and applies post-filters with retries.
        """
        return self._generate_one_ticket(target_date)

    def generate_tickets(self, target_date: date, ticket_count: Optional[int] = None) -> List[List[int]]:
        """Generate *ticket_count* distinct tickets for *target_date*.

        Deduplicates results so no two tickets are identical.  If fewer
        than ``ticket_count`` distinct tickets can be produced, logs a
        warning and returns whatever was generated.
        """
        count = ticket_count if ticket_count is not None else self.ticket_count
        seen: set = set()
        tickets: List[List[int]] = []
        attempts = 0
        max_attempts = max(count * 10, 100)

        while len(tickets) < count and attempts < max_attempts:
            ticket = self._generate_one_ticket(target_date)
            key = tuple(ticket)
            if key not in seen:
                seen.add(key)
                tickets.append(ticket)
            attempts += 1

        if len(tickets) < count:
            logger.warning(
                "generate_tickets: requested {} distinct tickets for {}, only produced {} after {} attempts",
                count,
                target_date,
                len(tickets),
                attempts,
            )

        return tickets

    def backtest(self, date_from=None, date_to=None) -> None:
        """Run the pipeline over the date range in ``self.df``.

        For each date, generates ``self.ticket_count`` tickets, compares each
        against the actual draw result, and stores results in
        ``self.df_backtest`` with the standard ``PredictModel`` column layout.

        After the loop, ``self.df_backtest`` is ready for ``evaluate()`` and
        ``revenue()``.
        """
        _df = self.df.copy()
        if date_from is not None:
            _df = _df[_df["date"] >= date_from]
        if date_to is not None:
            _df = _df[_df["date"] <= date_to]

        def fn_apply(row):
            tickets = self.generate_tickets(row.date, self.ticket_count)
            specials = self.predict_special(row.date)
            if not specials:
                specials = [None]

            predicted: List[dict] = []
            for ticket_idx, ticket in enumerate(tickets):
                for special_idx, special in enumerate(specials):
                    main_match, special_match = self._compare_list(
                        ticket,
                        special,
                        row.result,
                        has_special=self.has_special,
                        special_position=self.special_position,
                        special_pick_required=self.special_pick_required,
                        main_count=self.main_count,
                    )
                    is_correct = main_match == self.main_count
                    predicted.append(
                        {
                            PredictModel.col_predict_idx: ticket_idx,
                            PredictModel.col_special_idx: special_idx,
                            PredictModel.col_predict: ticket,
                            PredictModel.col_predict_special: special,
                            PredictModel.col_main_match: main_match,
                            PredictModel.col_special_match: special_match,
                            PredictModel.col_correct: is_correct,
                            PredictModel.col_correct_num: main_match,
                        }
                    )
            return predicted

        _df["predict_metadata"] = _df.apply(fn_apply, axis=1)
        self.df_backtest = _df

    # ------------------------------------------------------------------
    # Internal helpers — chain execution
    # ------------------------------------------------------------------

    def _get_strategy(self, group_idx: int, step_idx: int) -> PredictModel:
        """Return (cached) strategy instance for a single chain step."""
        key = (group_idx, step_idx)
        if key not in self._strategy_cache:
            g = self.groups[group_idx]
            step = g["strategies"][step_idx]
            strategy_key = step["strategy"]
            params = step.get("params", {})
            strat = instantiate(strategy_key, self.df, **params)
            self._strategy_cache[key] = strat
        return self._strategy_cache[key]

    def _run_chain(self, group_spec: dict, group_idx: int, target_date: date) -> List[int]:
        """Execute the strategy chain for one group and return
        ``pick_count`` numbers.

        Each step may carry an explicit ``pool_size`` (int ≥ 1) to control
        the size of the filtered pool at that point.  When absent / ``None``
        the step runs in "auto" mode using the strategy's natural output.

        Parameters
        ----------
        group_spec:
            Normalised group dict with ``strategies`` and ``pick_count``.
        group_idx:
            Index of the group (for caching).
        target_date:
            Draw date to predict for.

        Returns
        -------
        List[int]
            Sorted list of ``pick_count`` distinct numbers from the chain.
        """
        pool: List[int] = []
        strategies = group_spec["strategies"]

        for i, step in enumerate(strategies):
            strategy = self._get_strategy(group_idx, i)
            explicit_pool_size = step.get("pool_size")

            if i == 0:
                # First step: propose initial candidate pool.
                if explicit_pool_size is not None and explicit_pool_size >= 1:
                    pool = list(strategy.propose_top_numbers(target_date, int(explicit_pool_size)))
                else:
                    default_size = max(group_spec.get("pick_count", self.number_predict) * 3, 12)
                    pool = list(strategy.propose_top_numbers(target_date, default_size))
            else:
                # Subsequent step: filter the pool using the strategy's
                # ``filter_pool`` method.  Strategies that have a native
                # pool-filtering method (e.g. Steiner) override this to
                # return numbers drawn exclusively from the pool.
                previous_pool = pool

                if explicit_pool_size is not None and explicit_pool_size >= 1:
                    k = int(explicit_pool_size)
                else:
                    # Auto: let the strategy pick its natural output size
                    # from the pool, but never inflate the pool.
                    k = min(len(pool), self.number_predict)

                filtered = list(strategy.filter_pool(target_date, list(pool), k))

                if not filtered:
                    logger.warning(
                        "Chain step {} for group '{}' produced empty pool, keeping previous step pool",
                        i,
                        group_spec.get("name", "unnamed"),
                    )
                    pool = previous_pool
                else:
                    pool = filtered

        # Pick ``pick_count`` from the final pool.
        pick_count = group_spec["pick_count"]
        if len(pool) <= pick_count:
            return sorted(set(pool))
        return sorted(random.sample(pool, pick_count))

    def _generate_one_ticket(self, target_date: date) -> List[int]:
        """Generate a single ticket by assembling group picks and applying
        post-filters.  Retries up to ``_MAX_RETRIES`` times if filters fail."""
        ticket: List[int] = []
        for attempt in range(1, _MAX_RETRIES + 1):
            ticket = self._build_ticket(target_date)
            if self._passes_filters(ticket):
                return ticket
            if attempt == _MAX_RETRIES:
                logger.warning(
                    "PipelineStrategy: could not satisfy post-filters "
                    "after {} attempts for {}. Returning best-effort ticket.",
                    _MAX_RETRIES,
                    target_date,
                )
                return ticket
        return ticket

    def _build_ticket(self, target_date: date) -> List[int]:
        """Assemble numbers from all groups by running each group's strategy
        chain, ensuring no overlap across groups.

        When the chain output has fewer candidates than needed, numbers are
        padded from the full range.  Otherwise, numbers are randomly sampled
        to give variety across different invocations.
        """
        selected: set = set()

        for group_idx, g in enumerate(self.groups):
            chain_result = self._run_chain(g, group_idx, target_date)
            pick_count = g["pick_count"]

            # Filter out already-selected numbers.
            available = [n for n in chain_result if n not in selected]

            if len(available) < pick_count:
                # Pad from the full range.
                remaining = [n for n in range(self.min_val, self.max_val + 1) if n not in selected]
                available = available + remaining

            # Randomly sample to allow variation across multiple calls.
            picked = sorted(random.sample(available, pick_count))
            selected.update(picked)

        return sorted(selected)

    def _passes_filters(self, ticket: List[int]) -> bool:
        """Check whether *ticket* satisfies all active post-filters."""
        f = self.post_filters
        if not f:
            return True

        total = sum(ticket)
        evens = sum(1 for n in ticket if n % 2 == 0)
        odds = self.number_predict - evens

        min_sum = f.get("min_sum")
        max_sum = f.get("max_sum")
        min_even = f.get("min_even")
        max_even = f.get("max_even")
        min_odd = f.get("min_odd")
        max_odd = f.get("max_odd")

        if min_sum is not None and total < min_sum:
            return False
        if max_sum is not None and total > max_sum:
            return False
        if min_even is not None and evens < min_even:
            return False
        if max_even is not None and evens > max_even:
            return False
        if min_odd is not None and odds < min_odd:
            return False
        if max_odd is not None and odds > max_odd:
            return False

        return True
