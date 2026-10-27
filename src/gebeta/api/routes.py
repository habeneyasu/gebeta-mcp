"""REST endpoints for games; each delegates to the shared `GameService`."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request, status

from gebeta.application.game_service import GameService
from gebeta.mapping import game_state_out, move_record_out, move_result_out
from gebeta.schemas import (
    ErrorOut,
    GameStateOut,
    MoveRecordOut,
    MoveResultOut,
    NewGameRequest,
    PlayMoveRequest,
)

ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    code: {"model": ErrorOut} for code in (404, 409, 422)
}

router = APIRouter(prefix="/games", tags=["games"], responses=ERROR_RESPONSES)


def get_service(request: Request) -> GameService:
    service: GameService = request.app.state.service
    return service


Service = Annotated[GameService, Depends(get_service)]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_game(service: Service, body: NewGameRequest | None = None) -> GameStateOut:
    request = body or NewGameRequest()
    return game_state_out(service.create_game(starting_player=request.starting_player))


@router.get("")
def list_games(service: Service) -> list[GameStateOut]:
    return [game_state_out(state) for state in service.list_games()]


@router.get("/{game_id}")
def get_game(game_id: str, service: Service) -> GameStateOut:
    return game_state_out(service.get_state(game_id))


@router.get("/{game_id}/legal-moves")
def get_legal_moves(game_id: str, service: Service) -> list[int]:
    return list(service.legal_moves(game_id))


@router.post("/{game_id}/moves")
def play_move(game_id: str, body: PlayMoveRequest, service: Service) -> MoveResultOut:
    return move_result_out(service.play_move(game_id, body.pit))


@router.get("/{game_id}/history")
def get_history(game_id: str, service: Service) -> list[MoveRecordOut]:
    return [move_record_out(record) for record in service.history(game_id)]
