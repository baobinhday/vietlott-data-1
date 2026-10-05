"""Unit tests for the sales-free rollover timing signal in ``vietlott.web_api.rollover``."""

from datetime import date

from vietlott.web_api import rollover as rollover_mod
from vietlott.web_api.rollover import (
    ROLLOVER_MIN,
    get_rollover_state,
    should_play,
)
from vietlott.web_api.service import predict_tickets


def _index(jackpot_value: int, winners: int) -> dict:
    """Build the loader's ``{draw_id: {tier: {pv, winners}}}`` shape for one draw."""
    return {
        "Jackpot": {"prize_value": jackpot_value, "winners_count": winners},
    }


def test_hot_when_pool_and_streak_are_high(monkeypatch):
    """power_645 at 30B (2.5× min) with 6 straight no-winner draws → hot."""
    index = {f"{i:05d}": _index(30_000_000_000, 0) for i in range(1, 7)}
    monkeypatch.setattr(rollover_mod, "_load_prizes_index", lambda product: index)

    state = get_rollover_state("power_645")
    assert state["level"] == "hot"
    assert state["streak"] == 6
    assert state["multiple_of_min"] == 2.5
    assert state["latest_draw_id"] == "00006"
    assert state["jackpot_value"] == 30_000_000_000
    assert state["jackpot_winners"] == 0
    assert should_play("power_645") is True


def test_cold_when_pool_near_min_and_short_streak(monkeypatch):
    """power_645 at 12.1B with a single rollover → cold."""
    index = {
        "00001": _index(12_100_000_000, 1),
        "00002": _index(12_100_000_000, 0),
    }
    monkeypatch.setattr(rollover_mod, "_load_prizes_index", lambda product: index)

    state = get_rollover_state("power_645")
    assert state["level"] == "cold"
    assert state["streak"] == 1
    assert state["multiple_of_min"] == 12_100_000_000 / 12_000_000_000
    assert state["latest_draw_id"] == "00002"
    assert should_play("power_645") is False


def test_unknown_when_index_is_empty(monkeypatch):
    """Missing prize data degrades to the unknown state without raising."""
    monkeypatch.setattr(rollover_mod, "_load_prizes_index", lambda product: {})

    state = get_rollover_state("power_645")
    assert state["level"] == "unknown"
    assert state["latest_draw_id"] is None
    assert state["jackpot_value"] == 0
    assert should_play("power_645") is False


def test_streak_stops_at_first_winner(monkeypatch):
    """A winner in an earlier draw terminates the consecutive streak."""
    index = {
        "00001": _index(12_500_000_000, 0),
        "00002": _index(12_500_000_000, 0),
        "00003": _index(12_500_000_000, 1),  # winner breaks the chain
        "00004": _index(12_500_000_000, 0),
    }
    monkeypatch.setattr(rollover_mod, "_load_prizes_index", lambda product: index)

    state = get_rollover_state("power_645")
    assert state["streak"] == 1
    assert state["latest_draw_id"] == "00004"


def test_power_655_uses_jackpot_1_tier(monkeypatch):
    """power_655 reads "Jackpot 1" against its 30B minimum."""
    index = {f"{i:05d}": {"Jackpot 1": {"prize_value": 75_000_000_000, "winners_count": 0}} for i in range(1, 4)}
    monkeypatch.setattr(rollover_mod, "_load_prizes_index", lambda product: index)

    state = get_rollover_state("power_655")
    assert ROLLOVER_MIN["power_655"] == 30_000_000_000
    assert state["multiple_of_min"] == 2.5
    assert state["level"] == "hot"


def test_unsupported_product_is_unknown(monkeypatch):
    """power_535 (and anything else) stays out of the signal → unknown."""
    monkeypatch.setattr(rollover_mod, "_load_prizes_index", lambda product: {"00001": _index(6_000_000_000, 0)})

    state = get_rollover_state("power_535")
    assert state["level"] == "unknown"
    assert should_play("power_535") is False


def test_predict_tickets_includes_rollover():
    """Integration: predict_tickets exposes a valid rollover signal for 6/45."""
    result = predict_tickets("power_645", config={"tpd": 1}, target_date=date(2025, 10, 15))
    assert "rollover" in result
    signal = result["rollover"]
    assert signal is not None
    assert signal["level"] in ("cold", "warm", "hot")
    assert signal["product"] == "power_645"
    assert isinstance(signal["streak"], int)
