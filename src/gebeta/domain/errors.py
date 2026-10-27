"""Move rejections and engine errors (spec §5.1, §10).

Unknown game IDs and malformed requests are reported by the application
and schema layers, not the domain.
"""

from enum import StrEnum


class ErrorCode(StrEnum):
    INVALID_PIT = "invalid_pit"
    EMPTY_PIT = "empty_pit"
    OPPONENT_PIT = "opponent_pit"
    GAME_OVER = "game_over"
    SOWING_CYCLE = "sowing_cycle"
    SOWING_LIMIT_EXCEEDED = "sowing_limit_exceeded"


class MoveError(Exception):
    """A move that was not applied. The game state is unchanged."""

    def __init__(self, code: ErrorCode, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
