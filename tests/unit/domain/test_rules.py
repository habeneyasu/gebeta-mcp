"""Legal moves, capture, turn order, and scoring (spec §18, criteria 8, 17–18, 24–25, 28–33)."""

import pytest

from gebeta.domain import rules
from gebeta.domain.board import initial_board
from gebeta.domain.models import DEFAULT_LIMITS, GameResult, Limits, SeedTotals, TurnReason
from tests.fixtures.positions import LOOPING_BOARD, board_with


def test_every_own_pit_is_legal_on_the_opening_board() -> None:
    assert rules.legal_moves(initial_board(), 1, DEFAULT_LIMITS) == (6, 7, 8, 9, 10, 11)
    assert rules.legal_moves(initial_board(), 2, DEFAULT_LIMITS) == (0, 1, 2, 3, 4, 5)


def test_empty_pits_are_not_legal() -> None:
    assert rules.legal_moves(board_with(p7=1, p9=1), 1, DEFAULT_LIMITS) == (7, 9)


def test_looping_moves_are_excluded() -> None:
    assert rules.legal_moves(LOOPING_BOARD, 1, DEFAULT_LIMITS) == (8, 10)
    assert rules.legal_moves(LOOPING_BOARD, 2, DEFAULT_LIMITS) == (0, 2, 3, 5)


def test_moves_over_the_drop_limit_are_excluded() -> None:
    board = board_with(p0=13)  # this move takes 25 drops
    assert rules.legal_moves(board, 2, Limits(max_drops=24)) == ()
    assert rules.legal_moves(board, 2, Limits(max_drops=25)) == (0,)


def test_player_with_empty_row_has_no_legal_moves() -> None:
    assert rules.legal_moves(board_with(p7=1), 2, DEFAULT_LIMITS) == ()
    assert not rules.has_legal_move(board_with(p7=1), 2, DEFAULT_LIMITS)


def test_capture_takes_every_seed_from_the_opposite_pit() -> None:
    assert rules.capture(board_with(p2=5, p8=1), 8) == (board_with(p8=1), 5)


def test_no_capture_when_the_opposite_pit_is_empty() -> None:
    assert rules.capture(board_with(p8=1), 8) == (board_with(p8=1), 0)


def test_game_ends_when_neither_player_has_a_legal_move() -> None:
    # Every non-empty pit needs at least 2 drops, so a 1-drop limit leaves no legal move.
    board = board_with(p0=2, p6=2)
    turn = rules.next_turn(board, 1, captured=0, moves_without_capture=1, limits=Limits(1))
    assert turn == (None, TurnReason.NO_LEGAL_MOVES)


def test_game_ends_at_the_no_capture_limit() -> None:
    turn = rules.next_turn(
        initial_board(), 1, captured=0, moves_without_capture=20, limits=DEFAULT_LIMITS
    )
    assert turn == (None, TurnReason.NO_CAPTURE_LIMIT)


def test_remaining_seeds_go_to_the_row_owner() -> None:
    board = board_with(p0=1, p5=2, p6=3, p11=4)
    assert rules.remaining_seeds(board) == SeedTotals(player_1=7, player_2=3)


@pytest.mark.parametrize(
    ("collected", "expected"),
    [
        (SeedTotals(30, 18), GameResult.PLAYER_1_WINS),
        (SeedTotals(18, 30), GameResult.PLAYER_2_WINS),
        (SeedTotals(24, 24), GameResult.DRAW),
    ],
)
def test_result_is_decided_by_collected_seeds(collected: SeedTotals, expected: GameResult) -> None:
    assert rules.result(collected) is expected
