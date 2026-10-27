"""Use cases for playing Gebeta: the only entry point to the domain.

The REST API and the MCP server share one `GameService`. Moves on the same
game are serialised by a per-game lock, so two concurrent requests cannot
both play from the same state.
"""

import threading
import uuid
from collections.abc import Callable, Sequence

from gebeta.application.ports import GameRepository
from gebeta.domain import game
from gebeta.domain.board import DEFAULT_STARTING_PLAYER, Player
from gebeta.domain.models import DEFAULT_LIMITS, GameState, Limits, MoveRecord, MoveResult


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

    def create_game(self, starting_player: Player = DEFAULT_STARTING_PLAYER) -> GameState:
        state = game.new_game(
            self._new_game_id(), starting_player=starting_player, limits=self._limits
        )
        self._repository.save(state)
        return state

    def get_state(self, game_id: str) -> GameState:
        state = self._repository.get(game_id)
        if state is None:
            raise GameNotFoundError(game_id)
        return state

    def list_games(self) -> Sequence[GameState]:
        return self._repository.list()

    def legal_moves(self, game_id: str) -> tuple[int, ...]:
        return game.legal_moves(self.get_state(game_id))

    def history(self, game_id: str) -> tuple[MoveRecord, ...]:
        return self.get_state(game_id).history

    def play_move(self, game_id: str, pit: int) -> MoveResult:
        """Apply a move and save the new state; raises `MoveError` if rejected."""
        with self._lock_for(game_id):
            result = game.apply_move(self.get_state(game_id), pit)
            self._repository.save(result.state)
        return result

    def _lock_for(self, game_id: str) -> threading.Lock:
        with self._locks_guard:
            return self._locks.setdefault(game_id, threading.Lock())
