"""Domain values converted to wire schemas."""

from gebeta.application.game_service import GameNotFoundError
from gebeta.domain.errors import ErrorCode, MoveError
from gebeta.domain.game import apply_move, new_game
from gebeta.mapping import error_out, game_state_out, move_result_out
from gebeta.schemas import ErrorOut, GameStateOut, MoveResultOut, PickupOut, SeedTotalsOut
from tests.fixtures.positions import board_with, state_with


def test_new_game_state() -> None:
    out = game_state_out(new_game("g1"))

    assert out.game_id == "g1"
    assert out.board == [4] * 12
    assert (out.current_player, out.status, out.result) == (1, "active", None)
    assert out.legal_moves == [6, 7, 8, 9, 10, 11]
    assert out.collected == SeedTotalsOut(player_1=0, player_2=0)
    assert (out.move_count, out.moves_without_capture) == (0, 0)
    assert out.limits.max_drops == 10_000


def test_move_result() -> None:
    out = move_result_out(apply_move(state_with(board_with(p7=1, p2=2, p9=1)), 7))

    assert out.success is True
    move = out.move
    assert (move.move_number, move.player, move.pit, move.seeds_picked_up) == (1, 1, 7, 1)
    assert move.pickups == [PickupOut(pit=7, seeds=1)]
    assert (move.landing_pit, move.opposite_pit, move.captured) == (8, 2, 2)
    assert move.capture_occurred and move.turn_retained
    assert (move.turn_reason, move.status, move.awarded) == ("capture", "active", None)
    assert out.state.move_count == 1


def test_completed_game() -> None:
    result = apply_move(state_with(board_with(p7=1, p4=1), moves_without_capture=19), 7)
    out = move_result_out(result)

    assert out.move.turn_reason == "no_capture_limit"
    assert out.move.awarded == SeedTotalsOut(player_1=1, player_2=1)
    assert (out.state.status, out.state.result) == ("completed", "player_1_wins")
    assert (out.state.current_player, out.state.legal_moves) == (None, [])


def test_responses_survive_a_json_round_trip() -> None:
    result = move_result_out(apply_move(new_game("g1"), 6))
    assert MoveResultOut.model_validate_json(result.model_dump_json()) == result
    state = game_state_out(new_game("g1"))
    assert GameStateOut.model_validate_json(state.model_dump_json()) == state


def test_move_error() -> None:
    error = MoveError(ErrorCode.SOWING_CYCLE, "Move from pit 6 enters a sowing cycle.")
    assert error_out(error) == ErrorOut(
        code="sowing_cycle", message="Move from pit 6 enters a sowing cycle."
    )


def test_game_not_found_error() -> None:
    assert error_out(GameNotFoundError("missing")) == ErrorOut(
        code="game_not_found", message="Game 'missing' not found."
    )
