"""Immutable values the engine returns (spec §13, §14).

The domain uses frozen dataclasses; `gebeta.schemas` handles validation and
serialisation at the edges.
"""

from dataclasses import dataclass, replace
from enum import StrEnum
from typing import Final, Self

from gebeta.domain.board import PIT_COUNT, TOTAL_SEEDS, Player, opposite_pit

DEFAULT_MAX_DROPS: Final = 10_000
DEFAULT_MAX_MOVES_WITHOUT_CAPTURE: Final = 20


class GameStatus(StrEnum):
    ACTIVE = "active"
    COMPLETED = "completed"


class GameResult(StrEnum):
    PLAYER_1_WINS = "player_1_wins"
    PLAYER_2_WINS = "player_2_wins"
    DRAW = "draw"


class TurnReason(StrEnum):
    """Why the next player was chosen, or why the game ended (spec §11)."""

    CAPTURE = "capture"
    TURN_PASSES = "turn_passes"
    OPPONENT_HAS_NO_MOVE = "opponent_has_no_move"
    NO_LEGAL_MOVES = "no_legal_moves"
    NO_CAPTURE_LIMIT = "no_capture_limit"


@dataclass(frozen=True, slots=True)
class Limits:
    """Configurable rule limits (spec §5.1, §11.2), fixed when a game is created."""

    max_drops: int = DEFAULT_MAX_DROPS
    max_moves_without_capture: int = DEFAULT_MAX_MOVES_WITHOUT_CAPTURE

    def __post_init__(self) -> None:
        if self.max_drops < 1 or self.max_moves_without_capture < 1:
            raise ValueError(f"Limits must be at least 1: {self}.")


DEFAULT_LIMITS: Final = Limits()


@dataclass(frozen=True, slots=True)
class SeedTotals:
    """Seeds per player, indexed by player number: `totals[1]`, `totals[2]`."""

    player_1: int = 0
    player_2: int = 0

    def __post_init__(self) -> None:
        if self.player_1 < 0 or self.player_2 < 0:
            raise ValueError(f"Seed totals cannot be negative: {self}.")

    def __getitem__(self, player: Player) -> int:
        return self.player_1 if player == 1 else self.player_2

    def add(self, player: Player, seeds: int) -> Self:
        if player == 1:
            return replace(self, player_1=self.player_1 + seeds)
        return replace(self, player_2=self.player_2 + seeds)

    def __add__(self, other: "SeedTotals") -> Self:
        return replace(
            self, player_1=self.player_1 + other.player_1, player_2=self.player_2 + other.player_2
        )

    @property
    def total(self) -> int:
        return self.player_1 + self.player_2


@dataclass(frozen=True, slots=True)
class Pickup:
    """Seeds lifted from `pit` and sown one at a time from the next pit."""

    pit: int
    seeds: int


@dataclass(frozen=True, slots=True)
class Sowing:
    """A completed sowing (spec §4, §5).

    The first pickup is the selected pit; any others are continuation pickups.
    `board` is the board after the final seed is placed, before any capture.
    """

    board: tuple[int, ...]
    pickups: tuple[Pickup, ...]
    landing_pit: int

    @property
    def pit(self) -> int:
        return self.pickups[0].pit

    @property
    def seeds_picked_up(self) -> int:
        return self.pickups[0].seeds

    @property
    def drops(self) -> int:
        return sum(pickup.seeds for pickup in self.pickups)


@dataclass(frozen=True, slots=True)
class MoveRecord:
    """One valid move in the history (spec §14).

    `awarded` holds the remaining seeds given to each player when this move
    ended the game, and is None otherwise.
    """

    move_number: int
    player: Player
    sowing: Sowing
    captured: int
    awarded: SeedTotals | None
    collected: SeedTotals
    next_player: Player | None
    turn_reason: TurnReason
    status: GameStatus

    @property
    def pit(self) -> int:
        return self.sowing.pit

    @property
    def landing_pit(self) -> int:
        return self.sowing.landing_pit

    @property
    def opposite_pit(self) -> int:
        return opposite_pit(self.sowing.landing_pit)

    @property
    def capture_occurred(self) -> bool:
        return self.captured > 0

    @property
    def turn_retained(self) -> bool:
        return self.next_player == self.player


@dataclass(frozen=True, slots=True)
class GameState:
    """Authoritative game state (spec §13).

    Construction enforces the seed-count invariant and a consistent status,
    so an invalid state cannot be committed.
    """

    game_id: str
    board: tuple[int, ...]
    current_player: Player | None
    collected: SeedTotals
    status: GameStatus
    result: GameResult | None
    starting_player: Player
    history: tuple[MoveRecord, ...] = ()
    moves_without_capture: int = 0
    limits: Limits = DEFAULT_LIMITS

    def __post_init__(self) -> None:
        if self.moves_without_capture < 0:
            raise ValueError("moves_without_capture cannot be negative.")
        if len(self.board) != PIT_COUNT:
            raise ValueError(f"Board must have {PIT_COUNT} pits, got {len(self.board)}.")
        if any(seeds < 0 for seeds in self.board):
            raise ValueError(f"Pit seed counts cannot be negative: {self.board}.")
        seeds = sum(self.board) + self.collected.total
        if seeds != TOTAL_SEEDS:
            raise ValueError(f"Seed count is {seeds}, expected {TOTAL_SEEDS}.")
        if self.status is GameStatus.ACTIVE:
            if self.current_player is None or self.result is not None:
                raise ValueError("An active game needs a current player and no result.")
        elif self.current_player is not None or self.result is None or any(self.board):
            raise ValueError("A completed game needs empty pits, a result, and no current player.")


@dataclass(frozen=True, slots=True)
class MoveResult:
    """A successful move: its history record and the committed state.

    Rejected moves raise `MoveError` instead, so a MoveResult always means
    the move succeeded.
    """

    record: MoveRecord
    state: GameState
