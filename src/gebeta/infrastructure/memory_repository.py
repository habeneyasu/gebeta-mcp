"""In-process game storage behind the `GameRepository` port.

Games are lost on restart and are not shared between processes, so run a
single worker.
"""

from collections.abc import Sequence

from gebeta.domain.models import GameState


class InMemoryGameRepository:
    def __init__(self) -> None:
        self._games: dict[str, GameState] = {}

    def get(self, game_id: str) -> GameState | None:
        return self._games.get(game_id)

    def save(self, state: GameState) -> None:
        self._games[state.game_id] = state

    def list(self) -> Sequence[GameState]:
        return tuple(self._games.values())
