"""REST API over the shared game service."""

from typing import Any

import pytest
from fastapi.testclient import TestClient

from gebeta.api.app import create_app
from gebeta.application.game_service import GameService
from gebeta.config import Settings
from gebeta.domain.models import GameState, Limits
from gebeta.infrastructure.memory_repository import InMemoryGameRepository
from tests.fixtures.positions import LOOPING_BOARD, LOOPING_PIT, board_with, state_with


def client_with(state: GameState) -> TestClient:
    """A api_client whose only game is `state`, saved under the ID "test"."""
    app = create_app(Settings())
    repository = InMemoryGameRepository()
    repository.save(state)
    app.state.service = GameService(repository)
    return TestClient(app)


def new_game(api_client: TestClient, **body: Any) -> dict[str, Any]:
    response = api_client.post("/games", json=body or None)
    assert response.status_code == 201
    game: dict[str, Any] = response.json()
    return game


def assert_error(response: Any, status_code: int, code: str) -> None:
    assert response.status_code == status_code
    assert response.json()["code"] == code
    assert response.json()["message"]


def test_health(api_client: TestClient) -> None:
    assert api_client.get("/health").json() == {"status": "ok"}


def test_create_game(api_client: TestClient) -> None:
    game = new_game(api_client)
    assert (game["current_player"], game["status"]) == (1, "active")
    assert game["legal_moves"] == [6, 7, 8, 9, 10, 11]


def test_create_game_with_player_2(api_client: TestClient) -> None:
    assert new_game(api_client, starting_player=2)["current_player"] == 2


@pytest.mark.parametrize("player", [3, True, "2"])
def test_create_game_rejects_invalid_player(api_client: TestClient, player: object) -> None:
    assert_error(
        api_client.post("/games", json={"starting_player": player}), 422, "invalid_request"
    )


def test_list_and_get_games(api_client: TestClient) -> None:
    first, second = new_game(api_client), new_game(api_client)
    assert [g["game_id"] for g in api_client.get("/games").json()] == [
        first["game_id"],
        second["game_id"],
    ]
    assert api_client.get(f"/games/{first['game_id']}").json() == first


@pytest.mark.parametrize("path", ["", "/legal-moves", "/history"])
def test_unknown_game_is_404(api_client: TestClient, path: str) -> None:
    assert_error(api_client.get(f"/games/missing{path}"), 404, "game_not_found")


def test_play_move_on_unknown_game_is_404(api_client: TestClient) -> None:
    assert_error(api_client.post("/games/missing/moves", json={"pit": 6}), 404, "game_not_found")


def test_play_move_updates_state_and_history(api_client: TestClient) -> None:
    game_id = new_game(api_client)["game_id"]

    result = api_client.post(f"/games/{game_id}/moves", json={"pit": 6}).json()

    assert result["success"] is True
    assert (result["move"]["pit"], result["move"]["landing_pit"]) == (6, 8)
    assert result["state"]["current_player"] == 2
    assert api_client.get(f"/games/{game_id}").json() == result["state"]
    assert api_client.get(f"/games/{game_id}/history").json() == [result["move"]]
    assert api_client.get(f"/games/{game_id}/legal-moves").json() == [0, 1, 3, 4, 5]


@pytest.mark.parametrize(
    ("body", "status_code", "code"),
    [
        ({"pit": 12}, 422, "invalid_pit"),
        ({"pit": 0}, 409, "opponent_pit"),
        ({"pit": "6"}, 422, "invalid_request"),
        ({"pit": True}, 422, "invalid_request"),
        ({}, 422, "invalid_request"),
    ],
)
def test_rejected_moves_leave_the_game_unchanged(
    api_client: TestClient, body: dict[str, Any], status_code: int, code: str
) -> None:
    game = new_game(api_client)

    assert_error(api_client.post(f"/games/{game['game_id']}/moves", json=body), status_code, code)
    assert api_client.get(f"/games/{game['game_id']}").json() == game


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
def test_state_conflicts_are_409(state: GameState, pit: int, code: str) -> None:
    assert_error(client_with(state).post("/games/test/moves", json={"pit": pit}), 409, code)


def test_full_game_over_http(api_client: TestClient) -> None:
    game_id = new_game(api_client)["game_id"]
    state = api_client.get(f"/games/{game_id}").json()

    for _ in range(1_000):
        if state["status"] == "completed":
            break
        move = api_client.post(f"/games/{game_id}/moves", json={"pit": state["legal_moves"][0]})
        state = move.json()["state"]

    assert state["status"] == "completed"
    assert sum(state["collected"].values()) == 48
    assert state["result"] in {"player_1_wins", "player_2_wins", "draw"}
    assert len(api_client.get(f"/games/{game_id}/history").json()) == state["move_count"]
    assert_error(api_client.post(f"/games/{game_id}/moves", json={"pit": 6}), 409, "game_over")
