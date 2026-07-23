"""Integration tests for ``vietlott.web_api.app`` via FastAPI TestClient."""

from fastapi.testclient import TestClient

from vietlott.web_api.app import app

client = TestClient(app)


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


class TestHealth:
    def test_health_returns_ok(self):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# Products
# ---------------------------------------------------------------------------


class TestProducts:
    def test_list_products(self):
        resp = client.get("/api/products")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert "power_655" in data

    def test_product_info_known(self):
        resp = client.get("/api/products/power_655")
        assert resp.status_code == 200
        data = resp.json()
        assert data["min"] == 1
        assert data["max"] == 55
        assert data["size_output"] == 6

    def test_product_info_unknown(self):
        resp = client.get("/api/products/unknown")
        assert resp.status_code == 404
        assert "unknown" in resp.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------


class TestStrategies:
    def test_list_strategies(self):
        resp = client.get("/api/strategies")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        # At least the key strategies should be present.
        keys = {s["key"] for s in data}
        for expected in ("frequency", "steiner", "hot_numbers", "cold_numbers", "random"):
            assert expected in keys, f"Missing expected strategy: {expected}"

    def test_strategy_entry_structure(self):
        resp = client.get("/api/strategies")
        for entry in resp.json():
            assert "key" in entry
            assert "label" in entry
            assert "params" in entry


# ---------------------------------------------------------------------------
# Generate
# ---------------------------------------------------------------------------


class TestGenerate:
    def _valid_payload(self, product: str = "power_655") -> dict:
        pick_cnt = 5 if product in ("power_655", "power_645") else 4
        return {
            "pipeline": {
                "product": product,
                "groups": [
                    {
                        "name": "Steiner pool",
                        "strategy": "steiner",
                        "params": {"lookback_days": 365},
                        "pool_size": 15,
                        "pick_count": pick_cnt,
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
            },
            "target_date": "2024-06-15",
        }

    def test_generate_valid(self):
        resp = client.post("/api/generate", json=self._valid_payload())
        assert resp.status_code == 200, f"Body: {resp.text}"
        data = resp.json()
        assert "tickets" in data
        assert isinstance(data["tickets"], list)
        assert len(data["tickets"]) == 2
        for ticket in data["tickets"]:
            assert isinstance(ticket, list)
            assert len(ticket) == 6
            assert all(1 <= n <= 55 for n in ticket)
        assert data["total_cost_vnd"] > 0

    def test_generate_unknown_product(self):
        payload = {
            "pipeline": {
                "product": "unknown",
                "groups": [{"strategy": "random", "pick_count": 6}],
                "ticket_count": 1,
            },
        }
        resp = client.post("/api/generate", json=payload)
        # Should be 400 because the service raises ValueError
        assert resp.status_code == 400

    def test_generate_empty_groups(self):
        payload = {
            "pipeline": {
                "product": "power_655",
                "groups": [],
                "ticket_count": 1,
            },
        }
        resp = client.post("/api/generate", json=payload)
        # Pydantic validation: min_length=1 -> 422
        assert resp.status_code == 422

    def test_generate_extra_field_rejected(self):
        """Unknown fields in PipelineSpec should be rejected with 422."""
        payload = {
            "pipeline": {
                "product": "power_655",
                "groups": [{"strategy": "random", "pick_count": 6}],
                "ticket_count": 1,
                "bogus_field": "nope",
            },
        }
        resp = client.post("/api/generate", json=payload)
        assert resp.status_code == 422

    def test_generate_new_format_chain(self):
        """New format: groups[].strategies list (chain of 2 strategies)."""
        payload = {
            "pipeline": {
                "product": "power_655",
                "groups": [
                    {
                        "name": "Steiner->Freq",
                        "strategies": [
                            {"strategy": "steiner", "params": {"lookback_days": 365}, "pool_size": 15},
                            {"strategy": "frequency", "params": {"lookback_days": 90, "strategy_type": "hot"}},
                        ],
                        "pick_count": 3,
                    },
                    {
                        "name": "Random->Steiner",
                        "strategies": [
                            {"strategy": "random", "params": {}, "pool_size": 15},
                            {"strategy": "steiner", "params": {"lookback_days": 180}},
                        ],
                        "pick_count": 3,
                    },
                ],
                "combiner": {"method": "concatenate"},
                "post_filters": {},
                "ticket_count": 2,
            },
            "target_date": "2024-06-15",
        }
        resp = client.post("/api/generate", json=payload)
        assert resp.status_code == 200, f"Body: {resp.text}"
        data = resp.json()
        assert "tickets" in data
        assert len(data["tickets"]) == 2
        for ticket in data["tickets"]:
            assert len(ticket) == 6
            assert all(1 <= n <= 55 for n in ticket)
        assert data["total_cost_vnd"] == 2 * 10000

    def test_generate_old_format_still_works(self):
        """Backward compat: old single-strategy format still works."""
        payload = {
            "pipeline": {
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
            },
            "target_date": "2024-06-15",
        }
        resp = client.post("/api/generate", json=payload)
        assert resp.status_code == 200, f"Body: {resp.text}"
        data = resp.json()
        assert len(data["tickets"]) == 2
        for ticket in data["tickets"]:
            assert len(ticket) == 6
            assert all(1 <= n <= 55 for n in ticket)

    def test_generate_new_format_invalid_strategy(self):
        """New format with unknown strategy should be rejected."""
        payload = {
            "pipeline": {
                "product": "power_655",
                "groups": [
                    {
                        "name": "Bad chain",
                        "strategies": [
                            {"strategy": "nonexistent", "params": {}},
                        ],
                        "pick_count": 6,
                    },
                ],
            },
        }
        resp = client.post("/api/generate", json=payload)
        assert resp.status_code == 422 or resp.status_code == 400, f"Body: {resp.text}"

    def test_generate_explicit_pool_size_every_step(self):
        """Chain where every step has explicit pool_size."""
        payload = {
            "pipeline": {
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
            },
            "target_date": "2024-06-15",
        }
        resp = client.post("/api/generate", json=payload)
        assert resp.status_code == 200, f"Body: {resp.text}"
        data = resp.json()
        assert len(data["tickets"]) == 1
        assert len(data["tickets"][0]) == 6
        assert all(1 <= n <= 55 for n in data["tickets"][0])


# ---------------------------------------------------------------------------
# Backtest
# ---------------------------------------------------------------------------


class TestBacktest:
    def _spec(self, product: str = "power_655") -> dict:
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
        """Backtest a short range."""
        resp = client.post(
            "/api/backtest",
            json={
                "pipeline": self._spec("power_655"),
                "date_from": "2024-06-01",
                "date_to": "2024-07-01",
            },
        )
        assert resp.status_code == 200, f"Body: {resp.text}"
        data = resp.json()
        assert data["draws"] >= 1
        assert isinstance(data["matches_distribution"], dict)
        assert isinstance(data["per_draw"], list)
        assert len(data["per_draw"]) > 0
        assert data["total_cost_vnd"] > 0

    def test_backtest_power_535(self):
        """Backtest a short range for power_535."""
        resp = client.post(
            "/api/backtest",
            json={
                "pipeline": self._spec("power_535"),
                "date_from": "2025-07-01",
                "date_to": "2025-07-15",
            },
        )
        assert resp.status_code == 200, f"Body: {resp.text}"
        data = resp.json()
        assert data["draws"] >= 1
        assert isinstance(data["matches_distribution"], dict)
        assert len(data["per_draw"]) > 0

    def test_backtest_with_ticket_count_3(self):
        """Backtest with ticket_count=3."""
        spec = self._spec("power_655")
        spec["ticket_count"] = 3
        resp = client.post(
            "/api/backtest",
            json={
                "pipeline": spec,
                "date_from": "2024-06-01",
                "date_to": "2024-07-01",
            },
        )
        assert resp.status_code == 200, f"Body: {resp.text}"
        data = resp.json()
        assert data["tickets_per_draw"] == 3

    def test_backtest_invalid_date_range(self):
        """date_from > date_to should return 400."""
        resp = client.post(
            "/api/backtest",
            json={
                "pipeline": self._spec("power_655"),
                "date_from": "2024-07-01",
                "date_to": "2024-06-01",
            },
        )
        assert resp.status_code == 400

    def test_backtest_uses_pipeline_ticket_count_when_not_in_request(self):
        """No top-level ticket_count → pipeline.ticket_count is used."""
        pipeline = self._spec("power_655")
        pipeline["ticket_count"] = 7  # set at pipeline level
        resp = client.post(
            "/api/backtest",
            json={
                "pipeline": pipeline,
                "date_from": "2024-06-01",
                "date_to": "2024-07-01",
                # no ticket_count at top level
            },
        )
        assert resp.status_code == 200, f"Body: {resp.text}"
        data = resp.json()
        assert data["tickets_per_draw"] == 7, f"Expected 7, got {data['tickets_per_draw']}"
        assert "total_tickets" in data
        assert data["total_tickets"] == data["draws"] * data["tickets_per_draw"]

    def test_backtest_request_ticket_count_overrides_pipeline(self):
        """Top-level ticket_count overrides pipeline.ticket_count."""
        pipeline = self._spec("power_655")
        pipeline["ticket_count"] = 7  # pipeline says 7
        resp = client.post(
            "/api/backtest",
            json={
                "pipeline": pipeline,
                "date_from": "2024-06-01",
                "date_to": "2024-07-01",
                "ticket_count": 5,  # request says 5 (overrides)
            },
        )
        assert resp.status_code == 200, f"Body: {resp.text}"
        data = resp.json()
        assert data["tickets_per_draw"] == 5, f"Expected 5, got {data['tickets_per_draw']}"

    def test_backtest_per_draw_ticket_non_empty(self):
        """Each per_draw entry has a non-empty ticket with 6 numbers."""
        resp = client.post(
            "/api/backtest",
            json={
                "pipeline": self._spec("power_655"),
                "date_from": "2024-06-01",
                "date_to": "2024-07-01",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        for entry in data["per_draw"]:
            t = entry["ticket"]
            assert isinstance(t, list), f"ticket should be a list, got {type(t)}"
            assert len(t) == 6, f"ticket should have 6 numbers, got {len(t)}"
            assert all(isinstance(n, int) for n in t)

    def test_backtest_per_draw_tickets_field(self):
        """Each per_draw entry has a tickets list with at least 1 ticket."""
        resp = client.post(
            "/api/backtest",
            json={
                "pipeline": self._spec("power_655"),
                "date_from": "2024-06-01",
                "date_to": "2024-07-01",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        for entry in data["per_draw"]:
            assert "tickets" in entry, "Missing 'tickets' field"
            ts = entry["tickets"]
            assert isinstance(ts, list) and len(ts) >= 1
            for t in ts:
                assert isinstance(t, list) and len(t) == 6

    def test_backtest_per_draw_tickets_with_ticket_count_3(self):
        """With ticket_count=3, each per_draw has 3 tickets."""
        spec = self._spec("power_655")
        spec["ticket_count"] = 3
        resp = client.post(
            "/api/backtest",
            json={
                "pipeline": spec,
                "date_from": "2024-06-01",
                "date_to": "2024-07-01",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        for entry in data["per_draw"]:
            assert len(entry["tickets"]) == 3, f"Expected 3 tickets per draw, got {len(entry['tickets'])}"

    def test_backtest_unknown_product(self):
        resp = client.post(
            "/api/backtest",
            json={
                "pipeline": {
                    "product": "unknown",
                    "groups": [{"strategy": "random", "pick_count": 6}],
                },
                "date_from": "2024-06-01",
                "date_to": "2024-07-01",
            },
        )
        assert resp.status_code == 400
