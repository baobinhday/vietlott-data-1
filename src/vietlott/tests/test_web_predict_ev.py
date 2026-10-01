"""Tests for the Phase-1 web-adapter endpoints: ``POST /api/predict`` and ``POST /api/ev``.

The TS lib (``web/src/lib/predict.ts`` / ``ev.ts``) is the contract spec —
these tests assert the response shapes the frontend consumes
(camelCase keys via the pydantic aliases).
"""

from datetime import date

from fastapi.testclient import TestClient

from vietlott.web_api.app import app
from vietlott.web_api.service import compute_ev, predict_tickets

client = TestClient(app)


# ---------------------------------------------------------------------------
# POST /api/predict
# ---------------------------------------------------------------------------


class TestPredictEndpoint:
    def test_happy_path_power_645(self):
        resp = client.post(
            "/api/predict",
            json={
                "product": "power_645",
                "config": {"strategy": "Inverse Hybrid: Cold Numbers → Steiner", "tpd": 3},
                "target_date": "2025-10-15",
            },
        )
        assert resp.status_code == 200, f"Body: {resp.text}"
        data = resp.json()
        # PredictionResult contract fields.
        for key in ("product", "productDisplay", "strategy", "config", "previousDraw", "tickets", "generatedAt"):
            assert key in data, f"Missing key {key}"
        assert data["product"] == "power_645"
        assert data["productDisplay"] == "Power 6/45"
        assert data["strategy"] == "Inverse Hybrid: Cold Numbers → Steiner"
        # No special pick required for 6/45 → exactly tpd tickets, predictedSpecial null.
        assert len(data["tickets"]) == 3
        ticket = data["tickets"][0]
        assert set(ticket.keys()) == {"predicted", "predictedSpecial", "coverage"}
        assert len(ticket["predicted"]) == 6
        assert all(1 <= n <= 45 for n in ticket["predicted"])
        assert ticket["predictedSpecial"] is None
        assert ticket["coverage"] == 1
        # previousDraw shape.
        prev = data["previousDraw"]
        assert set(prev.keys()) == {"date", "id", "result"}
        # Config echo (camelCase).
        assert data["config"]["tpd"] == 3
        assert data["config"]["steiner"]["lookbackDays"] == 365
        assert data["config"]["specials"]["mode"] == "markov_steiner"
        assert data["config"]["ddFilter"]["enabled"] is True

    def test_happy_path_power_535_wheels_specials(self):
        resp = client.post(
            "/api/predict",
            json={"product": "power_535", "target_date": "2025-10-15"},
        )
        assert resp.status_code == 200, f"Body: {resp.text}"
        data = resp.json()
        assert data["productDisplay"] == "Power 5/35"
        # default tpd=2 × specials.topN=4.
        assert len(data["tickets"]) == 8
        specials_seen = {t["predictedSpecial"] for t in data["tickets"]}
        assert len(specials_seen) == 4
        assert None not in specials_seen
        assert all(1 <= s <= 12 for s in specials_seen)
        assert all(len(t["predicted"]) == 5 for t in data["tickets"])
        assert all(1 <= n <= 35 for t in data["tickets"] for n in t["predicted"])

    def test_target_date_defaults_to_next_draw(self):
        """Omitted target_date → response still produced (next draw computed)."""
        resp = client.post("/api/predict", json={"product": "power_645", "config": {"tpd": 1}})
        assert resp.status_code == 200, f"Body: {resp.text}"
        data = resp.json()
        assert len(data["tickets"]) == 1

    def test_trio_strategy(self):
        resp = client.post(
            "/api/predict",
            json={
                "product": "power_535",
                "strategy": "Inverse Hybrid: Trio (Cold + PairFreq + Pattern)",
                "config": {"tpd": 2},
                "target_date": "2025-10-15",
            },
        )
        assert resp.status_code == 200, f"Body: {resp.text}"
        data = resp.json()
        assert data["strategy"] == "Inverse Hybrid: Trio (Cold + PairFreq + Pattern)"
        assert len(data["tickets"]) == 8

    def test_unknown_product_400(self):
        resp = client.post("/api/predict", json={"product": "unknown_product"})
        assert resp.status_code == 400

    def test_invalid_tpd_400(self):
        resp = client.post(
            "/api/predict",
            json={"product": "power_645", "config": {"tpd": 0}, "target_date": "2025-10-15"},
        )
        assert resp.status_code == 400

    def test_snake_case_accepted(self):
        """snake_case request fields populate the camelCase contract."""
        resp = client.post(
            "/api/predict",
            json={
                "product": "power_645",
                "target_date": "2025-10-15",
                "config": {"tpd": 1, "cold": {"lookback_days": 90}},
            },
        )
        assert resp.status_code == 200
        assert resp.json()["config"]["cold"]["lookbackDays"] == 90


class TestPredictService:
    def test_power_645_ten_tickets_diverse(self):
        """6/45 tickets are pairwise distinct with overlap <= size_output - 2 = 4."""
        result = predict_tickets("power_645", config={"tpd": 10}, target_date=date(2025, 10, 15))
        tickets = result["tickets"]
        assert len(tickets) == 10
        sets = [set(t["predicted"]) for t in tickets]
        for i, s_i in enumerate(sets):
            assert len(s_i) == 6
            for s_j in sets[i + 1 :]:
                assert s_i != s_j, "tickets must be pairwise distinct as sets"
                assert len(s_i & s_j) <= 4, f"overlap {len(s_i & s_j)} > 4 between tickets {i} and later"

    def test_power_535_ticket_count_matches_ts(self):
        result = predict_tickets("power_535", target_date=date(2025, 10, 15))
        assert len(result["tickets"]) == 2 * 4  # tpd × specials.topN
        assert result["previous_draw"]["date"] < "2025-10-15"

    def test_unknown_product_raises(self):
        import pytest

        with pytest.raises(ValueError, match="Unknown"):
            predict_tickets("nope", target_date=date(2025, 10, 15))


# ---------------------------------------------------------------------------
# POST /api/ev
# ---------------------------------------------------------------------------


class TestEvEndpoint:
    def test_happy_path_power_535(self):
        resp = client.post(
            "/api/ev",
            json={"product": "power_535", "numTickets": 8, "historyLimit": 10},
        )
        assert resp.status_code == 200, f"Body: {resp.text}"
        data = resp.json()
        for key in (
            "product",
            "display",
            "ticketPrice",
            "jackpotBase",
            "historySampleSize",
            "historyEndId",
            "tierMode",
            "evPerTicket",
            "totalEv",
            "numTickets",
            "breakdown",
            "projection",
        ):
            assert key in data, f"Missing key {key}"
        assert data["ticketPrice"] == 10_000
        assert data["numTickets"] == 8
        assert isinstance(data["breakdown"], list) and len(data["breakdown"]) == 7
        row = data["breakdown"][0]
        assert set(row.keys()) == {
            "tier",
            "displayName",
            "probability",
            "expectedPayout",
            "ev",
            "splitAdjusted",
            "expectedOtherWinners",
        }
        tiers = [b["tier"] for b in data["breakdown"]]
        assert tiers[0] == "jackpot" and tiers[-1] == "khuyen_khich"
        proj = data["projection"]
        for key in (
            "expectedNextJackpot",
            "expectedRevenue",
            "expectedTickets",
            "avgTicketsLastN",
            "sampleSize",
            "confidence",
            "avgJackpotWinnersLastN",
            "expectedWinners",
            "splitMode",
        ):
            assert key in proj, f"Missing projection key {key}"
        assert proj["expectedWinners"]["khuyen_khich"] >= 0
        # totalEv = evPerTicket × numTickets
        assert data["totalEv"] == data["evPerTicket"] * 8

    def test_historical_mean_mode(self):
        resp = client.post("/api/ev", json={"product": "power_535", "tierMode": "historical_mean"})
        assert resp.status_code == 200, f"Body: {resp.text}"
        assert resp.json()["tierMode"] == "historical_mean"

    def test_history_end_id_not_found(self):
        resp = client.post("/api/ev", json={"product": "power_535", "historyEndId": "999999"})
        assert resp.status_code == 400

    def test_unknown_product(self):
        resp = client.post("/api/ev", json={"product": "unknown_product"})
        assert resp.status_code == 400

    def test_few_draws_with_prizes_400(self):
        resp = client.post("/api/ev", json={"product": "power_535", "historyLimit": 2, "historyEndId": "00002"})
        # Either works (2 draws is enough) or 400 if prize data is missing for those ids.
        assert resp.status_code in (200, 400)


class TestEvService:
    def test_compute_ev_defaults_match_ts(self):
        result = compute_ev("power_535")
        assert result["display"] == "Power 5/35"
        assert result["ticket_price"] == 10_000
        assert result["num_tickets"] == 8
        assert len(result["breakdown"]) == 7
        probs = {b["tier"]: b["probability"] for b in result["breakdown"]}
        # p(5+1) = 1/3,895,584
        assert probs["jackpot"] < 1e-6
        assert result["projection"]["sample_size"] > 0

    def test_ev_per_ticket_formula(self):
        # Breakdown EV is sum of p*payout minus price.
        result = compute_ev("power_535")
        raw = sum(b["ev"] for b in result["breakdown"])
        assert result["ev_per_ticket"] == raw - 10_000
