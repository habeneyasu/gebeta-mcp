"""MCP server: game tools and the `gebeta://rules` resource (spec §16).

Every tool delegates to `GameService`; the server implements no rules of its
own. A rejected move or unknown game is returned as a tool error whose text
is the same `ErrorOut` JSON the REST API returns.
"""

from collections.abc import Callable
from importlib.resources import files
from pathlib import Path

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

from gebeta.application.game_service import GameNotFoundError, GameService, error_out
from gebeta.domain.errors import MoveError
from gebeta.schemas import GameStateOut, MoveRecordOut, MoveResultOut, Pit, StartingPlayer

RULES_URI = "gebeta://rules"

INSTRUCTIONS = """\
Play Gebeta through these tools; the engine enforces every rule.
Player 1 owns pits 6-11 and player 2 owns pits 0-5. Call get_state for the board,
the current player, and legal_moves, then play_move with one of those pits.
Rejected moves return an error with a code and leave the game unchanged.
Read gebeta://rules for the full rules."""


def create_mcp_server(service: GameService) -> MCPServer:
    server = MCPServer(name="gebeta", instructions=INSTRUCTIONS)
    rules_text = load_rules()

    @server.tool()
    def new_game(starting_player: StartingPlayer = 1) -> GameStateOut:
        """Start a new game and return its state. Player 1 starts unless stated otherwise."""
        return _run(lambda: service.create_game(starting_player=starting_player))

    @server.tool()
    def get_state(game_id: str) -> GameStateOut:
        """Board, current player, legal moves, collected seeds, status, and result."""
        return _run(lambda: service.get_state(game_id))

    @server.tool()
    def legal_moves(game_id: str) -> list[int]:
        """Pits the current player may select. Empty when the game has ended."""
        return _run(lambda: service.legal_moves(game_id))

    @server.tool()
    def play_move(game_id: str, pit: Pit) -> MoveResultOut:
        """Play `pit` for the current player. Returns the move and the new state."""
        return _run(lambda: service.play_move(game_id, pit))

    @server.tool()
    def get_history(game_id: str) -> list[MoveRecordOut]:
        """Every valid move so far, oldest first."""
        return _run(lambda: service.history(game_id))

    @server.resource(RULES_URI, name="rules", mime_type="text/markdown")
    def rules() -> str:
        """The authoritative Gebeta rules this engine enforces."""
        return rules_text

    return server


def load_rules() -> str:
    """The rules spec: packaged in the wheel, or read from the source checkout."""
    packaged = files("gebeta").joinpath("rules.md")
    if packaged.is_file():
        return packaged.read_text(encoding="utf-8")
    checkout = Path(__file__).resolve().parents[3] / "docs" / "spec" / "gebeta-rules.md"
    return checkout.read_text(encoding="utf-8")


def _run[T](call: Callable[[], T]) -> T:
    try:
        return call()
    except (MoveError, GameNotFoundError) as error:
        raise ToolError(error_out(error).model_dump_json()) from error
