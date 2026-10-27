"""Game services preloaded with test positions."""

import itertools

from gebeta.application.game_service import GameService
from gebeta.domain.models import GameState
from gebeta.infrastructure.memory_repository import InMemoryGameRepository


def service_with(*states: GameState) -> GameService:
    """A service whose repository already holds `states`, with IDs g1, g2, … for new games."""
    repository = InMemoryGameRepository()
    for state in states:
        repository.save(state)
    ids = (f"g{n}" for n in itertools.count(1))
    return GameService(repository, new_game_id=lambda: next(ids))
