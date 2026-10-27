"""Shared fixtures: game service, FastAPI test client, and in-memory MCP client."""

from collections.abc import AsyncIterator

import pytest
from fastapi.testclient import TestClient

from gebeta.api.app import create_app
from gebeta.application.game_service import GameService
from gebeta.config import Settings
from gebeta.mcp.client import GebetaClient
from gebeta.mcp.server import create_mcp_server
from tests.fixtures.services import service_with


@pytest.fixture
def service() -> GameService:
    return service_with()


@pytest.fixture
def api_client() -> TestClient:
    return TestClient(create_app(Settings()))


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
async def mcp_client(service: GameService) -> AsyncIterator[GebetaClient]:
    """An MCP client connected in-process to a server over `service`.

    Use with `pytest.mark.anyio`, which runs the fixture and test in one task as
    the MCP SDK's task groups require.
    """
    async with GebetaClient(create_mcp_server(service)) as client:
        yield client
