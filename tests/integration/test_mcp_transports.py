"""MCP over its real transports: streamable HTTP at /mcp and stdio."""

import socket
import threading
import time
from collections.abc import Iterator

import httpx
import pytest
import uvicorn

from gebeta.api.app import create_app
from gebeta.config import Settings
from gebeta.mcp.client import GebetaClient

pytestmark = pytest.mark.anyio


@pytest.fixture
def server_url() -> Iterator[str]:
    """The FastAPI app (REST and MCP) served by uvicorn on a free local port."""
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    server = uvicorn.Server(
        uvicorn.Config(create_app(Settings()), host="127.0.0.1", port=port, log_level="warning")
    )
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.monotonic() + 10
    while not server.started:
        assert time.monotonic() < deadline, "server did not start"
        time.sleep(0.02)
    yield f"http://127.0.0.1:{port}"
    server.should_exit = True
    thread.join(timeout=10)


async def test_http_mcp_shares_games_with_rest(server_url: str) -> None:
    async with GebetaClient.http(f"{server_url}/mcp") as client:
        game = await client.new_game()
        await client.play_move(game.game_id, 6)

    async with httpx.AsyncClient(base_url=server_url) as rest:
        state = (await rest.get(f"/games/{game.game_id}")).json()
    assert (state["move_count"], state["current_player"]) == (1, 2)


async def test_stdio_server() -> None:
    async with GebetaClient.stdio() as client:
        game = await client.new_game()
        assert game.legal_moves == [6, 7, 8, 9, 10, 11]
        assert (await client.rules()).startswith("# Gebeta Game Rules")
