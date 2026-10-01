"""Tests for Phase-2 endpoints: ``GET /api/draws`` and ``POST /api/backtest/strategy``."""

from fastapi.testclient import TestClient

from vietlott.web_api.app import app

client = TestClient(app)


# ---------------------------------------------------------------------------
# GET /api/draws
# ---------------------------------------------------------------------------


class TestDrawsEndpoint:
    def test_happy_path_power_645(self):
        resp = client.get("/api/draws", params={"product": "power_645", "limit": 3})
        assert resp.status_code == 200, f"Body: {resp.text}"
        data = resp.json()
        for key in ("product", "display", "total", "draws"):
            assert key in data, f"Missing key {key}"
        assert data["product"] == "power_645"
        assert data["display"] == "Power 6/45"
        assert isinstance(data["total"], int) and data["total"] >= 3
        assert len(data["draws"]) == 3
        draw = data["draws"][0]
        assert {"date", "id", "result"} <= set(draw.keys())
        assert len(draw["result"]) == 6
        assert all(1 <= n <= 45 for n in draw["result"])
        # Newest-first ordering.
        dates = [d["date"] for d in data["draws"]]
        assert dates == sorted(dates, reverse=True)

    def test_prizes_attached(self):
        resp = client.get("/api/draws", params={"product": "power_535", "limit": 2, "prizes": "1"})
        assert resp.status_code == 200, f"Body: {resp.text}"
        data = resp.json()
        for draw in data["draws"]:
            assert "prizes" in draw
            assert draw["prizes"], f"Expected prize tiers for draw {draw['id']}"
            tier = draw["prizes"][0]
            assert {"prize_name", "prize_value", "winners_count"} <= set(tier.keys())

    def test_no_prizes_by_default(self):
        resp = client.get("/api/draws", params={"product": "power_535", "limit": 2})
        assert resp.status_code == 200
        assert all(d.get("prizes") is None for d in resp.json()["draws"])

    def test_limit_clamped(self):
        resp = client.get("/api/draws", params={"product": "power_645", "limit": 500})
        assert resp.status_code == 200
        assert len(resp.json()["draws"]) <= 200

    def test_unknown_product_400(self):
        resp = client.get("/api/draws", params={"product": "unknown_product"})
        assert resp.status_code == 400

    def test_3d_dict_results_skipped_like_ts(self):
        """3d stores dict results; the old TS loader skipped them (empty draws, total 0)."""
        resp = client.get("/api/draws", params={"product": "3d", "prizes": "1"})
        assert resp.status_code == 200, f"Body: {resp.text}"
        data = resp.json()
        assert data["product"] == "3d"
        assert len(data["draws"]) == 0


# ---------------------------------------------------------------------------
# POST /api/backtest/strategy
# ---------------------------------------------------------------------------


class TestStrategyBacktestEndpoint:
    def test_happy_path_power_645(self):
        resp = client.post(
            "/api/backtest/strategy",
            json={
                "product": "power_645",
                "config": {
                    "strategy": "Inverse Hybrid: Cold Numbers → Steiner",
                    "tpd": 1,
                    "ddFilter": {"enabled": False},
                    "dateFrom": "2025-07-01",
                    "dateTo": "2025-07-31",
                },
            },
        )
        assert resp.status_code == 200, f"Body: {resp.text}"
        data = resp.json()
        for key in (
            "totalCost",
            "totalGain",
            "netProfit",
            "roi",
            "totalDraws",
            "totalPredictions",
            "matchDistribution",
            "specialHits",
            "bestThreshold",
            "eligibleDraws",
            "bestResults",
            "yearlyBreakdown",
            "allRows",
        ):
            assert key in data, f"Missing key {key}"
        assert data["totalDraws"] >= 1
        assert data["totalPredictions"] >= data["totalDraws"]  # tpd=1 × 1 wheel
        assert data["totalCost"] == data["totalPredictions"] * 10_000
        assert data["netProfit"] == data["totalGain"] - data["totalCost"]
        assert isinstance(data["yearlyBreakdown"], list) and data["yearlyBreakdown"]
        year_row = data["yearlyBreakdown"][0]
        assert set(year_row.keys()) == {"year", "draws", "predictions", "cost", "gain", "profit", "roi"}

    def test_power_535_dd_filter_and_specials(self):
        resp = client.post(
            "/api/backtest/strategy",
            json={
                "product": "power_535",
                "config": {"tpd": 1, "ddFilter": {"enabled": True, "threshold": 15_000_000_000}},
            },
        )
        assert resp.status_code == 200, f"Body: {resp.text}"
        data = resp.json()
        assert data["totalDraws"] >= 1
        # Wheel tpd × topN specials.
        assert data["totalPredictions"] == data["totalDraws"] * 4
        row = data["allRows"][0]
        assert {
            "date",
            "drawId",
            "predicted",
            "predictedSpecial",
            "result",
            "mainMatch",
            "specialMatch",
            "gain",
            "isCorrect",
            "predictIdx",
            "specialIdx",
        } <= set(row.keys())
        assert row["predictedSpecial"] is not None
        assert 1 <= row["predictedSpecial"] <= 12

    def test_unknown_product_400(self):
        resp = client.post("/api/backtest/strategy", json={"product": "unknown_product"})
        assert resp.status_code == 400

    def test_invalid_tpd_400(self):
        resp = client.post(
            "/api/backtest/strategy",
            json={"product": "power_645", "config": {"tpd": 0}},
        )
        assert resp.status_code == 400
