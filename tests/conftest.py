"""Shared fixtures for all tests. Uses lazy imports so unimplemented modules
don't break the existing unit test suite during RED phase."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def mock_service():
    service = AsyncMock()
    service.add.return_value = "mem-test-id"
    service.search.return_value = []
    service.batch_add.return_value = ["mem-1", "mem-2"]
    service.export.return_value = []
    service.delete.return_value = True
    return service


@pytest.fixture
def mock_registry():
    """Registry that accepts 'test-valid-key' and rejects everything else."""
    registry = MagicMock()
    registry.validate_key.side_effect = (
        lambda k: "research_agent" if k == "test-valid-key" else None
    )
    registry.list_agents.return_value = []
    registry.get_agent.return_value = None
    return registry


@pytest.fixture
def auth_headers() -> dict[str, str]:
    return {"X-API-Key": "test-valid-key"}


@pytest.fixture
def client(mock_service, mock_registry):
    from memory_hub.app import create_app  # lazy — fails until app.py exists

    app = create_app(memory_service=mock_service, registry=mock_registry)
    # Use as context manager so the lifespan runs and app.state is populated
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
