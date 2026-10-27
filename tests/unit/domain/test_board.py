"""Board geometry acceptance tests (spec §18, criteria 1–7)."""

import pytest

from gebeta.domain.board import (
    DEFAULT_STARTING_PLAYER,
    OWNED_PITS,
    PIT_COUNT,
    TOTAL_SEEDS,
    initial_board,
    is_valid_pit,
    next_pit,
    opponent,
    opposite_pit,
    pit_owner,
)


def test_initial_board_has_twelve_pits_of_four_seeds() -> None:
    assert initial_board() == (4,) * 12


def test_initial_total_is_48_seeds() -> None:
    assert sum(initial_board()) == TOTAL_SEEDS == 48


def test_player_1_starts_by_default() -> None:
    assert DEFAULT_STARTING_PLAYER == 1


@pytest.mark.parametrize("pit", range(6, 12))
def test_player_1_owns_pits_6_to_11(pit: int) -> None:
    assert pit_owner(pit) == 1


@pytest.mark.parametrize("pit", range(0, 6))
def test_player_2_owns_pits_0_to_5(pit: int) -> None:
    assert pit_owner(pit) == 2


def test_ownership_covers_every_pit_exactly_once() -> None:
    assert sorted([*OWNED_PITS[1], *OWNED_PITS[2]]) == list(range(PIT_COUNT))


@pytest.mark.parametrize("pit", range(12))
def test_pits_0_to_11_are_valid(pit: int) -> None:
    assert is_valid_pit(pit)


@pytest.mark.parametrize("value", [-1, 12, 100, True, False, 1.0, "3", None])
def test_out_of_range_and_non_integer_pits_are_invalid(value: object) -> None:
    assert not is_valid_pit(value)


@pytest.mark.parametrize("pit", range(11))
def test_next_pit_follows_circular_sequence(pit: int) -> None:
    assert next_pit(pit) == pit + 1


def test_pit_11_wraps_to_pit_0() -> None:
    assert next_pit(11) == 0


def test_twelve_steps_return_to_start() -> None:
    pit = 5
    for _ in range(PIT_COUNT):
        pit = next_pit(pit)
    assert pit == 5


@pytest.mark.parametrize(
    ("pit", "expected"),
    [(0, 6), (1, 7), (2, 8), (3, 9), (4, 10), (5, 11),
     (6, 0), (7, 1), (8, 2), (9, 3), (10, 4), (11, 5)],
)  # fmt: skip
def test_opposite_pit_pairs_match_spec_table(pit: int, expected: int) -> None:
    assert opposite_pit(pit) == expected


@pytest.mark.parametrize("pit", range(12))
def test_opposite_pit_is_symmetrical(pit: int) -> None:
    assert opposite_pit(opposite_pit(pit)) == pit
    assert opposite_pit(pit) != pit


def test_opponent() -> None:
    assert opponent(1) == 2
    assert opponent(2) == 1
