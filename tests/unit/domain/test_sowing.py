"""Sowing acceptance tests (spec §18, criteria 10–14, 27, 30)."""

import contextlib

import pytest

from gebeta.domain.board import initial_board
from gebeta.domain.errors import ErrorCode, MoveError
from gebeta.domain.models import Pickup
from gebeta.domain.sowing import DEFAULT_MAX_DROPS, sow
from tests.fixtures.positions import LOOPING_BOARD, LOOPING_PIT


def board_with(**pits: int) -> tuple[int, ...]:
    """A board that is empty except for the given pits, e.g. board_with(p6=2)."""
    board = [0] * 12
    for name, seeds in pits.items():
        board[int(name.removeprefix("p"))] = seeds
    return tuple(board)


def test_default_limit_is_10000_drops() -> None:
    assert DEFAULT_MAX_DROPS == 10_000


def test_sowing_stops_when_final_seed_lands_in_empty_pit() -> None:
    sowing = sow(board_with(p6=2, p7=1), 6)

    assert sowing.board == board_with(p7=2, p8=1)
    assert sowing.pickups == (Pickup(6, 2),)
    assert sowing.landing_pit == 8


def test_occupied_landing_pit_is_picked_up_and_sown_from_next_pit() -> None:
    sowing = sow(board_with(p6=1, p7=1), 6)

    assert sowing.pickups == (Pickup(6, 1), Pickup(7, 2))
    assert sowing.board == board_with(p8=1, p9=1)
    assert sowing.landing_pit == 9


def test_hand_larger_than_twelve_wraps_and_sows_into_selected_pit() -> None:
    sowing = sow(board_with(p0=13), 0)

    assert sowing.pickups == (
        Pickup(0, 13),
        Pickup(1, 2),
        Pickup(3, 2),
        Pickup(5, 2),
        Pickup(7, 2),
        Pickup(9, 2),
        Pickup(11, 2),
    )
    assert sowing.board == (2, 1, 2, 0, 2, 0, 2, 0, 2, 0, 2, 0)
    assert sowing.landing_pit == 1
    assert sowing.drops == 25


def test_opening_move_distributes_every_seed_exactly_once() -> None:
    sowing = sow(initial_board(), 6)

    assert sowing.pickups == (
        Pickup(6, 4),
        Pickup(10, 5),
        Pickup(3, 5),
        Pickup(8, 6),
        Pickup(2, 6),
    )
    assert sowing.board == (6, 6, 0, 1, 6, 6, 2, 7, 1, 6, 1, 6)
    assert sowing.landing_pit == 8
    assert sum(sowing.board) == 48
    assert sowing.drops == 26


def test_looping_move_is_rejected_with_sowing_cycle() -> None:
    with pytest.raises(MoveError) as excinfo:
        sow(LOOPING_BOARD, LOOPING_PIT)
    assert excinfo.value.code is ErrorCode.SOWING_CYCLE


@pytest.mark.parametrize("pit", [0, 2, 3, 5, 8, 10])
def test_other_moves_in_looping_position_complete(pit: int) -> None:
    sowing = sow(LOOPING_BOARD, pit)
    assert sowing.board[sowing.landing_pit] == 1


def test_move_within_drop_limit_succeeds() -> None:
    assert sow(board_with(p0=13), 0, max_drops=25).drops == 25


def test_move_over_drop_limit_is_rejected() -> None:
    with pytest.raises(MoveError) as excinfo:
        sow(board_with(p0=13), 0, max_drops=24)
    assert excinfo.value.code is ErrorCode.SOWING_LIMIT_EXCEEDED


def test_drop_limit_can_stop_a_looping_move_before_the_cycle_repeats() -> None:
    with pytest.raises(MoveError) as excinfo:
        sow(LOOPING_BOARD, LOOPING_PIT, max_drops=100)
    assert excinfo.value.code is ErrorCode.SOWING_LIMIT_EXCEEDED


@pytest.mark.parametrize("pit", [LOOPING_PIT, 5])
def test_input_board_is_not_modified(pit: int) -> None:
    board = list(LOOPING_BOARD)
    with contextlib.suppress(MoveError):
        sow(board, pit)
    assert board == list(LOOPING_BOARD)


@pytest.mark.parametrize("pit", [-1, 12])
def test_invalid_pit_is_a_caller_error(pit: int) -> None:
    with pytest.raises(ValueError):
        sow(initial_board(), pit)


def test_empty_pit_is_a_caller_error() -> None:
    with pytest.raises(ValueError):
        sow(board_with(p6=1), 7)


def test_board_must_have_twelve_pits() -> None:
    with pytest.raises(ValueError):
        sow((4,) * 11, 6)


def test_max_drops_must_be_positive() -> None:
    with pytest.raises(ValueError):
        sow(initial_board(), 6, max_drops=0)
