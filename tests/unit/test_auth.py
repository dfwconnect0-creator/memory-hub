"""Phase 2 — Auth middleware tests (RED phase)."""
from unittest.mock import MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient


def _make_app(registry) -> FastAPI:
    from memory_hub.middleware.auth import AuthMiddleware
    app = FastAPI()
    app.add_middleware(AuthMiddleware, registry=registry)

    @app.get("/test")
    def test_endpoint():
        return {"ok": True}

    return app


def test_valid_key_accepted():
    registry = MagicMock()
    registry.validate_key.return_value = "research_agent"
    client = TestClient(_make_app(registry), raise_server_exceptions=False)
    response = client.get("/test", headers={"X-API-Key": "valid-key"})
    assert response.status_code == 200


def test_invalid_key_rejected():
    registry = MagicMock()
    registry.validate_key.return_value = None
    client = TestClient(_make_app(registry), raise_server_exceptions=False)
    response = client.get("/test", headers={"X-API-Key": "bad-key"})
    assert response.status_code == 403


def test_missing_header_returns_403():
    registry = MagicMock()
    client = TestClient(_make_app(registry), raise_server_exceptions=False)
    response = client.get("/test")
    assert response.status_code == 403


def test_error_body_has_message():
    registry = MagicMock()
    registry.validate_key.return_value = None
    client = TestClient(_make_app(registry), raise_server_exceptions=False)
    response = client.get("/test", headers={"X-API-Key": "bad-key"})
    body = response.json()
    assert "message" in body or "detail" in body or "error" in body


def test_valid_key_sets_agent_id(monkeypatch):
    """Valid key must inject agent_id into request state."""
    registry = MagicMock()
    registry.validate_key.return_value = "seo_agent"

    from memory_hub.middleware.auth import AuthMiddleware
    app = FastAPI()
    app.add_middleware(AuthMiddleware, registry=registry)

    @app.get("/whoami")
    def whoami_endpoint(request):
        return {"agent_id": request.state.agent_id}

    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/whoami", headers={"X-API-Key": "agent-key"})
    # Should not be 403
    assert response.status_code != 403
