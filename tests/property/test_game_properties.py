"""Whole-game properties under random play (spec §13, §18 criteria 31, 34–35)."""

import random

from hypothesis import given, settings
from hypothesis import strategies as st

from gebeta.domain.board import TOTAL_SEEDS
from gebeta.domain.errors import MoveError
from gebeta.domain.game import apply_move, legal_moves, new_game
from gebeta.domain.models import GameStatus

MAX_MOVES = 1_000


@settings(max_examples=30, deadline=None)
@given(rng=st.randoms(use_true_random=False), starting_player=st.sampled_from([1, 2]))
def test_random_games_end_with_48_seeds_and_rejections_change_nothing(
    rng: random.Random, starting_player: int
) -> None:
    state = new_game("p", starting_player=1 if starting_player == 1 else 2)

    for _ in range(MAX_MOVES):
        if state.status is GameStatus.COMPLETED:
            break
        assert sum(state.board) + state.collected.total == TOTAL_SEEDS

        moves = legal_moves(state)
        assert moves, "an active game always offers the current player a move"
        illegal = [pit for pit in range(-1, 13) if pit not in moves]
        before = state
        try:
            apply_move(state, rng.choice(illegal))
        except MoveError:
            pass
        else:
            raise AssertionError("a pit outside legal_moves was accepted")
        assert state == before

        state = apply_move(state, rng.choice(moves)).state

    assert state.status is GameStatus.COMPLETED
    assert state.board == (0,) * 12
    assert state.collected.total == TOTAL_SEEDS
