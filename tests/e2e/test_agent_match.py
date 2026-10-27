"""Two baseline agents complete a match over HTTP MCP (spec §18 criterion 38)."""

import httpx
import pytest

from gebeta.agents.baseline import GreedyAgent, RandomAgent
from gebeta.agents.controller import run_match
from gebeta.mcp.client import GebetaClient

pytestmark = pytest.mark.anyio


async def test_baseline_agents_complete_a_match_over_http(server_url: str) -> None:
    async with GebetaClient.http(f"{server_url}/mcp") as client:
        result = await run_match(client, {1: RandomAgent(seed=42), 2: GreedyAgent()})

    state = result.final_state
    assert state.status == "completed"
    assert state.collected.player_1 + state.collected.player_2 == 48
    assert state.result in {"player_1_wins", "player_2_wins", "draw"}

    async with httpx.AsyncClient(base_url=server_url) as rest:
        history = (await rest.get(f"/games/{result.game_id}/history")).json()
    assert len(history) == state.move_count
