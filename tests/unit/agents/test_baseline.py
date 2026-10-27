"""Baseline agents, and the greedy prediction checked against the engine."""

import pytest
from hypothesis import given
from hypothesis import strategies as st

from gebeta.agents.baseline import GreedyAgent, RandomAgent, predicted_capture
from gebeta.application.game_service import _state_out
from gebeta.domain.game import Game
from gebeta.schemas import GameStateOut
from tests.fixtures.positions import board_with, state_with

pytestmark = pytest.mark.anyio


def state_out(board: tuple[int, ...], player: int = 1) -> GameStateOut:
    return _state_out(state_with(board, 1 if player == 1 else 2))


async def test_random_agent_picks_a_legal_move_reproducibly() -> None:
    state = state_out((4,) * 12)
    first = [await RandomAgent(seed=7).choose_move(state, state.legal_moves) for _ in range(5)]
    again = [await RandomAgent(seed=7).choose_move(state, state.legal_moves) for _ in range(5)]
    assert first == again
    assert set(first) <= set(state.legal_moves)


async def test_greedy_agent_prefers_the_biggest_capture() -> None:
    # Pit 7 lands in 8 and captures 2 from pit 2; pit 9 lands in 10 and captures 5 from pit 4.
    state = state_out(board_with(p7=1, p2=2, p9=1, p4=5))
    assert await GreedyAgent().choose_move(state, state.legal_moves) == 9


async def test_greedy_agent_breaks_ties_with_the_lowest_pit() -> None:
    state = state_out(board_with(p7=1, p9=1, p0=1))
    assert await GreedyAgent().choose_move(state, state.legal_moves) == 7


def test_prediction_counts_continuation_sowing() -> None:
    # 6 → 7 (now 2 seeds) → continue 8, 9; lands in empty 9, opposite pit 3 has 4.
    assert predicted_capture(board_with(p6=1, p7=1, p3=4), 6, 10_000) == 4


def test_prediction_is_zero_over_the_drop_limit() -> None:
    assert predicted_capture(board_with(p0=13, p8=3), 0, 24) == 0


boards = st.lists(st.integers(0, 6), min_size=12, max_size=12).filter(
    lambda b: any(b[6:]) and sum(b) <= 48
)


@given(board=boards, data=st.data())
def test_prediction_matches_the_engine(board: list[int], data: st.DataObject) -> None:
    game = Game(state_with(tuple(board)))
    moves = game.legal_moves()
    if not moves:
        return
    pit = data.draw(st.sampled_from(moves))
    expected = game.apply_move(pit).record.captured
    assert predicted_capture(board, pit, game.state.limits.max_drops) == expected
