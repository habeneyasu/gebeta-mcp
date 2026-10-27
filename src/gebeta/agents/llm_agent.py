"""Claude agent: asks Claude to choose a pit from the legal moves (spec §17).

Claude only proposes a pit; the engine decides the outcome. If Claude names a
pit outside the legal moves, the agent tells it so and asks again.
"""

import json
from typing import Any, Literal

from anthropic import AsyncAnthropic
from pydantic import BaseModel, Field

from gebeta.schemas import GameStateOut

DEFAULT_MODEL = "claude-opus-5-5"
Effort = Literal["low", "medium", "high", "xhigh", "max"]

SYSTEM_PROMPT = """\
You are playing Gebeta, a two-player sowing game. A deterministic engine enforces \
the rules; your only job is to choose a good pit from the legal moves you are given.

Board: 12 pits indexed 0-11, sown in the order 0, 1, ..., 11, 0, ... Player 1 owns \
pits 6-11 and player 2 owns pits 0-5. Pit i is opposite pit (i + 6) % 12.

A move picks up every seed in one of your pits and sows them one at a time into the \
following pits. If the last seed lands in an occupied pit, all seeds there are picked \
up and sowing continues. When the last seed lands in an empty pit, every seed in the \
opposite pit is captured, and a capture lets you move again. The game ends when \
neither player can move or after 20 moves in a row without a capture; seeds left in \
a row go to that row's owner. The player with more seeds wins.

Answer with the pit you choose and one short sentence explaining why."""


class PitChoice(BaseModel):
    pit: int = Field(description="One of the legal moves.")
    reason: str = Field(description="One short sentence.")


class AgentError(Exception):
    """Claude did not produce a legal move."""


class ClaudeAgent:
    def __init__(
        self,
        client: AsyncAnthropic | None = None,
        *,
        model: str = DEFAULT_MODEL,
        effort: Effort = "medium",
        max_attempts: int = 3,
        name: str = "claude",
    ) -> None:
        self.name = name
        self._client = client or AsyncAnthropic()
        self._model = model
        self._effort: Effort = effort
        self._max_attempts = max_attempts

    async def choose_move(self, state: GameStateOut, legal_moves: list[int]) -> int:
        messages: list[Any] = [{"role": "user", "content": _describe(state, legal_moves)}]
        for _ in range(self._max_attempts):
            response = await self._client.beta.messages.parse(
                model=self._model,
                max_tokens=16_000,
                system=SYSTEM_PROMPT,
                messages=messages,
                output_format=PitChoice,
                output_config={"effort": self._effort},
                betas=["server-side-fallback-2026-07-01"],
                fallbacks="default",
            )
            if response.stop_reason == "refusal":
                raise AgentError(f"Claude declined to choose a move: {response.stop_details}")
            choice = response.parsed_output
            if choice is not None and choice.pit in legal_moves:
                return choice.pit
            # Keep Claude's full turn (including thinking blocks) and ask again.
            messages.append({"role": "assistant", "content": response.content})
            proposed = "no pit" if choice is None else f"pit {choice.pit}"
            messages.append(
                {
                    "role": "user",
                    "content": f"You chose {proposed}, which is not legal. "
                    f"Choose one of {legal_moves}.",
                }
            )
        raise AgentError(f"Claude did not choose a legal move in {self._max_attempts} attempts.")


def _describe(state: GameStateOut, legal_moves: list[int]) -> str:
    position = {
        "you_are_player": state.current_player,
        "board": state.board,
        "collected": state.collected.model_dump(),
        "moves_without_capture": state.moves_without_capture,
        "legal_moves": legal_moves,
    }
    return f"Current position:\n{json.dumps(position)}\nChoose your move."
