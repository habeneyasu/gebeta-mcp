"""Engine value types and the seed-count invariant (spec §13, §14)."""

import dataclasses
from typing import Any

import pytest

from gebeta.domain.board import initial_board
from gebeta.domain.models import (
    GameResult,
    GameState,
    GameStatus,
    MoveRecord,
    Pickup,
    SeedTotals,
    Sowing,
    TurnReason,
)


def make_state(**overrides: Any) -> GameState:
    fields: dict[str, Any] = {
        "game_id": "g1",
        "board": initial_board(),
        "current_player": 1,
        "collected": SeedTotals(),
        "status": GameStatus.ACTIVE,
        "result": None,
        "starting_player": 1,
    }
    return GameState(**(fields | overrides))


def completed_state(**overrides: Any) -> GameState:
    fields: dict[str, Any] = {
        "board": (0,) * 12,
        "current_player": None,
        "collected": SeedTotals(30, 18),
        "status": GameStatus.COMPLETED,
        "result": GameResult.PLAYER_1_WINS,
    }
    return make_state(**(fields | overrides))


SOWING = Sowing(
    board=(0,) * 8 + (1, 1, 0, 0),
    pickups=(Pickup(6, 1), Pickup(7, 2)),
    landing_pit=9,
)


def make_record(**overrides: Any) -> MoveRecord:
    fields: dict[str, Any] = {
        "move_number": 1,
        "player": 1,
        "sowing": SOWING,
        "captured": 0,
        "awarded": None,
        "collected": SeedTotals(),
        "next_player": 2,
        "turn_reason": TurnReason.TURN_PASSES,
        "status": GameStatus.ACTIVE,
    }
    return MoveRecord(**(fields | overrides))


def test_seed_totals_index_by_player() -> None:
    totals = SeedTotals(5, 7)
    assert (totals[1], totals[2], totals.total) == (5, 7, 12)


def test_seed_totals_add_returns_new_totals() -> None:
    totals = SeedTotals()
    assert totals.add(2, 4) == SeedTotals(0, 4)
    assert totals == SeedTotals(0, 0)


def test_seed_totals_cannot_be_negative() -> None:
    with pytest.raises(ValueError):
        SeedTotals(-1, 0)


def test_sowing_derives_selected_pit_and_drop_count() -> None:
    assert (SOWING.pit, SOWING.seeds_picked_up, SOWING.drops) == (6, 1, 3)


def test_move_record_derives_landing_and_opposite_pits() -> None:
    record = make_record()
    assert (record.pit, record.landing_pit, record.opposite_pit) == (6, 9, 3)


def test_move_record_reports_capture_and_turn() -> None:
    record = make_record(captured=4, next_player=1, turn_reason=TurnReason.CAPTURE)
    assert record.capture_occurred
    assert record.turn_retained
    assert not make_record().capture_occurred
    assert not make_record().turn_retained


def test_initial_state_satisfies_invariant() -> None:
    state = make_state()
    assert sum(state.board) + state.collected[1] + state.collected[2] == 48


def test_completed_state_with_empty_pits_is_valid() -> None:
    assert completed_state().result is GameResult.PLAYER_1_WINS


def test_state_is_immutable() -> None:
    with pytest.raises(dataclasses.FrozenInstanceError):
        make_state().current_player = 2  # type: ignore[misc]


@pytest.mark.parametrize(
    "overrides",
    [
        {"board": (4,) * 11},
        {"board": (-1, 5) + (4,) * 10},
        {"board": (4,) * 11 + (3,)},
        {"collected": SeedTotals(1, 0)},
        {"current_player": None},
        {"result": GameResult.DRAW},
    ],
    ids=["11-pits", "negative-pit", "47-seeds", "49-seeds", "no-player", "early-result"],
)
def test_invalid_active_state_is_rejected(overrides: dict[str, Any]) -> None:
    with pytest.raises(ValueError):
        make_state(**overrides)


@pytest.mark.parametrize(
    "overrides",
    [
        {"board": (1,) + (0,) * 11, "collected": SeedTotals(29, 18)},
        {"current_player": 1},
        {"result": None},
    ],
    ids=["seeds-left", "current-player", "no-result"],
)
def test_invalid_completed_state_is_rejected(overrides: dict[str, Any]) -> None:
    with pytest.raises(ValueError):
        completed_state(**overrides)
