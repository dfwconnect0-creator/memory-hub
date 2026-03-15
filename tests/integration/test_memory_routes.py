"""Phase 3 — Integration tests: full request/response cycle through app stack.

Uses a complete FastAPI app (routing + middleware + service) with mocked store.
No external infrastructure (mem0, qdrant, Gemini) is needed.
"""
from __future__ import annotations

from memory_hub.models.domain import MemoryCategory, SearchResult

# ── Critical test from the plan ───────────────────────────────────────────────

def test_search_is_post_not_get(client, auth_headers):
    """search MUST use POST. This is a hard requirement from the plan."""
    get_resp = client.get("/api/v1/memory/search", headers=auth_headers)
    assert get_resp.status_code == 405

    post_resp = client.post(
        "/api/v1/memory/search",
        json={"query": "test", "project": "p1"},
        headers=auth_headers,
    )
    assert post_resp.status_code == 200


# ── Full flow tests ───────────────────────────────────────────────────────────

def test_add_then_search_flow(client, auth_headers, mock_service):
    # 1. Add
    add_resp = client.post(
        "/api/v1/memory",
        json={"content": "Ramadan +40%", "project": "content-creation", "agent_id": "research_agent"},  # noqa: E501
        headers=auth_headers,
    )
    assert add_resp.status_code == 201
    assert add_resp.json()["memory_id"] == "mem-test-id"

    # 2. Search (mock returns one result)
    mock_service.search.return_value = [
        SearchResult(
            id="mem-test-id",
            content="Ramadan +40%",
            project="content-creation",
            agent_id="research_agent",
            score=0.95,
            category=MemoryCategory.TREND,
        )
    ]
    search_resp = client.post(
        "/api/v1/memory/search",
        json={"query": "ramadan", "project": "content-creation"},
        headers=auth_headers,
    )
    assert search_resp.status_code == 200
    data = search_resp.json()
    assert data["total"] == 1
    assert data["results"][0]["id"] == "mem-test-id"


def test_project_cross_contamination_blocked(client, auth_headers, mock_service):
    """Searching project B must not return project A memories — service is scoped correctly."""
    mock_service.search.return_value = []

    resp = client.post(
        "/api/v1/memory/search",
        json={"query": "ramadan", "project": "seo-audit"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    # Verify the service was called with the correct project
    call = mock_service.search.call_args
    assert call.kwargs.get("project") == "seo-audit"


def test_missing_api_key_rejected(client):
    resp = client.post(
        "/api/v1/memory",
        json={"content": "x", "project": "p1", "agent_id": "a1"},
    )
    assert resp.status_code == 403
    body = resp.json()
    assert "message" in body


def test_invalid_api_key_rejected(client):
    resp = client.post(
        "/api/v1/memory",
        json={"content": "x", "project": "p1", "agent_id": "a1"},
        headers={"X-API-Key": "wrong"},
    )
    assert resp.status_code == 403


def test_health_publicly_accessible(client):
    """Health check must NOT require auth."""
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_batch_add_stores_all_items(client, auth_headers, mock_service):
    mock_service.batch_add.return_value = ["id-1", "id-2", "id-3"]
    resp = client.post(
        "/api/v1/memory/batch",
        json={
            "project": "content-creation",
            "agent_id": "research_agent",
            "items": [
                {"content": "trend 1", "project": "content-creation", "agent_id": "research_agent"},
                {"content": "trend 2", "project": "content-creation", "agent_id": "research_agent"},
                {"content": "trend 3", "project": "content-creation", "agent_id": "research_agent"},
            ],
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["count"] == 3
    assert len(data["memory_ids"]) == 3


def test_export_calls_service_with_project(client, auth_headers, mock_service):
    resp = client.get(
        "/api/v1/memory/export?project=personal",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    mock_service.export.assert_called_once_with(project="personal")


def test_agents_list_requires_auth(client):
    resp = client.get("/api/v1/agents")
    assert resp.status_code == 403


def test_agents_list_returns_200(client, auth_headers):
    resp = client.get("/api/v1/agents", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "agents" in data
    assert "count" in data
