"""Use cases for playing Gebeta: the only entry point to the domain.

The REST API and the MCP server share one `GameService`, which returns the
wire schemas from `gebeta.schemas`. Moves on the same game are serialised by a
per-game lock, so two concurrent requests cannot both play from the same state.
"""

import threading
import uuid
from collections.abc import Callable

from gebeta.application.ports import GameRepository
from gebeta.domain.board import DEFAULT_STARTING_PLAYER, Player
from gebeta.domain.errors import MoveError
from gebeta.domain.game import Game
from gebeta.domain.models import (
    DEFAULT_LIMITS,
    GameState,
    Limits,
    MoveRecord,
    MoveResult,
    SeedTotals,
)
from gebeta.schemas import (
    ErrorOut,
    GameStateOut,
    LimitsOut,
    MoveRecordOut,
    MoveResultOut,
    PickupOut,
    SeedTotalsOut,
)


class GameNotFoundError(Exception):
    def __init__(self, game_id: str) -> None:
        super().__init__(f"Game {game_id!r} not found.")
        self.game_id = game_id


def _new_game_id() -> str:
    return uuid.uuid4().hex


class GameService:
    def __init__(
        self,
        repository: GameRepository,
        *,
        limits: Limits = DEFAULT_LIMITS,
        new_game_id: Callable[[], str] = _new_game_id,
    ) -> None:
        self._repository = repository
        self._limits = limits
        self._new_game_id = new_game_id
        self._locks: dict[str, threading.Lock] = {}
        self._locks_guard = threading.Lock()

    def create_game(self, starting_player: Player = DEFAULT_STARTING_PLAYER) -> GameStateOut:
        game = Game.new(self._new_game_id(), starting_player=starting_player, limits=self._limits)
        self._repository.save(game.state)
        return _state_out(game.state)

    def get_state(self, game_id: str) -> GameStateOut:
        return _state_out(self._load(game_id))

    def list_games(self) -> list[GameStateOut]:
        return [_state_out(state) for state in self._repository.list()]

    def legal_moves(self, game_id: str) -> list[int]:
        return list(Game(self._load(game_id)).legal_moves())

    def history(self, game_id: str) -> list[MoveRecordOut]:
        return [_record_out(record) for record in self._load(game_id).history]

    def play_move(self, game_id: str, pit: int) -> MoveResultOut:
        """Apply a move and save the new state; raises `MoveError` if rejected."""
        with self._lock_for(game_id):
            game = Game(self._load(game_id))
            result = game.apply_move(pit)
            self._repository.save(game.state)
        return _result_out(result)

    def _load(self, game_id: str) -> GameState:
        state = self._repository.get(game_id)
        if state is None:
            raise GameNotFoundError(game_id)
        return state

    def _lock_for(self, game_id: str) -> threading.Lock:
        with self._locks_guard:
            return self._locks.setdefault(game_id, threading.Lock())


def error_out(error: MoveError | GameNotFoundError) -> ErrorOut:
    if isinstance(error, GameNotFoundError):
        return ErrorOut(code="game_not_found", message=str(error))
    return ErrorOut(code=error.code.value, message=error.message)


# Domain → wire conversion. mypy checks that each domain enum value is one of
# the matching `schemas` literals, so the two cannot drift apart.


def _totals_out(totals: SeedTotals) -> SeedTotalsOut:
    return SeedTotalsOut(player_1=totals.player_1, player_2=totals.player_2)


def _state_out(state: GameState) -> GameStateOut:
    return GameStateOut(
        game_id=state.game_id,
        board=list(state.board),
        current_player=state.current_player,
        legal_moves=list(Game(state).legal_moves()),
        collected=_totals_out(state.collected),
        status=state.status.value,
        result=None if state.result is None else state.result.value,
        starting_player=state.starting_player,
        move_count=len(state.history),
        moves_without_capture=state.moves_without_capture,
        limits=LimitsOut(
            max_drops=state.limits.max_drops,
            max_moves_without_capture=state.limits.max_moves_without_capture,
        ),
    )


def _record_out(record: MoveRecord) -> MoveRecordOut:
    return MoveRecordOut(
        move_number=record.move_number,
        player=record.player,
        pit=record.pit,
        seeds_picked_up=record.sowing.seeds_picked_up,
        pickups=[PickupOut(pit=p.pit, seeds=p.seeds) for p in record.sowing.pickups],
        drops=record.sowing.drops,
        landing_pit=record.landing_pit,
        opposite_pit=record.opposite_pit,
        captured=record.captured,
        capture_occurred=record.capture_occurred,
        awarded=None if record.awarded is None else _totals_out(record.awarded),
        collected=_totals_out(record.collected),
        next_player=record.next_player,
        turn_retained=record.turn_retained,
        turn_reason=record.turn_reason.value,
        status=record.status.value,
    )


def _result_out(result: MoveResult) -> MoveResultOut:
    return MoveResultOut(move=_record_out(result.record), state=_state_out(result.state))
