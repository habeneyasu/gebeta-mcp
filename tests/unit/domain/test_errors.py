"""Error codes for rejected moves and engine errors (spec §5.1, §10)."""

import pytest

from gebeta.domain.errors import ErrorCode, MoveError


def test_error_codes_match_wire_names() -> None:
    assert {code.value for code in ErrorCode} == {
        "invalid_pit",
        "empty_pit",
        "opponent_pit",
        "game_over",
        "sowing_cycle",
        "sowing_limit_exceeded",
    }


def test_error_codes_compare_equal_to_strings() -> None:
    assert ErrorCode.SOWING_CYCLE == "sowing_cycle"


def test_move_error_carries_code_and_message() -> None:
    with pytest.raises(MoveError) as excinfo:
        raise MoveError(ErrorCode.EMPTY_PIT, "Pit 7 is empty.")
    assert excinfo.value.code is ErrorCode.EMPTY_PIT
    assert excinfo.value.message == "Pit 7 is empty."
    assert str(excinfo.value) == "Pit 7 is empty."
