"""Unit tests for ``vietlott.web_api.service`` (no HTTP)."""

from datetime import date

import pytest

from vietlott.web_api.service import (
    compute_next_draw_date,
    generate_tickets,
    get_all_products,
    get_product_info,
    get_strategies_metadata,
    run_backtest,
)

# ---------------------------------------------------------------------------
# get_strategies_metadata
# ---------------------------------------------------------------------------


class TestGetStrategiesMetadata:
    def test_returns_non_empty_list(self):
        result = get_strategies_metadata()
        assert isinstance(result, list)
        assert len(result) > 0

    def test_entries_have_required_keys(self):
        for entry in get_strategies_metadata():
            assert "key" in entry
            assert "label" in entry
            assert "description" in entry
            assert "params" in entry


# ---------------------------------------------------------------------------
# get_all_products / get_product_info
# ---------------------------------------------------------------------------


class TestProducts:
    def test_get_all_products(self):
        products = get_all_products()
        assert "power_655" in products
        assert "power_645" in products
        assert "power_535" in products

    def test_get_product_info_known(self):
        info = get_product_info("power_655")
        assert info["min"] == 1
        assert info["max"] == 55
        assert info["size_output"] == 6
        assert info["has_special"] is True
        assert info["ticket_price"] == 10000

    def test_get_product_info_unknown(self):
        with pytest.raises(ValueError, match="Unknown"):
            get_product_info("bogus")


# ---------------------------------------------------------------------------
# compute_next_draw_date
# ---------------------------------------------------------------------------


class TestComputeNextDrawDate:
    def test_returns_date(self):
        result = compute_next_draw_date("power_655", today=date(2024, 1, 1))
        assert isinstance(result, date)

    def test_returns_future_date(self):
        today = date(2024, 1, 1)
        result = compute_next_draw_date("power_655", today=today)
        assert result >= today

    def test_returns_date_for_power535(self):
        result = compute_next_draw_date("power_535", today=date(2025, 7, 1))
        assert isinstance(result, date)
        assert result >= date(2025, 7, 1)


# ---------------------------------------------------------------------------
# generate_tickets
# ---------------------------------------------------------------------------


class TestGenerateTickets:
    def _sample_pipeline(self, product: str = "power_655") -> dict:
        return {
            "product": product,
            "groups": [
                {
                    "name": "Steiner pool",
                    "strategy": "steiner",
                    "params": {"lookback_days": 365},
                    "pool_size": 15,
                    "pick_count": 5 if product == "power_655" or product == "power_645" else 4,
                },
                {
                    "name": "Frequency filler",
                    "strategy": "frequency",
                    "params": {"lookback_days": 90, "strategy_type": "hot"},
                    "pool_size": 10,
                    "pick_count": 1 if product == "power_655" or product == "power_645" else 1,
                },
            ],
            "combiner": {"method": "concatenate"},
            "post_filters": {},
            "ticket_count": 2,
        }

    def test_generate_returns_tickets(self):
        result = generate_tickets(
            self._sample_pipeline("power_655"),
            target_date=date(2024, 6, 15),
        )
        assert "tickets" in result
        assert isinstance(result["tickets"], list)
        assert len(result["tickets"]) == 2
        for ticket in result["tickets"]:
            assert isinstance(ticket, list)
            assert len(ticket) == 6
            assert all(1 <= n <= 55 for n in ticket)
            assert ticket == sorted(ticket)
            assert len(set(ticket)) == 6
        assert result["total_cost_vnd"] == 2 * 10000
        assert result["product"] == "power_655"

    def test_generate_power535(self):
        result = generate_tickets(
            self._sample_pipeline("power_535"),
            target_date=date(2025, 7, 15),
        )
        assert "tickets" in result
        assert len(result["tickets"]) == 2
        for ticket in result["tickets"]:
            assert len(ticket) == 5
            assert all(1 <= n <= 35 for n in ticket)

    def test_generate_invalid_product(self):
        with pytest.raises(ValueError, match="Unknown"):
            generate_tickets(
                {"product": "bogus", "groups": [{"strategy": "random", "pick_count": 6}]},
                target_date=date(2024, 6, 15),
            )

    def test_generate_new_format(self):
        """New format with chain strategies works."""
        pipeline = {
            "product": "power_655",
            "groups": [
                {
                    "name": "Chain A",
                    "strategies": [
                        {"strategy": "steiner", "params": {"lookback_days": 365}, "pool_size": 20},
                        {"strategy": "frequency", "params": {"lookback_days": 90, "strategy_type": "hot"}},
                    ],
                    "pick_count": 3,
                },
                {
                    "name": "Chain B",
                    "strategies": [
                        {"strategy": "random", "params": {}, "pool_size": 55},
                        {"strategy": "steiner", "params": {"lookback_days": 180}},
                    ],
                    "pick_count": 3,
                },
            ],
            "combiner": {"method": "concatenate"},
            "post_filters": {},
            "ticket_count": 2,
        }
        result = generate_tickets(pipeline, target_date=date(2024, 6, 15))
        assert "tickets" in result
        assert len(result["tickets"]) == 2
        for ticket in result["tickets"]:
            assert len(ticket) == 6
            assert all(1 <= n <= 55 for n in ticket)
            assert ticket == sorted(ticket)
            assert len(set(ticket)) == 6

    def test_generate_old_format_still_works(self):
        """Old format still works via backward compat in service layer."""
        pipeline = {
            "product": "power_655",
            "groups": [
                {
                    "name": "Steiner pool",
                    "strategy": "steiner",
                    "params": {"lookback_days": 365},
                    "pool_size": 15,
                    "pick_count": 5,
                },
                {
                    "name": "Frequency filler",
                    "strategy": "frequency",
                    "params": {"lookback_days": 90, "strategy_type": "hot"},
                    "pool_size": 10,
                    "pick_count": 1,
                },
            ],
            "combiner": {"method": "concatenate"},
            "post_filters": {},
            "ticket_count": 2,
        }
        result = generate_tickets(pipeline, target_date=date(2024, 6, 15))
        assert "tickets" in result
        assert len(result["tickets"]) == 2
        for ticket in result["tickets"]:
            assert len(ticket) == 6
            assert all(1 <= n <= 55 for n in ticket)

    def test_generate_mixed_old_new_format(self):
        """Mixed old + new format groups in same pipeline."""
        pipeline = {
            "product": "power_655",
            "groups": [
                {
                    "name": "Old group",
                    "strategy": "random",
                    "params": {},
                    "pool_size": 55,
                    "pick_count": 3,
                },
                {
                    "name": "New group",
                    "strategies": [
                        {"strategy": "random", "params": {}, "pool_size": 55},
                    ],
                    "pick_count": 3,
                },
            ],
            "combiner": {"method": "concatenate"},
            "post_filters": {},
            "ticket_count": 1,
        }
        result = generate_tickets(pipeline, target_date=date(2024, 6, 15))
        assert len(result["tickets"]) == 1
        assert len(result["tickets"][0]) == 6

    def test_generate_explicit_per_step_pool_size(self):
        """Chain with explicit pool_size at every step."""
        pipeline = {
            "product": "power_655",
            "groups": [
                {
                    "name": "Explicit chain",
                    "strategies": [
                        {"strategy": "random", "params": {}, "pool_size": 20},
                        {
                            "strategy": "frequency",
                            "params": {"lookback_days": 90, "strategy_type": "hot"},
                            "pool_size": 10,
                        },
                        {"strategy": "steiner", "params": {"lookback_days": 365}, "pool_size": 6},
                    ],
                    "pick_count": 6,
                },
            ],
            "combiner": {"method": "concatenate"},
            "post_filters": {},
            "ticket_count": 1,
        }
        result = generate_tickets(pipeline, target_date=date(2024, 6, 15))
        assert len(result["tickets"]) == 1
        assert len(result["tickets"][0]) == 6
        assert all(1 <= n <= 55 for n in result["tickets"][0])
        assert result["total_cost_vnd"] == 10000

    def test_generate_requested_ticket_count_satisfied_with_steiner(self):
        """Regression: ticket_count must be satisfied even when Steiner is restrictive.

        Previously the chain was fully deterministic, so requesting 30
        tickets for a Steiner step with limited disjoint blocks returned
        only 3.  The fix threads ``ticket_count`` through as
        ``coverage`` and tops up with random samples from the pool.
        """
        pipeline = {
            "product": "power_655",
            "groups": [
                {
                    "name": "Restrictive Steiner",
                    "strategies": [
                        {"strategy": "pair_frequency", "params": {"lookback_days": 365}, "pool_size": 15},
                        {
                            "strategy": "steiner",
                            "params": {"lookback_days": 365, "t": "5", "k": "6", "v": "15"},
                            "pool_size": 6,
                        },
                    ],
                    "pick_count": 6,
                },
            ],
            "combiner": {"method": "concatenate"},
            "post_filters": {},
            "ticket_count": 30,
        }
        result = generate_tickets(pipeline, target_date=date(2024, 6, 15))
        assert len(result["tickets"]) == 30, (
            f"Expected 30 tickets, got {len(result['tickets'])} — Steiner chain failed to fall back to random"
        )
        # All 30 must be distinct
        unique = {tuple(t) for t in result["tickets"]}
        assert len(unique) == 30, f"Expected 30 unique tickets, got {len(unique)}"
        for ticket in result["tickets"]:
            assert len(ticket) == 6
            assert all(1 <= n <= 55 for n in ticket)


# ---------------------------------------------------------------------------
# run_backtest
# ---------------------------------------------------------------------------


class TestRunBacktest:
    def _sample_pipeline(self, product: str = "power_655") -> dict:
        pick_cnt = 5 if product in ("power_655", "power_645") else 4
        return {
            "product": product,
            "groups": [
                {
                    "name": "Steiner",
                    "strategy": "steiner",
                    "params": {"lookback_days": 365},
                    "pool_size": 15,
                    "pick_count": pick_cnt,
                },
                {
                    "name": "Frequency",
                    "strategy": "frequency",
                    "params": {"lookback_days": 90, "strategy_type": "hot"},
                    "pool_size": 10,
                    "pick_count": 1,
                },
            ],
            "combiner": {"method": "concatenate"},
            "post_filters": {},
            "ticket_count": 1,
        }

    def test_backtest_power_655(self):
        """Backtest a short range for power_655."""
        result = run_backtest(
            self._sample_pipeline("power_655"),
            date_from=date(2024, 6, 1),
            date_to=date(2024, 7, 1),
        )
        assert result["draws"] >= 1
        assert isinstance(result["matches_distribution"], dict)
        assert isinstance(result["per_draw"], list)
        assert all(isinstance(d, dict) for d in result["per_draw"])
        assert result["total_cost_vnd"] > 0
        assert result["total_revenue_vnd"] >= 0
        assert "roi" in result

    def test_backtest_power_535(self):
        """Backtest a short range for power_535 (5-number lottery with special)."""
        result = run_backtest(
            self._sample_pipeline("power_535"),
            date_from=date(2025, 7, 1),
            date_to=date(2025, 7, 15),
        )
        assert result["draws"] >= 1
        assert isinstance(result["matches_distribution"], dict)
        assert len(result["per_draw"]) > 0
        assert result["total_cost_vnd"] > 0

    def test_backtest_with_ticket_count(self):
        """When ticket_count > 1, cost should reflect the extra tickets per draw."""
        spec = self._sample_pipeline("power_655")
        spec["ticket_count"] = 3
        result = run_backtest(
            spec,
            date_from=date(2024, 6, 1),
            date_to=date(2024, 7, 1),
        )
        assert result["tickets_per_draw"] == 3
        assert result["total_cost_vnd"] > 0

    def test_backtest_invalid_date_range(self):
        """date_from > date_to is invalid."""
        from vietlott.web_api.service import _validate_date_range

        with pytest.raises(ValueError, match="date_from"):
            _validate_date_range(date_from=date(2024, 7, 1), date_to=date(2024, 6, 1))

    def test_backtest_invalid_product(self):
        with pytest.raises(ValueError, match="Unknown"):
            run_backtest(
                {"product": "bogus", "groups": [{"strategy": "random", "pick_count": 6}]},
                date_from=date(2024, 6, 1),
                date_to=date(2024, 7, 1),
            )

    def test_per_draw_structure(self):
        """Each per_draw entry should have the expected keys."""
        result = run_backtest(
            self._sample_pipeline("power_655"),
            date_from=date(2024, 6, 1),
            date_to=date(2024, 7, 1),
        )
        for entry in result["per_draw"]:
            assert "date" in entry
            assert "ticket" in entry
            assert "tickets" in entry, "per_draw must have 'tickets' field"
            assert "actual" in entry
            assert "matches" in entry
            assert "prize_vnd" in entry
            assert "cumulative_profit_vnd" in entry

    def test_per_draw_ticket_non_empty(self):
        """The ticket field in per_draw should be a non-empty list of ints."""
        result = run_backtest(
            self._sample_pipeline("power_655"),
            date_from=date(2024, 6, 1),
            date_to=date(2024, 7, 1),
        )
        for entry in result["per_draw"]:
            t = entry["ticket"]
            assert isinstance(t, list), f"ticket should be a list, got {type(t)}"
            assert len(t) == 6, f"ticket should have 6 numbers, got {len(t)}"
            assert all(isinstance(n, int) for n in t), "ticket must contain ints"

    def test_per_draw_tickets_all_predictions(self):
        """tickets field contains all predicted tickets for the draw."""
        result = run_backtest(
            self._sample_pipeline("power_655"),
            date_from=date(2024, 6, 1),
            date_to=date(2024, 7, 1),
        )
        for entry in result["per_draw"]:
            ts = entry["tickets"]
            assert isinstance(ts, list), "tickets should be a list"
            assert len(ts) >= 1, "tickets should have at least one ticket"
            for t in ts:
                assert isinstance(t, list) and len(t) == 6, f"Each ticket in tickets should have 6 numbers"
                assert all(isinstance(n, int) for n in t)

    def test_per_draw_tickets_with_ticket_count_3(self):
        """With ticket_count=3, each per_draw has 3 entries in tickets."""
        spec = self._sample_pipeline("power_655")
        spec["ticket_count"] = 3
        result = run_backtest(
            spec,
            date_from=date(2024, 6, 1),
            date_to=date(2024, 7, 1),
        )
        for entry in result["per_draw"]:
            assert len(entry["tickets"]) == 3, f"Expected 3 tickets per draw, got {len(entry['tickets'])}"

    def test_backtest_respects_explicit_ticket_count(self):
        """Explicit ticket_count overrides pipeline spec."""
        spec = self._sample_pipeline("power_655")
        spec["ticket_count"] = 7  # pipeline says 7
        result = run_backtest(
            spec,
            date_from=date(2024, 6, 1),
            date_to=date(2024, 7, 1),
            ticket_count=5,  # override to 5
        )
        assert result["tickets_per_draw"] == 5, f"Expected 5, got {result['tickets_per_draw']}"
        assert "total_tickets" in result
        assert result["total_tickets"] == result["draws"] * result["tickets_per_draw"]

    def test_backtest_no_explicit_ticket_count_uses_pipeline(self):
        """No ticket_count passed → pipeline.ticket_count is used."""
        spec = self._sample_pipeline("power_655")
        spec["ticket_count"] = 9  # pipeline says 9
        result = run_backtest(
            spec,
            date_from=date(2024, 6, 1),
            date_to=date(2024, 7, 1),
            # no ticket_count parameter
        )
        assert result["tickets_per_draw"] == 9, f"Expected 9, got {result['tickets_per_draw']}"

    def test_backtest_total_tickets_in_response(self):
        """Response always includes total_tickets = draws * tickets_per_draw."""
        result = run_backtest(
            self._sample_pipeline("power_655"),
            date_from=date(2024, 6, 1),
            date_to=date(2024, 7, 1),
        )
        assert "total_tickets" in result
        assert result["total_tickets"] == result["draws"] * result["tickets_per_draw"]
