"""Match controller over an in-memory MCP client (spec §17)."""

import pytest

from gebeta.agents.base import Agent
from gebeta.agents.baseline import GreedyAgent, RandomAgent
from gebeta.agents.controller import MatchError, run_match
from gebeta.mcp.client import GebetaClient
from gebeta.schemas import GameStateOut, PlayerNumber

pytestmark = pytest.mark.anyio


class RecordingAgent:
    """Plays the first legal move and records which player it was asked for."""

    def __init__(self, name: str, calls: list[tuple[str, int | None]]) -> None:
        self.name = name
        self._calls = calls

    async def choose_move(self, state: GameStateOut, legal_moves: list[int]) -> int:
        self._calls.append((self.name, state.current_player))
        return legal_moves[0]


class StubbornAgent:
    """Tries an illegal pit `illegal_tries` times, then plays legally."""

    def __init__(self, illegal_tries: int) -> None:
        self.name = "stubborn"
        self._remaining = illegal_tries

    async def choose_move(self, state: GameStateOut, legal_moves: list[int]) -> int:
        if self._remaining:
            self._remaining -= 1
            return 99
        return legal_moves[0]


async def test_two_agents_complete_a_match(mcp_client: GebetaClient) -> None:
    result = await run_match(mcp_client, {1: RandomAgent(seed=1), 2: GreedyAgent()})

    state = result.final_state
    assert state.status == "completed"
    assert state.collected.player_1 + state.collected.player_2 == 48
    assert result.rejected_moves == 0
    assert len(await mcp_client.get_history(result.game_id)) == state.move_count


async def test_each_agent_is_asked_only_for_the_engines_current_player(
    mcp_client: GebetaClient,
) -> None:
    calls: list[tuple[str, int | None]] = []
    await run_match(mcp_client, {1: RecordingAgent("one", calls), 2: RecordingAgent("two", calls)})

    assert calls
    assert all((name == "one") == (player == 1) for name, player in calls)
    history = await mcp_client.get_history("g1")
    assert [record.player for record in history] == [player for _, player in calls]


async def test_starting_player_2(mcp_client: GebetaClient) -> None:
    calls: list[tuple[str, int | None]] = []
    agents: dict[PlayerNumber, Agent] = {
        1: RecordingAgent("one", calls),
        2: RecordingAgent("two", calls),
    }
    await run_match(mcp_client, agents, starting_player=2)
    assert calls[0] == ("two", 2)


async def test_rejected_moves_are_retried(mcp_client: GebetaClient) -> None:
    result = await run_match(mcp_client, {1: StubbornAgent(illegal_tries=2), 2: GreedyAgent()})
    assert result.rejected_moves == 2
    assert result.final_state.status == "completed"


async def test_too_many_rejections_stop_the_match(mcp_client: GebetaClient) -> None:
    with pytest.raises(MatchError, match="invalid_pit"):
        await run_match(mcp_client, {1: StubbornAgent(illegal_tries=10), 2: GreedyAgent()})
    assert (await mcp_client.get_state("g1")).move_count == 0


async def test_turn_limit_stops_the_match(mcp_client: GebetaClient) -> None:
    with pytest.raises(MatchError, match="did not finish"):
        await run_match(mcp_client, {1: GreedyAgent(), 2: GreedyAgent()}, max_turns=3)
