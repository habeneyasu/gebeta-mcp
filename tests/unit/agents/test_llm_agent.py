"""Claude agent against a fake Anthropic client (no network)."""

from dataclasses import dataclass, field
from typing import Any, cast

import pytest

from gebeta.agents.llm_agent import AgentError, ClaudeAgent, PitChoice
from gebeta.application.game_service import _state_out
from gebeta.domain.game import Game

pytestmark = pytest.mark.anyio


@dataclass
class FakeResponse:
    parsed_output: PitChoice | None
    stop_reason: str = "end_turn"
    stop_details: Any = None
    content: list[Any] = field(default_factory=list)


class FakeClient:
    """Mimics `AsyncAnthropic().beta.messages.parse`, returning queued responses."""

    def __init__(self, *responses: FakeResponse) -> None:
        self.requests: list[dict[str, Any]] = []
        self._responses = list(responses)
        self.beta = self
        self.messages = self

    async def parse(self, **request: Any) -> FakeResponse:
        self.requests.append({**request, "messages": list(request["messages"])})
        return self._responses.pop(0)


def agent_with(*responses: FakeResponse) -> tuple[ClaudeAgent, FakeClient]:
    client = FakeClient(*responses)
    return ClaudeAgent(cast(Any, client), model="claude-opus-5-5", effort="low"), client


def choice(pit: int) -> FakeResponse:
    return FakeResponse(parsed_output=PitChoice(pit=pit, reason="test"))


STATE = _state_out(Game.new("g1").state)


async def test_returns_a_legal_choice() -> None:
    agent, client = agent_with(choice(9))

    assert await agent.choose_move(STATE, STATE.legal_moves) == 9
    request = client.requests[0]
    assert request["model"] == "claude-opus-5-5"
    assert request["output_format"] is PitChoice
    assert request["output_config"] == {"effort": "low"}
    assert request["fallbacks"] == "default"
    assert '"legal_moves": [6, 7, 8, 9, 10, 11]' in request["messages"][0]["content"]


async def test_illegal_choice_is_corrected_and_asked_again() -> None:
    agent, client = agent_with(choice(2), choice(7))

    assert await agent.choose_move(STATE, STATE.legal_moves) == 7
    retry = client.requests[1]["messages"]
    assert [m["role"] for m in retry] == ["user", "assistant", "user"]
    assert "pit 2, which is not legal" in retry[2]["content"]


async def test_gives_up_after_max_attempts() -> None:
    agent, _ = agent_with(choice(0), choice(1), choice(2))
    with pytest.raises(AgentError, match="3 attempts"):
        await agent.choose_move(STATE, STATE.legal_moves)


async def test_refusal_is_reported() -> None:
    agent, _ = agent_with(FakeResponse(parsed_output=None, stop_reason="refusal"))
    with pytest.raises(AgentError, match="declined"):
        await agent.choose_move(STATE, STATE.legal_moves)
