"""Match controller: plays two agents against each other through MCP (spec §17).

The controller never decides turn order: after every move it asks the agent
of whichever player the engine reports as current.
"""

from collections.abc import Mapping
from dataclasses import dataclass

from gebeta.agents.base import Agent
from gebeta.mcp.client import GebetaClient, GebetaError
from gebeta.schemas import GameStateOut, PlayerNumber


class MatchError(Exception):
    """A match that could not be completed; the game state is left as the engine has it."""


@dataclass(frozen=True, slots=True)
class MatchResult:
    final_state: GameStateOut
    rejected_moves: int

    @property
    def game_id(self) -> str:
        return self.final_state.game_id


async def run_match(
    client: GebetaClient,
    agents: Mapping[PlayerNumber, Agent],
    *,
    starting_player: PlayerNumber = 1,
    max_turns: int = 1_000,
    max_retries: int = 3,
) -> MatchResult:
    """Play a new game to completion, retrying an agent up to `max_retries` times per turn."""
    state = await client.new_game(starting_player=starting_player)
    rejected = 0

    for _ in range(max_turns):
        if state.status == "completed":
            return MatchResult(final_state=state, rejected_moves=rejected)
        player = state.current_player
        if player is None:
            raise MatchError(f"Game {state.game_id} is active but has no current player.")
        agent = agents[player]

        for attempt in range(max_retries + 1):
            pit = await agent.choose_move(state, list(state.legal_moves))
            try:
                state = (await client.play_move(state.game_id, pit)).state
                break
            except GebetaError as error:
                rejected += 1
                if attempt == max_retries:
                    raise MatchError(
                        f"Player {player} ({agent.name}) made {max_retries + 1} rejected moves; "
                        f"last: {error.code}: {error.message}"
                    ) from error
                state = await client.get_state(state.game_id)

    raise MatchError(f"Game {state.game_id} did not finish within {max_turns} turns.")
