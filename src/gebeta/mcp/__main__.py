"""Stdio MCP server: `python -m gebeta.mcp`.

This process keeps its own games, which the HTTP server and UI do not see.
"""

from gebeta.application.game_service import GameService
from gebeta.config import Settings
from gebeta.infrastructure.memory_repository import InMemoryGameRepository
from gebeta.mcp.server import create_mcp_server


def main() -> None:
    service = GameService(InMemoryGameRepository(), limits=Settings().limits)
    create_mcp_server(service).run("stdio")


if __name__ == "__main__":
    main()
