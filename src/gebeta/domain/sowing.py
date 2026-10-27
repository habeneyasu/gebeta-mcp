"""Sowing with continuation, cycle detection, and the seed-drop cap (spec §4, §5).

`sow` never modifies the board it is given, so a rejected move leaves the
game state untouched (spec §5.1).
"""

from collections.abc import Sequence

from gebeta.domain.board import PIT_COUNT, is_valid_pit, next_pit
from gebeta.domain.errors import ErrorCode, MoveError
from gebeta.domain.models import DEFAULT_MAX_DROPS, Pickup, Sowing


def sow(board: Sequence[int], pit: int, *, max_drops: int = DEFAULT_MAX_DROPS) -> Sowing:
    """Sow from `pit` until the final seed lands in an empty pit.

    `pit` must be a valid, non-empty pit; ownership and game status are the
    caller's concern. Raises `MoveError` with `sowing_cycle` when a
    (board, landing pit) state repeats before a continuation pickup, or with
    `sowing_limit_exceeded` when the move would place more than `max_drops`
    seeds.
    """
    if len(board) != PIT_COUNT:
        raise ValueError(f"Board must have {PIT_COUNT} pits, got {len(board)}.")
    if not is_valid_pit(pit) or board[pit] == 0:
        raise ValueError(f"Pit {pit!r} is not a valid, non-empty pit.")
    if max_drops < 1:
        raise ValueError(f"max_drops must be at least 1, got {max_drops}.")

    pits = list(board)
    pickups: list[Pickup] = []
    seen: set[tuple[tuple[int, ...], int]] = set()
    drops = 0
    current = pit

    while True:
        hand = pits[current]
        drops += hand
        if drops > max_drops:
            raise MoveError(
                ErrorCode.SOWING_LIMIT_EXCEEDED,
                f"Move from pit {pit} places more than {max_drops} seeds.",
            )
        pits[current] = 0
        pickups.append(Pickup(current, hand))
        for _ in range(hand):
            current = next_pit(current)
            pits[current] += 1

        if pits[current] == 1:
            return Sowing(board=tuple(pits), pickups=tuple(pickups), landing_pit=current)

        state = (tuple(pits), current)
        if state in seen:
            raise MoveError(ErrorCode.SOWING_CYCLE, f"Move from pit {pit} enters a sowing cycle.")
        seen.add(state)
