"""Board geometry: pit indices, ownership, and traversal (spec §1–§3, §6).

Pit index functions assume a valid index; callers validate with
`is_valid_pit` first, as required by spec §15.
"""

from collections.abc import Mapping
from typing import Final, Literal

Player = Literal[1, 2]

PIT_COUNT: Final = 12
SEEDS_PER_PIT: Final = 4
TOTAL_SEEDS: Final = PIT_COUNT * SEEDS_PER_PIT
PLAYERS: Final[tuple[Player, Player]] = (1, 2)
DEFAULT_STARTING_PLAYER: Final[Player] = 1
OWNED_PITS: Final[Mapping[Player, range]] = {1: range(6, 12), 2: range(0, 6)}


def initial_board() -> tuple[int, ...]:
    return (SEEDS_PER_PIT,) * PIT_COUNT


def is_valid_pit(index: object) -> bool:
    """True for an int (not bool) in the range 0–11."""
    return isinstance(index, int) and not isinstance(index, bool) and 0 <= index < PIT_COUNT


def next_pit(index: int) -> int:
    return (index + 1) % PIT_COUNT


def opposite_pit(index: int) -> int:
    return (index + 6) % PIT_COUNT


def pit_owner(index: int) -> Player:
    return 1 if index in OWNED_PITS[1] else 2


def opponent(player: Player) -> Player:
    return 2 if player == 1 else 1
