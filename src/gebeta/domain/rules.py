"""Legal moves, capture, turn order, and game end (spec §7–§12)."""

from collections.abc import Sequence

from gebeta.domain.board import OWNED_PITS, Player, opponent, opposite_pit
from gebeta.domain.errors import MoveError
from gebeta.domain.models import GameResult, Limits, SeedTotals, TurnReason
from gebeta.domain.sowing import sow


def legal_moves(board: Sequence[int], player: Player, limits: Limits) -> tuple[int, ...]:
    """Non-empty pits of `player` whose move neither loops nor exceeds the drop limit."""
    return tuple(pit for pit in OWNED_PITS[player] if _is_legal(board, pit, limits))


def has_legal_move(board: Sequence[int], player: Player, limits: Limits) -> bool:
    return any(_is_legal(board, pit, limits) for pit in OWNED_PITS[player])


def _is_legal(board: Sequence[int], pit: int, limits: Limits) -> bool:
    if board[pit] == 0:
        return False
    try:
        sow(board, pit, max_drops=limits.max_drops)
    except MoveError:
        return False
    return True


def capture(board: tuple[int, ...], landing_pit: int) -> tuple[tuple[int, ...], int]:
    """Take every seed from the pit opposite `landing_pit` (spec §7, §8).

    Returns the new board and the number of seeds captured. The seed in the
    landing pit stays where it is.
    """
    opposite = opposite_pit(landing_pit)
    seeds = board[opposite]
    if seeds == 0:
        return board, 0
    pits = list(board)
    pits[opposite] = 0
    return tuple(pits), seeds


def next_turn(
    board: Sequence[int],
    player: Player,
    *,
    captured: int,
    moves_without_capture: int,
    limits: Limits,
) -> tuple[Player | None, TurnReason]:
    """The player who moves next, or None when the game ends (spec §11)."""
    if moves_without_capture >= limits.max_moves_without_capture:
        return None, TurnReason.NO_CAPTURE_LIMIT
    mine = has_legal_move(board, player, limits)
    theirs = has_legal_move(board, opponent(player), limits)
    if not mine and not theirs:
        return None, TurnReason.NO_LEGAL_MOVES
    if captured and mine:
        return player, TurnReason.CAPTURE
    if theirs:
        return opponent(player), TurnReason.TURN_PASSES
    return player, TurnReason.OPPONENT_HAS_NO_MOVE


def remaining_seeds(board: Sequence[int]) -> SeedTotals:
    """Seeds left in each player's row, awarded to that player at game end (spec §11.2)."""
    return SeedTotals(
        player_1=sum(board[pit] for pit in OWNED_PITS[1]),
        player_2=sum(board[pit] for pit in OWNED_PITS[2]),
    )


def result(collected: SeedTotals) -> GameResult:
    """The winner by collected seeds, or a draw (spec §12)."""
    if collected[1] > collected[2]:
        return GameResult.PLAYER_1_WINS
    if collected[2] > collected[1]:
        return GameResult.PLAYER_2_WINS
    return GameResult.DRAW
