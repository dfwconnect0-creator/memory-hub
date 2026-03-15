"""Phase 3 — Health route tests (RED phase)."""
from __future__ import annotations


def test_health_returns_200(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200


def test_health_returns_ok_status(client):
    response = client.get("/api/v1/health")
    data = response.json()
    assert data["status"] == "ok"


def test_health_no_auth_required(client):
    """Health endpoint must be publicly accessible without API key."""
    response = client.get("/api/v1/health")  # no auth header
    assert response.status_code == 200


def test_health_includes_agents_count(client):
    response = client.get("/api/v1/health")
    data = response.json()
    assert "agents_registered" in data


def test_health_includes_version(client):
    response = client.get("/api/v1/health")
    data = response.json()
    assert "version" in data
