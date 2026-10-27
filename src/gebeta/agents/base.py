"""Agent interface: a move-selection strategy (spec §17).

Agents only choose a pit. The controller submits it through MCP and the
engine decides the outcome, so an agent cannot bypass move validation.
"""

from typing import Protocol

from gebeta.schemas import GameStateOut


class Agent(Protocol):
    name: str

    async def choose_move(self, state: GameStateOut, legal_moves: list[int]) -> int:
        """Return one pit, normally from `legal_moves`."""
        ...
