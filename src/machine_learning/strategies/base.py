"""
Base class for all lottery prediction strategies.

All concrete strategy classes must inherit from ``PredictModel`` and override
the :meth:`predict` method.  The base class provides:

* shared constants (number range, prize table, column names);
* generic :meth:`backtest` that calls ``predict`` once per row in the dataset;
* :meth:`evaluate` that flattens the backtest results and computes accuracy
  statistics; and
* :meth:`revenue` that estimates profit/loss given the prize structure.
"""

from typing import List

import pandas as pd


class PredictModel:
    """
    Abstract base model for Vietlott lottery number prediction.

    Sub-classes implement :meth:`predict` with their own selection logic.
    The remaining methods (:meth:`backtest`, :meth:`evaluate`, :meth:`revenue`)
    are generic and work unchanged for every strategy.

    Class-level constants
    ---------------------
    POWER_655_MIN_VAL / POWER_655_MAX_VAL
        Inclusive number range for Power 6/55 (1–55).
    number_predict
        How many distinct numbers form a single ticket (6).
    ticket_price
        Cost of a single ticket in VND (10,000).
    prices
        Mapping from ``correct_num`` → prize amount in VND.
    col_*
        Column name constants used across backtest / evaluate DataFrames.
    """

    POWER_655_MIN_VAL = 1
    POWER_655_MAX_VAL = 55  # assume we are using power655
    number_predict = 6
    ticket_price = 10000

    prices = {6: 30_000_000_000, 5: 40_000_000, 4: 500_000, 3: 50_000}

    # Canonical main-number field names (aliased from the legacy names above)
    main_count: int = 6
    main_min: int = 1
    main_max: int = 55

    # Special-number (số đặc biệt) fields
    has_special: bool = False
    special_position: int = 0
    special_pick_required: bool = False
    special_min: int = 0
    special_max: int = 0
    special_count: int = 1

    # Training-time toggle: include the special number when building
    # strategy statistics (Markov transitions, Steiner pair-freq, hot/cold
    # frequency, etc.).  Default ``False`` — strategies train on main
    # numbers only, which is the correct behaviour for prize computation
    # (main_match is judged on main numbers, special_match is separate).
    # Set to ``True`` to reproduce the legacy behaviour where the special
    # number was treated as just another main number during training.
    include_special_in_training: bool = False

    col_date = "date"
    col_result = "result"
    col_predict = "predicted"
    col_predict_time = "predict_time"
    col_predict_metadata = "predict_metadata"
    col_correct = "is_correct"
    col_correct_num = "correct_num"
    col_predict_idx = "predict_idx"
    col_special_idx = "special_idx"
    col_predict_special = "predicted_special"
    col_main_match = "main_match"
    col_special_match = "special_match"

    def __init__(
        self,
        df: pd.DataFrame,
        time_predict: int = 1,
        min_val: int = POWER_655_MIN_VAL,
        max_val: int = POWER_655_MAX_VAL,
    ):
        """
        Parameters
        ----------
        df:
            Historical lottery draw data.  Must contain at least a ``date``
            column and a ``result`` column where each cell is a list of drawn
            numbers.
        time_predict:
            Number of independent tickets to generate per draw date during
            backtesting.  Higher values increase cost but give the model more
            chances to match any given draw.
        min_val:
            Smallest valid lottery number (inclusive).
        max_val:
            Largest valid lottery number (inclusive).
        """
        self.df = df
        self.df_backtest = None
        self.df_backtest_explode = None
        self.df_backtest_evaluate = None
        self.time_predict = time_predict
        self.min_val = min_val
        self.max_val = max_val
        self.prize_fn = None  # set by render files per product
        self.product_name: str | None = None  # set by apply_product_config
        self._id_column: str = "id"  # source column carrying the draw id

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @classmethod
    def _count_number(cls, number_series):
        """Return a frequency table for numbers across all draw rows."""
        return number_series.explode().value_counts().to_frame("times")

    def _main_numbers(self, result):
        """Return only the main numbers from a draw's result list.

        Excludes the special number (số đặc biệt) for products that have one
        (e.g. Power 6/55, Power 5/35) **unless** ``include_special_in_training``
        is set to ``True`` on this instance.  Strategies must train only on
        main numbers, so this helper slices ``result`` to ``special_position``
        when the product has a special number and the row is long enough.

        For legacy rows with fewer than ``special_position + 1`` elements
        (e.g. 6-number rows from before the special was added), returns
        the result unchanged.

        Parameters
        ----------
        result:
            A list-like of drawn numbers.  May be a list, tuple or
            ``numpy`` array; a fresh ``list`` is always returned so
            callers may mutate it freely.
        """
        if self.include_special_in_training:
            return list(result)
        if self.has_special and len(result) > self.special_position:
            return list(result[: self.special_position])
        return list(result)

    @classmethod
    def _compare_list(
        cls,
        predicted_main,
        predicted_special,
        result,
        has_special=False,
        special_position=0,
        special_pick_required=False,
        main_count=6,
    ):
        """
        Compare predicted main + special numbers against the actual draw result.

        Parameters
        ----------
        predicted_main:
            List of main-number predictions (length ``main_count``).
        predicted_special:
            The special-number prediction (scalar) or ``None`` when not
            explicitly picked.
        result:
            The actual draw result list.
        has_special:
            Whether this product has a special number.
        special_position:
            0-based index of the special number in ``result``.
        special_pick_required:
            Whether the player explicitly picks a special number.
        main_count:
            How many main numbers are in a ticket.

        Returns
        -------
        (main_match, special_match)
            ``main_match`` — count of predicted_main that appear in
            ``result[:special_position]`` (or full result when no special).
            ``special_match`` — 1 if special matched, else 0.
        """
        # If the result list does not have a special position (e.g. legacy data
        # with only 6 numbers for 6/55), treat it as no special regardless of
        # the has_special flag.
        effective_has_special = has_special and special_position < len(result)

        if effective_has_special:
            main_result = set(result[:special_position])
            special_result = result[special_position]
        else:
            main_result = set(result)
            special_result = None

        main_match = len(set(predicted_main) & main_result)

        if effective_has_special:
            if special_pick_required:
                # e.g. 5/35: player picks special explicitly
                special_match = 1 if (predicted_special is not None and predicted_special == special_result) else 0
            else:
                # e.g. 6/55: any predicted main == result[special_position]
                special_match = 1 if special_result in predicted_main else 0
        else:
            special_match = 0

        return main_match, special_match

    # ------------------------------------------------------------------
    # Core interface
    # ------------------------------------------------------------------

    def apply_product_config(self, config):
        """Configure this model for a specific Vietlott product.

        Returns self for chaining.
        """
        self.main_min = config.min_value
        self.main_max = config.max_value
        self.main_count = config.size_output
        # Mirror to legacy names for backward compat
        self.min_val = config.min_value
        self.max_val = config.max_value
        self.number_predict = config.size_output
        # Special config
        self.has_special = getattr(config, "has_special", False)
        self.special_position = getattr(config, "special_position", 0)
        self.special_pick_required = getattr(config, "special_pick_required", False)
        self.special_min = getattr(config, "special_min", 0)
        self.special_max = getattr(config, "special_max", 0)
        self.special_count = getattr(config, "special_count", 1)
        # Steiner system (S(t, k, v)) — only SteinerStrategy consumes this.
        # Setting the value here triggers an in-place rebuild of the
        # Steiner blocks via :meth:`SteinerStrategy.set_steiner_system`.
        steiner_system = getattr(config, "steiner_system", None)
        if steiner_system is not None and hasattr(self, "set_steiner_system"):
            self.set_steiner_system(*steiner_system)
        if hasattr(config, "name"):
            from vietlott.config.prizes import get_prize_fn

            self.prize_fn = get_prize_fn(config.name)
            self.product_name = config.name
        return self

    def predict_special(self, date, candidate_pool=None):
        """Return list of special-number predictions (length = special_count).

        Default behaviour
        -----------------
        - If ``special_pick_required`` is False: return [] (no separate
          special pick, e.g. 6/55 overlap, 6/45 no-special).
        - Otherwise: return all specials in range (wheeling, e.g. 5/35
          returns ``[1, 2, …, 12]``).

        Strategies may override for smarter special-number prediction.
        """
        if not self.special_pick_required:
            return []
        return list(range(self.special_min, self.special_max + 1))

    def propose_top_numbers(self, target_date, k: int) -> List[int]:
        """Return up to ``k`` numbers from the strategy's native signal.

        Acts as the "proposer" role in :class:`InverseHybridStrategy`:
        another component (e.g. Steiner) uses this list as the candidate
        pool to pick from with its own algorithm.

        The default fallback returns the first ``k`` numbers in
        ``[min_val, max_val]``.  Strategies with their own scoring
        (frequency, absence, co-occurrence, etc.) should override this
        to expose a more meaningful ranking.
        """
        del target_date  # unused in fallback
        return list(range(self.min_val, min(self.min_val + k, self.max_val + 1)))

    def filter_pool(self, target_date, pool: List[int], k: int, coverage: int = 1) -> List[int]:
        """Filter a candidate pool to ``k`` numbers using this strategy.

        The default implementation calls ``predict(target_date, candidate_pool=pool)``
        and returns the intersection of its output with ``pool``, capped to ``k``.
        If the strategy returns fewer than ``k`` numbers from the pool, remaining
        slots are filled from the pool in sorted order.

        Sub-classes that have a native "pick from a given pool" method
        (e.g. ``SteinerStrategy.predict_from_pool``) should override this for
        better results.

        Parameters
        ----------
        target_date:
            Date for which to generate the prediction.
        pool:
            Candidate pool of distinct numbers to pick from.
        k:
            Desired number of output numbers (max).
        coverage:
            How many distinct tickets the caller wants.  Most strategies
            can ignore this and return a single deterministic result;
            strategies that can produce multiple distinct picks
            (e.g. Steiner) use it to pre-build a deeper ranked list
            that successive calls can rotate through.

        Returns
        -------
        Sorted list of up to ``k`` numbers drawn from ``pool``.  May return
        fewer than ``k`` if the pool itself is smaller.
        """
        del coverage  # unused in the default implementation
        if k >= len(pool):
            return sorted(set(pool))
        predicted = self.predict(target_date, candidate_pool=pool)
        pool_set = set(pool)
        result = [n for n in predicted if n in pool_set]
        # Top-up from pool if the strategy returned fewer than k.
        if len(result) < k:
            extra_pool = [n for n in pool if n not in set(result)]
            result = result + sorted(extra_pool[: k - len(result)])
        return sorted(result[:k])

    def _prize_for(self, main_match, special_match):
        """Compute prize for (main_match, special_match)."""
        if self.prize_fn is not None:
            return self.prize_fn(main_match, special_match)
        return self.prices.get(main_match, 0)

    def predict(self, date, candidate_pool=None) -> List[int]:
        """
        Predict lottery numbers for the given draw date.

        Sub-classes **must** override this method.

        Parameters
        ----------
        date:
            The draw date for which predictions should be generated.
            Only data strictly *before* this date should be used to avoid
            look-ahead bias.
        candidate_pool:
            Optional constrained set of numbers to pick from.  When
            provided, the strategy MUST restrict its selection to numbers
            in this pool.  When ``None``, the strategy picks from the
            full ``[min_val, max_val]`` range as usual.

        Returns
        -------
        list[int]
            A sorted list of ``number_predict`` distinct integers in
            ``[min_val, max_val]``.
        """
        pass

    def backtest(self, date_from=None, date_to=None, draw_ids=None):
        """
        Run the strategy over rows in ``self.df``.

        For each row the strategy generates ``time_predict`` main-number
        predictions and (for products with ``special_pick_required``) wheels
        through all specials.  Each combination is stored as a separate row
        in ``predict_metadata``.

        Results are saved to ``self.df_backtest``.

        Parameters
        ----------
        date_from:
            Optional start date (inclusive) for the backtest period.  Only
            rows with ``date >= date_from`` are evaluated.  The full
            ``self.df`` is still available to strategies for historical
            lookups; this only limits *which* dates are evaluated.
        date_to:
            Optional end date (inclusive) for the backtest period.  Only
            rows with ``date <= date_to`` are evaluated.
        draw_ids:
            Optional iterable / set of draw-id strings.  When supplied,
            only rows whose ``id`` is in the set are evaluated – the
            strategies still see the full ``self.df`` for lookback
            windows / voter logic, but no ticket is "bought" on
            non-listed draws (no cost, no gain).  Useful for variants
            that only want to play on specific draws (e.g. when the
            jackpot crosses a threshold).
        """
        _df = self.df.copy()
        if date_from is not None:
            _df = _df[_df["date"] >= date_from]
        if date_to is not None:
            _df = _df[_df["date"] <= date_to]
        if draw_ids is not None:
            id_set = {str(x) for x in draw_ids}
            _df = _df[_df["id"].astype(str).isin(id_set)]

        def fn_apply(row):
            predicted = []
            for i in range(self.time_predict):
                main_pred = self.predict(row.date)
                specials = self.predict_special(row.date)

                if not specials:
                    specials = [None]  # one entry per main prediction

                for special_idx, special in enumerate(specials):
                    main_match, special_match = self._compare_list(
                        main_pred,
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
                            PredictModel.col_predict_idx: i,
                            PredictModel.col_special_idx: special_idx,
                            PredictModel.col_predict: main_pred,
                            PredictModel.col_predict_special: special,
                            PredictModel.col_main_match: main_match,
                            PredictModel.col_special_match: special_match,
                            PredictModel.col_correct: is_correct,
                            PredictModel.col_correct_num: main_match,  # backward compat alias
                            # Carry the source draw id so per-draw prize
                            # lookups can run after ``evaluate()``.
                            "draw_id": row.get(self._id_column) if hasattr(row, "get") else None,
                        }
                    )

            return predicted

        _df["predict_metadata"] = _df.apply(fn_apply, axis=1)
        self.df_backtest = _df

    def evaluate(self):
        """
        Flatten backtest metadata and compute accuracy statistics.

        Populates ``self.df_backtest_explode`` and
        ``self.df_backtest_evaluate``, then returns a summary dict with:

        * ``correct_time`` – total number of fully-correct tickets.
        * ``count_correct_num`` – frequency distribution of main-match counts.
        """
        self.df_backtest_explode = self.df_backtest.explode(PredictModel.col_predict_metadata)
        self.df_backtest_evaluate = pd.concat(
            [
                self.df_backtest_explode.reset_index(drop=True),
                pd.json_normalize(self.df_backtest_explode[PredictModel.col_predict_metadata]).reset_index(drop=True),
            ],
            axis="columns",
        )

        return {
            "correct_time": self.df_backtest_evaluate[PredictModel.col_correct].sum(),
            "count_correct_num": self.df_backtest_evaluate[PredictModel.col_main_match].value_counts(),
        }

    def revenue(self):
        """
        Estimate financial outcome of the backtest.

        Returns
        -------
        (cost, gain, profit)
            All values in VND.  ``profit = gain - cost``.

        When ``self.product_name`` is set and the backtest rows carry a
        ``draw_id``, the gain is computed via
        :func:`vietlott.config.prizes.get_actual_prize_for_draw` so
        per-draw jackpots from ``data/<product>_prizes.jsonl`` are used.
        Falls back to the configured ``prize_fn`` (and ultimately the
        hardcoded baseline) when the data is missing.
        """
        cost = len(self.df_backtest_evaluate) * self.ticket_price
        # Try per-draw lookup first; resolve import lazily so the base
        # module has no hard dependency on the prize data files.
        product = self.product_name or ""
        use_actual = bool(product) and "draw_id" in self.df_backtest_evaluate.columns
        if use_actual:
            from vietlott.config.prizes import get_actual_prize_for_draw

            def _gain_row(m, s, did):
                return int(
                    get_actual_prize_for_draw(
                        product,
                        did,
                        int(m),
                        int(s),
                    )
                )

            gain = sum(
                _gain_row(m, s, did)
                for m, s, did in zip(
                    self.df_backtest_evaluate[PredictModel.col_main_match],
                    self.df_backtest_evaluate[PredictModel.col_special_match],
                    self.df_backtest_evaluate["draw_id"],
                )
            )
        else:
            gain = sum(
                self._prize_for(int(m), int(s))
                for m, s in zip(
                    self.df_backtest_evaluate[PredictModel.col_main_match],
                    self.df_backtest_evaluate[PredictModel.col_special_match],
                )
            )

        return cost, gain, gain - cost
