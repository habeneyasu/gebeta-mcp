"""Converts domain values into the wire schemas, for the API and MCP server.

mypy checks that each domain enum value is one of the matching `schemas`
literals, so the two cannot drift apart.
"""

from gebeta.application.game_service import GameNotFoundError
from gebeta.domain.errors import MoveError
from gebeta.domain.game import legal_moves
from gebeta.domain.models import GameState, MoveRecord, MoveResult, SeedTotals
from gebeta.schemas import (
    ErrorOut,
    GameStateOut,
    LimitsOut,
    MoveRecordOut,
    MoveResultOut,
    PickupOut,
    SeedTotalsOut,
)


def seed_totals_out(totals: SeedTotals) -> SeedTotalsOut:
    return SeedTotalsOut(player_1=totals.player_1, player_2=totals.player_2)


def game_state_out(state: GameState) -> GameStateOut:
    return GameStateOut(
        game_id=state.game_id,
        board=list(state.board),
        current_player=state.current_player,
        legal_moves=list(legal_moves(state)),
        collected=seed_totals_out(state.collected),
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


def move_record_out(record: MoveRecord) -> MoveRecordOut:
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
        awarded=None if record.awarded is None else seed_totals_out(record.awarded),
        collected=seed_totals_out(record.collected),
        next_player=record.next_player,
        turn_retained=record.turn_retained,
        turn_reason=record.turn_reason.value,
        status=record.status.value,
    )


def move_result_out(result: MoveResult) -> MoveResultOut:
    return MoveResultOut(move=move_record_out(result.record), state=game_state_out(result.state))


def error_out(error: MoveError | GameNotFoundError) -> ErrorOut:
    if isinstance(error, GameNotFoundError):
        return ErrorOut(code="game_not_found", message=str(error))
    return ErrorOut(code=error.code.value, message=error.message)
