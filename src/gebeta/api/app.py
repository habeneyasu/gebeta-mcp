"""FastAPI application factory: one shared `GameService` behind REST and MCP (/mcp).

Every failure is returned as `ErrorOut`: 404 for an unknown game, 422 for a
malformed request or an out-of-range pit, and 409 for a move that conflicts
with the current game state.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from gebeta.api.routes import router
from gebeta.application.game_service import GameNotFoundError, GameService, error_out
from gebeta.config import Settings
from gebeta.domain.errors import ErrorCode, MoveError
from gebeta.infrastructure.memory_repository import InMemoryGameRepository
from gebeta.mcp.server import create_mcp_server
from gebeta.schemas import ErrorOut


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    service = GameService(InMemoryGameRepository(), limits=settings.limits)
    mcp_server = create_mcp_server(service)
    mcp_http = mcp_server.streamable_http_app(streamable_http_path="/mcp", host=settings.host)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        async with mcp_server.session_manager.run():
            yield

    app = FastAPI(
        title="Gebeta", description="Deterministic Gebeta engine for AI agents.", lifespan=lifespan
    )
    app.state.service = service
    app.include_router(router)
    app.router.routes.extend(mcp_http.routes)  # MCP over streamable HTTP at /mcp

    @app.get("/health", tags=["health"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.exception_handler(GameNotFoundError)
    async def game_not_found(request: Request, error: GameNotFoundError) -> JSONResponse:
        return _error_response(status.HTTP_404_NOT_FOUND, error_out(error))

    @app.exception_handler(MoveError)
    async def move_rejected(request: Request, error: MoveError) -> JSONResponse:
        code = (
            status.HTTP_422_UNPROCESSABLE_CONTENT
            if error.code is ErrorCode.INVALID_PIT
            else status.HTTP_409_CONFLICT
        )
        return _error_response(code, error_out(error))

    @app.exception_handler(RequestValidationError)
    async def invalid_request(request: Request, error: RequestValidationError) -> JSONResponse:
        message = "; ".join(
            f"{'.'.join(str(part) for part in detail['loc'])}: {detail['msg']}"
            for detail in error.errors()
        )
        return _error_response(
            status.HTTP_422_UNPROCESSABLE_CONTENT, ErrorOut(code="invalid_request", message=message)
        )

    return app


def _error_response(status_code: int, error: ErrorOut) -> JSONResponse:
    return JSONResponse(status_code=status_code, content=error.model_dump())
