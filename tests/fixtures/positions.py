"""Named board positions and builders shared by tests."""

from gebeta.domain.board import PIT_COUNT, TOTAL_SEEDS, Player
from gebeta.domain.models import DEFAULT_LIMITS, GameState, GameStatus, Limits, SeedTotals

# Pit 6 enters a sowing cycle; every other non-empty pit sows normally.
LOOPING_BOARD = (1, 0, 2, 1, 0, 1, 2, 0, 1, 0, 1, 0)
LOOPING_PIT = 6


def board_with(**pits: int) -> tuple[int, ...]:
    """A board that is empty except for the given pits, e.g. board_with(p6=2)."""
    board = [0] * PIT_COUNT
    for name, seeds in pits.items():
        board[int(name.removeprefix("p"))] = seeds
    return tuple(board)


def state_with(
    board: tuple[int, ...],
    current_player: Player = 1,
    *,
    moves_without_capture: int = 0,
    limits: Limits = DEFAULT_LIMITS,
) -> GameState:
    """An active game on `board`; seeds not on the board count as captured by player 1."""
    return GameState(
        game_id="test",
        board=board,
        current_player=current_player,
        collected=SeedTotals(TOTAL_SEEDS - sum(board), 0),
        status=GameStatus.ACTIVE,
        result=None,
        starting_player=1,
        moves_without_capture=moves_without_capture,
        limits=limits,
    )
