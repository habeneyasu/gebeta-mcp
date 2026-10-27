"""Typed MCP client for agents and the match controller (spec §17).

It imports only `gebeta.schemas` and the MCP SDK, so agents can affect a game
only through the MCP server and never bypass the engine's validation.
"""

import sys
from types import TracebackType
from typing import Any, Self

from mcp import Client, StdioServerParameters
from mcp.server.mcpserver import MCPServer
from pydantic import TypeAdapter, ValidationError

from gebeta.schemas import ErrorCodeName, ErrorOut, GameStateOut, MoveRecordOut, MoveResultOut

RULES_URI = "gebeta://rules"

_pits = TypeAdapter(list[int])
_records = TypeAdapter(list[MoveRecordOut])


class GebetaError(Exception):
    """A tool call the server rejected; `code` is an `ErrorOut` code."""

    def __init__(self, error: ErrorOut) -> None:
        super().__init__(error.message)
        self.code: ErrorCodeName = error.code
        self.message = error.message


class GebetaClient:
    """Async context manager: `async with GebetaClient.http(url) as client: ...`"""

    def __init__(self, server: str | StdioServerParameters | MCPServer) -> None:
        self._client = Client(server)

    @classmethod
    def http(cls, url: str = "http://127.0.0.1:8000/mcp") -> Self:
        """Connect to the shared server, where games are also visible over REST."""
        return cls(url)

    @classmethod
    def stdio(cls) -> Self:
        """Launch `python -m gebeta.mcp` as a subprocess with its own games."""
        return cls(StdioServerParameters(command=sys.executable, args=["-m", "gebeta.mcp"]))

    async def __aenter__(self) -> Self:
        await self._client.__aenter__()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        await self._client.__aexit__(exc_type, exc_value, traceback)

    async def new_game(self, starting_player: int = 1) -> GameStateOut:
        result = await self._call("new_game", {"starting_player": starting_player})
        return GameStateOut.model_validate(result)

    async def get_state(self, game_id: str) -> GameStateOut:
        return GameStateOut.model_validate(await self._call("get_state", {"game_id": game_id}))

    async def legal_moves(self, game_id: str) -> list[int]:
        result = await self._call("legal_moves", {"game_id": game_id})
        return _pits.validate_python(result["result"])

    async def play_move(self, game_id: str, pit: int) -> MoveResultOut:
        result = await self._call("play_move", {"game_id": game_id, "pit": pit})
        return MoveResultOut.model_validate(result)

    async def get_history(self, game_id: str) -> list[MoveRecordOut]:
        result = await self._call("get_history", {"game_id": game_id})
        return _records.validate_python(result["result"])

    async def rules(self) -> str:
        result = await self._client.read_resource(RULES_URI)
        return "".join(getattr(content, "text", "") for content in result.contents)

    async def _call(self, tool: str, arguments: dict[str, Any]) -> dict[str, Any]:
        result = await self._client.call_tool(tool, arguments)
        text = "".join(getattr(content, "text", "") for content in result.content)
        if result.is_error:
            raise GebetaError(_parse_error(text.removeprefix(f"Error executing tool {tool}: ")))
        structured: dict[str, Any] | None = result.structured_content
        if structured is None:
            raise GebetaError(ErrorOut(code="invalid_request", message=text or "Empty result."))
        return structured


def _parse_error(text: str) -> ErrorOut:
    """The server's `ErrorOut`, or `invalid_request` for SDK argument-validation errors."""
    try:
        return ErrorOut.model_validate_json(text)
    except ValidationError:
        return ErrorOut(code="invalid_request", message=text)
