"""Interfaces the application needs from infrastructure."""

from collections.abc import Sequence
from typing import Protocol

from gebeta.domain.models import GameState


class GameRepository(Protocol):
    """Stores committed game states by game ID."""

    def get(self, game_id: str) -> GameState | None: ...

    def save(self, state: GameState) -> None: ...

    def list(self) -> Sequence[GameState]: ...
