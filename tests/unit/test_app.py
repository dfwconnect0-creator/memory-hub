"""Phase 3 — App factory tests (RED phase)."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient


def _make_registry(valid: bool = True):
    r = MagicMock()
    r.validate_key.return_value = "agent" if valid else None
    r.list_agents.return_value = []
    return r


def _make_service():
    s = AsyncMock()
    s.add.return_value = "mem-id"
    s.search.return_value = []
    s.export.return_value = []
    return s


def test_create_app_returns_fastapi():
    from memory_hub.app import create_app

    app = create_app(memory_service=_make_service(), registry=_make_registry())
    assert isinstance(app, FastAPI)


def test_app_has_title():
    from memory_hub.app import create_app

    app = create_app(memory_service=_make_service(), registry=_make_registry())
    assert "Memory Hub" in app.title


def test_health_route_registered():
    from memory_hub.app import create_app

    app = create_app(memory_service=_make_service(), registry=_make_registry())
    paths = [r.path for r in app.routes]
    assert any("/health" in p for p in paths)


def test_memory_route_registered():
    from memory_hub.app import create_app

    app = create_app(memory_service=_make_service(), registry=_make_registry())
    paths = [r.path for r in app.routes]
    assert any("/memory" in p for p in paths)


def test_app_state_populated_during_lifespan():
    """create_app wires services into app.state via lifespan."""
    from memory_hub.app import create_app

    svc = _make_service()
    reg = _make_registry()
    app = create_app(memory_service=svc, registry=reg)
    client = TestClient(app, raise_server_exceptions=False)
    with client:  # triggers lifespan startup
        assert app.state.memory is svc
        assert app.state.registry is reg
