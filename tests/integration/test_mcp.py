"""MCP client ↔ server in memory (spec §16, §18 criteria 37–38)."""

import pytest

from gebeta.domain.models import GameState, Limits
from gebeta.mcp.client import GebetaClient, GebetaError
from gebeta.mcp.server import create_mcp_server
from tests.fixtures.positions import LOOPING_BOARD, LOOPING_PIT, board_with, state_with
from tests.fixtures.services import service_with

pytestmark = pytest.mark.anyio


async def test_new_game_and_state(mcp_client: GebetaClient) -> None:
    game = await mcp_client.new_game()

    assert (game.game_id, game.current_player, game.status) == ("g1", 1, "active")
    assert await mcp_client.get_state("g1") == game
    assert await mcp_client.legal_moves("g1") == [6, 7, 8, 9, 10, 11]


async def test_new_game_with_player_2(mcp_client: GebetaClient) -> None:
    assert (await mcp_client.new_game(starting_player=2)).current_player == 2


async def test_play_move_and_history(mcp_client: GebetaClient) -> None:
    await mcp_client.new_game()

    result = await mcp_client.play_move("g1", 6)

    assert (result.move.pit, result.move.landing_pit, result.state.current_player) == (6, 8, 2)
    assert await mcp_client.get_state("g1") == result.state
    assert await mcp_client.get_history("g1") == [result.move]


async def test_rules_resource(mcp_client: GebetaClient) -> None:
    rules = await mcp_client.rules()
    assert rules.startswith("# Gebeta Game Rules")
    assert "no-capture limit" in rules


@pytest.mark.parametrize(
    ("pit", "code"),
    [(12, "invalid_pit"), (0, "opponent_pit"), (True, "invalid_request"), ("6", "invalid_request")],
)
async def test_rejected_moves_leave_the_game_unchanged(
    mcp_client: GebetaClient, pit: object, code: str
) -> None:
    game = await mcp_client.new_game()

    with pytest.raises(GebetaError) as excinfo:
        await mcp_client.play_move("g1", pit)  # type: ignore[arg-type]

    assert excinfo.value.code == code
    assert await mcp_client.get_state("g1") == game


@pytest.mark.parametrize("player", [3, True])
async def test_new_game_rejects_invalid_player(mcp_client: GebetaClient, player: int) -> None:
    with pytest.raises(GebetaError) as excinfo:
        await mcp_client.new_game(starting_player=player)
    assert excinfo.value.code == "invalid_request"


@pytest.mark.parametrize("tool", ["get_state", "legal_moves", "get_history"])
async def test_unknown_game(mcp_client: GebetaClient, tool: str) -> None:
    with pytest.raises(GebetaError) as excinfo:
        await getattr(mcp_client, tool)("missing")
    assert (excinfo.value.code, excinfo.value.message) == (
        "game_not_found",
        "Game 'missing' not found.",
    )


@pytest.mark.parametrize(
    ("state", "pit", "code"),
    [
        (state_with(board_with(p6=1, p0=1)), 7, "empty_pit"),
        (state_with(LOOPING_BOARD), LOOPING_PIT, "sowing_cycle"),
        (
            state_with(board_with(p0=13), 2, limits=Limits(max_drops=24)),
            0,
            "sowing_limit_exceeded",
        ),
    ],
    ids=["empty", "cycle", "limit"],
)
async def test_engine_rejections_carry_their_code(state: GameState, pit: int, code: str) -> None:
    async with GebetaClient(create_mcp_server(service_with(state))) as client:
        with pytest.raises(GebetaError) as excinfo:
            await client.play_move("test", pit)
    assert excinfo.value.code == code


async def test_full_game_through_mcp(mcp_client: GebetaClient) -> None:
    state = await mcp_client.new_game()

    for _ in range(1_000):
        if state.status == "completed":
            break
        state = (await mcp_client.play_move(state.game_id, state.legal_moves[0])).state

    assert state.status == "completed"
    assert state.collected.player_1 + state.collected.player_2 == 48
    assert len(await mcp_client.get_history(state.game_id)) == state.move_count
    with pytest.raises(GebetaError) as excinfo:
        await mcp_client.play_move(state.game_id, 6)
    assert excinfo.value.code == "game_over"
