"""Game service use cases and per-game locking."""

import itertools
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import pytest

from gebeta.application.game_service import GameNotFoundError, GameService
from gebeta.domain.errors import ErrorCode, MoveError
from gebeta.domain.models import GameState, GameStatus, Limits
from gebeta.infrastructure.memory_repository import InMemoryGameRepository


def make_service(**kwargs: object) -> GameService:
    ids = (f"g{n}" for n in itertools.count(1))
    return GameService(InMemoryGameRepository(), new_game_id=lambda: next(ids), **kwargs)  # type: ignore[arg-type]


def test_create_game_saves_an_active_game() -> None:
    service = make_service()
    state = service.create_game()

    assert (state.game_id, state.current_player, state.status) == ("g1", 1, GameStatus.ACTIVE)
    assert service.get_state("g1") is state


def test_create_game_with_player_2_starting() -> None:
    assert make_service().create_game(starting_player=2).current_player == 2


def test_default_ids_are_unique() -> None:
    service = GameService(InMemoryGameRepository())
    assert service.create_game().game_id != service.create_game().game_id


def test_games_use_the_configured_limits() -> None:
    limits = Limits(max_drops=500, max_moves_without_capture=10)
    assert make_service(limits=limits).create_game().limits == limits


def test_list_games() -> None:
    service = make_service()
    first, second = service.create_game(), service.create_game()
    assert service.list_games() == (first, second)


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

    assert service.get_state("g1") is result.state
    assert service.history("g1") == (result.record,)
    assert service.legal_moves("g1") == (0, 1, 3, 4, 5)


def test_rejected_move_saves_nothing() -> None:
    service = make_service()
    state = service.create_game()

    with pytest.raises(MoveError) as excinfo:
        service.play_move("g1", 0)

    assert excinfo.value.code is ErrorCode.OPPONENT_PIT
    assert service.get_state("g1") is state


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
