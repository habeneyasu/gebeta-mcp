"""MCP over its real transports: streamable HTTP at /mcp and stdio."""

import httpx
import pytest

from gebeta.mcp.client import GebetaClient

pytestmark = pytest.mark.anyio


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
