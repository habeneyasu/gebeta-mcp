"""Move execution, turn order, and game end (spec §18, criteria 9, 15–27, 30–31, 35–36, 39)."""

import pytest

from gebeta.domain.board import initial_board
from gebeta.domain.errors import ErrorCode, MoveError
from gebeta.domain.game import Game
from gebeta.domain.models import GameResult, GameState, GameStatus, Limits, SeedTotals, TurnReason
from tests.fixtures.positions import LOOPING_BOARD, LOOPING_PIT, board_with, state_with


def test_new_game_starts_with_player_1_by_default() -> None:
    state = Game.new("g1").state
    assert state.board == initial_board()
    assert (state.current_player, state.status, state.collected) == (
        1,
        GameStatus.ACTIVE,
        SeedTotals(),
    )
    assert state.history == ()


def test_new_game_can_start_with_player_2() -> None:
    assert Game.new("g1", starting_player=2).state.current_player == 2


def test_capture_on_own_side_keeps_the_turn() -> None:
    state = state_with(board_with(p7=1, p2=2, p9=1))
    move = Game(state).apply_move(7)

    assert move.state.board == board_with(p8=1, p9=1)
    assert move.record.captured == 2
    assert move.state.collected[1] == state.collected[1] + 2
    assert (move.state.current_player, move.record.turn_reason) == (1, TurnReason.CAPTURE)


def test_capture_on_opponent_side() -> None:
    move = Game(state_with(board_with(p11=1, p6=2, p9=1))).apply_move(11)

    assert move.record.landing_pit == 0
    assert move.record.captured == 2
    assert move.state.board == board_with(p0=1, p9=1)


def test_capture_passes_the_turn_when_the_capturer_cannot_move() -> None:
    move = Game(state_with(board_with(p11=1, p6=2))).apply_move(11)

    assert move.record.captured == 2
    assert (move.state.current_player, move.record.turn_reason) == (2, TurnReason.TURN_PASSES)


def test_no_capture_passes_the_turn() -> None:
    move = Game(state_with(board_with(p7=1, p4=1))).apply_move(7)

    assert move.record.captured == 0
    assert move.state.board[8] == 1
    assert (move.state.current_player, move.record.turn_reason) == (2, TurnReason.TURN_PASSES)


def test_no_capture_keeps_the_turn_when_the_opponent_cannot_move() -> None:
    move = Game(state_with(board_with(p7=1, p9=1))).apply_move(7)

    assert (move.state.current_player, move.record.turn_reason) == (
        1,
        TurnReason.OPPONENT_HAS_NO_MOVE,
    )


def test_capture_is_checked_only_where_sowing_ends() -> None:
    # Continuation passes through pit 7, opposite the seeds in pit 1; only pit 9 counts.
    move = Game(state_with(board_with(p6=1, p7=1, p1=3, p4=1))).apply_move(6)

    assert move.record.landing_pit == 9
    assert move.record.captured == 0
    assert move.state.board[1] == 3


@pytest.mark.parametrize(
    ("pit", "code"),
    [(12, ErrorCode.INVALID_PIT), (-1, ErrorCode.INVALID_PIT), (0, ErrorCode.OPPONENT_PIT)],
)
def test_invalid_and_opponent_pits_are_rejected(pit: int, code: ErrorCode) -> None:
    with pytest.raises(MoveError) as excinfo:
        Game.new("g1").apply_move(pit)
    assert excinfo.value.code is code


@pytest.mark.parametrize(
    ("state", "pit", "code"),
    [
        (state_with(board_with(p6=1, p0=1)), 7, ErrorCode.EMPTY_PIT),
        (state_with(LOOPING_BOARD), LOOPING_PIT, ErrorCode.SOWING_CYCLE),
        (
            state_with(board_with(p0=13), 2, limits=Limits(max_drops=24)),
            0,
            ErrorCode.SOWING_LIMIT_EXCEEDED,
        ),
    ],
    ids=["empty", "cycle", "limit"],
)
def test_rejected_moves_leave_the_state_unchanged(
    state: GameState, pit: int, code: ErrorCode
) -> None:
    before = (state.board, state.current_player, state.collected, state.status, state.history)
    with pytest.raises(MoveError) as excinfo:
        Game(state).apply_move(pit)
    assert excinfo.value.code is code
    after = (state.board, state.current_player, state.collected, state.status, state.history)
    assert after == before


def test_game_ends_when_neither_player_can_move() -> None:
    # After 11 → 0, pit 0 continues into pit 1 and pit 1 needs 3 drops: both exceed the limit.
    state = state_with(board_with(p11=1, p1=3), limits=Limits(max_drops=2))
    move = Game(state).apply_move(11)

    assert move.record.turn_reason is TurnReason.NO_LEGAL_MOVES
    assert move.record.awarded == SeedTotals(0, 4)
    assert_completed(move.state, GameResult.PLAYER_1_WINS)


def test_game_ends_after_twenty_moves_without_capture() -> None:
    move = Game(state_with(board_with(p7=1, p4=1), moves_without_capture=19)).apply_move(7)

    assert move.record.turn_reason is TurnReason.NO_CAPTURE_LIMIT
    assert move.record.awarded == SeedTotals(1, 1)
    assert move.state.collected == SeedTotals(47, 1)
    assert_completed(move.state, GameResult.PLAYER_1_WINS)


def test_capture_resets_the_no_capture_count() -> None:
    move = Game(state_with(board_with(p7=1, p2=2, p9=1), moves_without_capture=19)).apply_move(7)

    assert move.state.moves_without_capture == 0
    assert move.state.status is GameStatus.ACTIVE


def test_completed_game_rejects_moves_and_has_no_legal_moves() -> None:
    ended = Game(state_with(board_with(p7=1, p4=1), moves_without_capture=19)).apply_move(7).state

    assert Game(ended).legal_moves() == ()
    with pytest.raises(MoveError) as excinfo:
        Game(ended).apply_move(7)
    assert excinfo.value.code is ErrorCode.GAME_OVER


def test_successful_move_is_committed_to_the_game() -> None:
    game = Game.new("g1")
    result = game.apply_move(6)
    assert game.state is result.state


def test_rejected_move_is_not_committed_to_the_game() -> None:
    game = Game(state_with(LOOPING_BOARD))
    before = game.state
    with pytest.raises(MoveError):
        game.apply_move(LOOPING_PIT)
    assert game.state is before


def test_history_records_each_move() -> None:
    game = Game.new("g1")
    first = game.apply_move(6)
    second = game.apply_move(game.legal_moves()[0])

    assert game.state.history == (first.record, second.record)
    assert [r.move_number for r in second.state.history] == [1, 2]
    assert (first.record.player, first.record.pit, first.record.sowing.seeds_picked_up) == (
        1,
        6,
        4,
    )
    assert first.record.collected == first.state.collected
    assert first.record.next_player == first.state.current_player == 2


def assert_completed(state: GameState, result: GameResult) -> None:
    assert state.status is GameStatus.COMPLETED
    assert state.current_player is None
    assert state.board == (0,) * 12
    assert state.collected.total == 48
    assert state.result is result
