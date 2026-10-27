"""Wire contract shared by the REST API, the MCP server, and the MCP client.

This module must not import `gebeta.domain`: the MCP client depends on it and
may reach the game only through MCP (spec §17). Enumerated values are string
literals kept in sync with the domain enums by tests; `gebeta.mapping`
converts domain values into these models.
"""

from typing import Annotated, Literal

from pydantic import BaseModel, BeforeValidator, ConfigDict

PlayerNumber = Literal[1, 2]
StatusName = Literal["active", "completed"]
ResultName = Literal["player_1_wins", "player_2_wins", "draw"]
TurnReasonName = Literal[
    "capture", "turn_passes", "opponent_has_no_move", "no_legal_moves", "no_capture_limit"
]
ErrorCodeName = Literal[
    "invalid_pit",
    "empty_pit",
    "opponent_pit",
    "game_over",
    "sowing_cycle",
    "sowing_limit_exceeded",
    "game_not_found",
    "invalid_request",
]


class Request(BaseModel):
    """Strict input: `true`, `"3"`, or `3.0` is not a pit (spec §10, malformed requests)."""

    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)


class Response(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


def _reject_bool(value: object) -> object:
    # Literal[1, 2] accepts True because True == 1, even in strict mode.
    if isinstance(value, bool):
        raise ValueError("Player must be 1 or 2, not a boolean.")
    return value


class NewGameRequest(Request):
    starting_player: Annotated[PlayerNumber, BeforeValidator(_reject_bool)] = 1


class PlayMoveRequest(Request):
    pit: int


class SeedTotalsOut(Response):
    player_1: int
    player_2: int


class LimitsOut(Response):
    max_drops: int
    max_moves_without_capture: int


class PickupOut(Response):
    pit: int
    seeds: int


class MoveRecordOut(Response):
    """One valid move (spec §14). `pickups[0]` is the selected pit."""

    move_number: int
    player: PlayerNumber
    pit: int
    seeds_picked_up: int
    pickups: list[PickupOut]
    drops: int
    landing_pit: int
    opposite_pit: int
    captured: int
    capture_occurred: bool
    awarded: SeedTotalsOut | None
    collected: SeedTotalsOut
    next_player: PlayerNumber | None
    turn_retained: bool
    turn_reason: TurnReasonName
    status: StatusName


class GameStateOut(Response):
    """The game as clients see it (spec §13), with the current legal moves."""

    game_id: str
    board: list[int]
    current_player: PlayerNumber | None
    legal_moves: list[int]
    collected: SeedTotalsOut
    status: StatusName
    result: ResultName | None
    starting_player: PlayerNumber
    move_count: int
    moves_without_capture: int
    limits: LimitsOut


class MoveResultOut(Response):
    """A successful move. Rejected moves return `ErrorOut` instead."""

    success: Literal[True] = True
    move: MoveRecordOut
    state: GameStateOut


class ErrorOut(Response):
    code: ErrorCodeName
    message: str
