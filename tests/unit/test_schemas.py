"""Wire schemas: request validation and sync with the domain enums."""

from typing import Any, get_args

import pytest
from pydantic import ValidationError

from gebeta.domain.errors import ErrorCode
from gebeta.domain.models import GameResult, GameStatus, TurnReason
from gebeta.schemas import (
    ErrorCodeName,
    NewGameRequest,
    PlayMoveRequest,
    ResultName,
    StatusName,
    TurnReasonName,
)


@pytest.mark.parametrize(
    ("literal", "values"),
    [
        (StatusName, {s.value for s in GameStatus}),
        (ResultName, {r.value for r in GameResult}),
        (TurnReasonName, {t.value for t in TurnReason}),
        (ErrorCodeName, {c.value for c in ErrorCode} | {"game_not_found", "invalid_request"}),
    ],
    ids=["status", "result", "turn-reason", "error-code"],
)
def test_wire_literals_match_domain_enums(literal: Any, values: set[str]) -> None:
    assert set(get_args(literal)) == values


def test_play_move_accepts_an_integer_pit() -> None:
    assert PlayMoveRequest.model_validate({"pit": 7}).pit == 7
    assert PlayMoveRequest.model_validate_json('{"pit": 7}').pit == 7


def test_out_of_range_pit_is_left_to_the_engine() -> None:
    # The engine reports invalid_pit, which is more specific than invalid_request.
    assert PlayMoveRequest.model_validate({"pit": 12}).pit == 12


@pytest.mark.parametrize(
    "payload",
    [{"pit": True}, {"pit": "3"}, {"pit": 3.0}, {"pit": None}, {}, {"pit": 3, "player": 1}],
    ids=["bool", "string", "float", "null", "missing", "extra-field"],
)
def test_malformed_move_requests_are_rejected(payload: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        PlayMoveRequest.model_validate(payload)


def test_malformed_json_pit_is_rejected() -> None:
    with pytest.raises(ValidationError):
        PlayMoveRequest.model_validate_json('{"pit": "3"}')


def test_new_game_defaults_to_player_1() -> None:
    assert NewGameRequest().starting_player == 1
    assert NewGameRequest.model_validate({"starting_player": 2}).starting_player == 2


@pytest.mark.parametrize("player", [0, 3, "1", True])
def test_new_game_rejects_unknown_players(player: object) -> None:
    with pytest.raises(ValidationError):
        NewGameRequest.model_validate({"starting_player": player})
