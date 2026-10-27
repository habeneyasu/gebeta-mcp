"""Sowing properties over arbitrary boards (spec §4, §5, §13)."""

from hypothesis import given
from hypothesis import strategies as st

from gebeta.domain.board import PIT_COUNT, next_pit
from gebeta.domain.errors import ErrorCode, MoveError
from gebeta.domain.models import Sowing
from gebeta.domain.sowing import sow

boards = st.lists(st.integers(0, 8), min_size=PIT_COUNT, max_size=PIT_COUNT).filter(any)


def sow_or_none(board: list[int], pit: int) -> Sowing | None:
    """The sowing, or None for a rejected looping or over-limit move."""
    try:
        return sow(board, pit)
    except MoveError as error:
        assert error.code in {ErrorCode.SOWING_CYCLE, ErrorCode.SOWING_LIMIT_EXCEEDED}
        return None


def lap_end(pit: int, seeds: int) -> int:
    for _ in range(seeds):
        pit = next_pit(pit)
    return pit


@given(board=boards, data=st.data())
def test_sowing_conserves_seeds_and_ends_in_single_seed_pit(
    board: list[int], data: st.DataObject
) -> None:
    pit = data.draw(st.sampled_from([i for i, seeds in enumerate(board) if seeds]))
    sowing = sow_or_none(board, pit)
    if sowing is None:
        return

    assert sum(sowing.board) == sum(board)
    assert sowing.board[sowing.landing_pit] == 1
    assert sowing.pickups[0].pit == pit
    assert sowing.pickups[0].seeds == board[pit]


@given(board=boards, data=st.data())
def test_each_continuation_starts_where_the_previous_lap_ended(
    board: list[int], data: st.DataObject
) -> None:
    pit = data.draw(st.sampled_from([i for i, seeds in enumerate(board) if seeds]))
    sowing = sow_or_none(board, pit)
    if sowing is None:
        return

    laps = sowing.pickups
    for previous, following in zip(laps, laps[1:], strict=False):
        assert following.pit == lap_end(previous.pit, previous.seeds)
    assert sowing.landing_pit == lap_end(laps[-1].pit, laps[-1].seeds)


@given(board=boards, data=st.data())
def test_sowing_is_deterministic_and_leaves_input_unchanged(
    board: list[int], data: st.DataObject
) -> None:
    pit = data.draw(st.sampled_from([i for i, seeds in enumerate(board) if seeds]))
    original = list(board)

    assert sow_or_none(board, pit) == sow_or_none(board, pit)
    assert board == original
