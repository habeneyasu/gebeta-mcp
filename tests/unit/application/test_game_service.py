"""Game service use cases, wire output, and per-game locking."""

import itertools
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import pytest

from gebeta.application.game_service import GameNotFoundError, GameService, error_out
from gebeta.domain.errors import ErrorCode, MoveError
from gebeta.domain.models import GameState, Limits
from gebeta.infrastructure.memory_repository import InMemoryGameRepository
from gebeta.schemas import (
    ErrorOut,
    GameStateOut,
    LimitsOut,
    MoveResultOut,
    PickupOut,
    SeedTotalsOut,
)
from tests.fixtures.positions import board_with, state_with


def make_service(limits: Limits | None = None) -> GameService:
    ids = (f"g{n}" for n in itertools.count(1))
    if limits is None:
        return GameService(InMemoryGameRepository(), new_game_id=lambda: next(ids))
    return GameService(InMemoryGameRepository(), limits=limits, new_game_id=lambda: next(ids))


def service_with(state: GameState) -> GameService:
    """A service whose only game is `state`, saved under the ID "test"."""
    repository = InMemoryGameRepository()
    repository.save(state)
    return GameService(repository)


def test_create_game_returns_the_new_state() -> None:
    service = make_service()
    state = service.create_game()

    assert (state.game_id, state.current_player, state.status) == ("g1", 1, "active")
    assert state.board == [4] * 12
    assert state.legal_moves == [6, 7, 8, 9, 10, 11]
    assert state.collected == SeedTotalsOut(player_1=0, player_2=0)
    assert (state.move_count, state.moves_without_capture, state.result) == (0, 0, None)
    assert service.get_state("g1") == state


def test_create_game_with_player_2_starting() -> None:
    assert make_service().create_game(starting_player=2).current_player == 2


def test_default_ids_are_unique() -> None:
    service = GameService(InMemoryGameRepository())
    assert service.create_game().game_id != service.create_game().game_id


def test_games_use_the_configured_limits() -> None:
    state = make_service(Limits(max_drops=500, max_moves_without_capture=10)).create_game()
    assert state.limits == LimitsOut(max_drops=500, max_moves_without_capture=10)


def test_list_games() -> None:
    service = make_service()
    first, second = service.create_game(), service.create_game()
    assert service.list_games() == [first, second]


@pytest.mark.parametrize("call", ["get_state", "legal_moves", "history"])
def test_unknown_game_is_reported(call: str) -> None:
    with pytest.raises(GameNotFoundError) as excinfo:
        getattr(make_service(), call)("missing")
    assert excinfo.value.game_id == "missing"


def test_play_move_on_unknown_game_is_reported() -> None:
    with pytest.raises(GameNotFoundError):
        make_service().play_move("missing", 6)


def test_play_move_saves_the_new_state() -> None:
    service = make_service()
    service.create_game()

    result = service.play_move("g1", 6)

    assert service.get_state("g1") == result.state
    assert service.history("g1") == [result.move]
    assert service.legal_moves("g1") == [0, 1, 3, 4, 5]


def test_move_result_describes_the_move() -> None:
    result = service_with(state_with(board_with(p7=1, p2=2, p9=1))).play_move("test", 7)

    assert result.success is True
    move = result.move
    assert (move.move_number, move.player, move.pit, move.seeds_picked_up) == (1, 1, 7, 1)
    assert move.pickups == [PickupOut(pit=7, seeds=1)]
    assert (move.landing_pit, move.opposite_pit, move.captured) == (8, 2, 2)
    assert move.capture_occurred and move.turn_retained
    assert (move.turn_reason, move.status, move.awarded) == ("capture", "active", None)
    assert result.state.move_count == 1


def test_move_that_ends_the_game() -> None:
    service = service_with(state_with(board_with(p7=1, p4=1), moves_without_capture=19))
    result = service.play_move("test", 7)

    assert result.move.turn_reason == "no_capture_limit"
    assert result.move.awarded == SeedTotalsOut(player_1=1, player_2=1)
    assert (result.state.status, result.state.result) == ("completed", "player_1_wins")
    assert (result.state.current_player, result.state.legal_moves) == (None, [])


def test_output_survives_a_json_round_trip() -> None:
    service = make_service()
    state = service.create_game()
    result = service.play_move("g1", 6)
    assert GameStateOut.model_validate_json(state.model_dump_json()) == state
    assert MoveResultOut.model_validate_json(result.model_dump_json()) == result


def test_rejected_move_saves_nothing() -> None:
    service = make_service()
    state = service.create_game()

    with pytest.raises(MoveError) as excinfo:
        service.play_move("g1", 0)

    assert excinfo.value.code is ErrorCode.OPPONENT_PIT
    assert service.get_state("g1") == state


def test_error_out() -> None:
    assert error_out(MoveError(ErrorCode.EMPTY_PIT, "Pit 7 is empty.")) == ErrorOut(
        code="empty_pit", message="Pit 7 is empty."
    )
    assert error_out(GameNotFoundError("missing")) == ErrorOut(
        code="game_not_found", message="Game 'missing' not found."
    )


class SlowRepository(InMemoryGameRepository):
    """Widens the gap between reading and saving a game to expose races."""

    def get(self, game_id: str) -> GameState | None:
        state = super().get(game_id)
        time.sleep(0.02)
        return state


def test_concurrent_moves_on_one_game_are_serialised() -> None:
    service = GameService(SlowRepository(), new_game_id=lambda: "g1")
    service.create_game()
    start = threading.Barrier(4)

    def play() -> bool:
        start.wait()
        try:
            service.play_move("g1", 6)
        except MoveError:
            return False
        return True

    with ThreadPoolExecutor(max_workers=4) as pool:
        outcomes = list(pool.map(lambda _: play(), range(4)))

    assert outcomes.count(True) == 1
    assert len(service.history("g1")) == 1
