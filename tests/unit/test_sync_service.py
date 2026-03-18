"""Tests for SyncService."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from memory_hub.config import Settings


def _make_settings(monkeypatch, qdrant_url: str = "", qdrant_api_key: str = "") -> Settings:
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini")
    monkeypatch.setenv("HUB_API_KEY", "test-hub")
    monkeypatch.setenv("QDRANT_URL", qdrant_url)
    monkeypatch.setenv("QDRANT_API_KEY", qdrant_api_key)
    return Settings()


def test_can_sync_with_creds(monkeypatch):
    settings = _make_settings(
        monkeypatch,
        qdrant_url="https://cloud.qdrant.io",
        qdrant_api_key="secret-key",
    )
    from memory_hub.services.sync_service import SyncService

    svc = SyncService(settings)
    assert svc.can_sync() is True


def test_can_sync_without_creds(monkeypatch):
    settings = _make_settings(monkeypatch, qdrant_url="", qdrant_api_key="")
    from memory_hub.services.sync_service import SyncService

    svc = SyncService(settings)
    assert svc.can_sync() is False


@pytest.mark.asyncio
async def test_sync_no_local_collection(monkeypatch):
    settings = _make_settings(
        monkeypatch,
        qdrant_url="https://cloud.qdrant.io",
        qdrant_api_key="secret-key",
    )
    from memory_hub.services.sync_service import SyncService

    mock_client = MagicMock()
    mock_client.collection_exists.return_value = False

    with patch("memory_hub.services.sync_service.QdrantClient", return_value=mock_client):
        svc = SyncService(settings)
        result = await svc.sync()

    assert result["status"] == "skipped"
    assert result["points_synced"] == 0
