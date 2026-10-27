"""In-memory game repository."""

from dataclasses import replace

from gebeta.domain.game import Game
from gebeta.infrastructure.memory_repository import InMemoryGameRepository


def test_unknown_game_is_none() -> None:
    assert InMemoryGameRepository().get("missing") is None


def test_saved_game_can_be_read_back() -> None:
    repository = InMemoryGameRepository()
    state = Game.new("g1").state
    repository.save(state)
    assert repository.get("g1") is state


def test_saving_again_replaces_the_game() -> None:
    repository = InMemoryGameRepository()
    repository.save(Game.new("g1").state)
    updated = replace(Game.new("g1").state, current_player=2)
    repository.save(updated)
    assert repository.get("g1") is updated
    assert repository.list() == (updated,)


def test_list_returns_every_game() -> None:
    repository = InMemoryGameRepository()
    first, second = Game.new("g1").state, Game.new("g2").state
    repository.save(first)
    repository.save(second)
    assert repository.list() == (first, second)
