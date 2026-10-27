"""Shared fixtures: game service, FastAPI test client, MCP client, and a live server."""

import socket
import threading
import time
from collections.abc import AsyncIterator, Iterator

import pytest
import uvicorn
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


@pytest.fixture
def server_url() -> Iterator[str]:
    """The FastAPI app (REST and MCP) served by uvicorn on a free local port."""
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    server = uvicorn.Server(
        uvicorn.Config(create_app(Settings()), host="127.0.0.1", port=port, log_level="warning")
    )
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.monotonic() + 10
    while not server.started:
        assert time.monotonic() < deadline, "server did not start"
        time.sleep(0.02)
    yield f"http://127.0.0.1:{port}"
    server.should_exit = True
    thread.join(timeout=10)
