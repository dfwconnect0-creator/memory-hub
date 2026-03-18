"""Tests for POST /api/v1/sync route."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def mock_sync_ok():
    svc = MagicMock()
    svc.can_sync.return_value = True
    svc.sync = AsyncMock(return_value={"status": "ok", "points_synced": 5, "duration_seconds": 0.1})
    return svc


@pytest.fixture
def mock_sync_no_creds():
    svc = MagicMock()
    svc.can_sync.return_value = False
    return svc


def _make_client(sync_service: object) -> TestClient:
    mock_memory = AsyncMock()
    mock_registry = MagicMock()
    # Master key maps to "hub"; any other key is rejected
    mock_registry.validate_key.side_effect = lambda k: "hub" if k == "master-key" else None

    from memory_hub.app import create_app

    app = create_app(
        memory_service=mock_memory,
        registry=mock_registry,
        sync_service=sync_service,
    )
    return TestClient(app, raise_server_exceptions=False)


def test_sync_returns_200_with_report(mock_sync_ok):
    client = _make_client(mock_sync_ok)
    with client:
        response = client.post("/api/v1/sync", headers={"X-API-Key": "master-key"})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["points_synced"] == 5


def test_sync_returns_400_when_no_creds(mock_sync_no_creds):
    client = _make_client(mock_sync_no_creds)
    with client:
        response = client.post("/api/v1/sync", headers={"X-API-Key": "master-key"})
    assert response.status_code == 400
