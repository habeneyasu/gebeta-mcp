"""Baseline agents: a seedable random player and a greedy capturer."""

import random
from collections.abc import Sequence

from gebeta.schemas import GameStateOut

PIT_COUNT = 12


class RandomAgent:
    def __init__(self, seed: int | None = None, name: str = "random") -> None:
        self.name = name
        self._rng = random.Random(seed)

    async def choose_move(self, state: GameStateOut, legal_moves: list[int]) -> int:
        return self._rng.choice(legal_moves)


class GreedyAgent:
    """Chooses the legal move capturing the most seeds immediately; ties go to the lowest pit."""

    def __init__(self, name: str = "greedy") -> None:
        self.name = name

    async def choose_move(self, state: GameStateOut, legal_moves: list[int]) -> int:
        max_drops = state.limits.max_drops
        return max(
            legal_moves, key=lambda pit: (predicted_capture(state.board, pit, max_drops), -pit)
        )


def predicted_capture(board: Sequence[int], pit: int, max_drops: int) -> int:
    """Seeds a move from `pit` would capture, by local simulation of sowing (spec §4–§7).

    This only ranks moves: the engine alone decides the real result, and tests
    check that this prediction matches it. Returns 0 for a move that would
    exceed `max_drops`, which the engine excludes from legal moves anyway.
    """
    pits = list(board)
    current = pit
    drops = 0
    while True:
        hand = pits[current]
        drops += hand
        if drops > max_drops:
            return 0
        pits[current] = 0
        for _ in range(hand):
            current = (current + 1) % PIT_COUNT
            pits[current] += 1
        if pits[current] == 1:
            return pits[(current + PIT_COUNT // 2) % PIT_COUNT]
