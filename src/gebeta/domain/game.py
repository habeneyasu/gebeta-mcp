"""Game lifecycle: creating games and executing moves (spec §9).

States are immutable, so `apply_move` builds the new state from fresh values
and never changes the state it is given. A rejected move leaves no trace.
"""

from dataclasses import replace

from gebeta.domain import rules
from gebeta.domain.board import (
    DEFAULT_STARTING_PLAYER,
    PIT_COUNT,
    Player,
    initial_board,
    is_valid_pit,
    opponent,
    pit_owner,
)
from gebeta.domain.errors import ErrorCode, MoveError
from gebeta.domain.models import (
    DEFAULT_LIMITS,
    GameState,
    GameStatus,
    Limits,
    MoveRecord,
    MoveResult,
    SeedTotals,
)
from gebeta.domain.sowing import sow


def new_game(
    game_id: str,
    *,
    starting_player: Player = DEFAULT_STARTING_PLAYER,
    limits: Limits = DEFAULT_LIMITS,
) -> GameState:
    return GameState(
        game_id=game_id,
        board=initial_board(),
        current_player=starting_player,
        collected=SeedTotals(),
        status=GameStatus.ACTIVE,
        result=None,
        starting_player=starting_player,
        limits=limits,
    )


def legal_moves(state: GameState) -> tuple[int, ...]:
    if state.current_player is None:
        return ()
    return rules.legal_moves(state.board, state.current_player, state.limits)


def apply_move(state: GameState, pit: int) -> MoveResult:
    """Play `pit` for the current player, or raise `MoveError` (spec §9)."""
    player = _check_move(state, pit)
    sowing = sow(state.board, pit, max_drops=state.limits.max_drops)
    board, captured = rules.capture(sowing.board, sowing.landing_pit)
    collected = state.collected.add(player, captured)
    moves_without_capture = 0 if captured else state.moves_without_capture + 1
    next_player, reason = rules.next_turn(
        board,
        player,
        captured=captured,
        moves_without_capture=moves_without_capture,
        limits=state.limits,
    )

    awarded = None
    if next_player is None:
        awarded = rules.remaining_seeds(board)
        collected += awarded
        board = (0,) * PIT_COUNT
    status = GameStatus.COMPLETED if next_player is None else GameStatus.ACTIVE

    record = MoveRecord(
        move_number=len(state.history) + 1,
        player=player,
        sowing=sowing,
        captured=captured,
        awarded=awarded,
        collected=collected,
        next_player=next_player,
        turn_reason=reason,
        status=status,
    )
    committed = replace(
        state,
        board=board,
        current_player=next_player,
        collected=collected,
        status=status,
        result=None if awarded is None else rules.result(collected),
        history=(*state.history, record),
        moves_without_capture=moves_without_capture,
    )
    return MoveResult(record=record, state=committed)


def _check_move(state: GameState, pit: int) -> Player:
    """The current player, if they may select `pit` (spec §2, §10)."""
    player = state.current_player
    if state.status is GameStatus.COMPLETED or player is None:
        raise MoveError(ErrorCode.GAME_OVER, "The game has ended.")
    if not is_valid_pit(pit):
        raise MoveError(ErrorCode.INVALID_PIT, f"Pit {pit!r} is not between 0 and 11.")
    if pit_owner(pit) != player:
        raise MoveError(ErrorCode.OPPONENT_PIT, f"Pit {pit} belongs to player {opponent(player)}.")
    if state.board[pit] == 0:
        raise MoveError(ErrorCode.EMPTY_PIT, f"Pit {pit} is empty.")
    return player
