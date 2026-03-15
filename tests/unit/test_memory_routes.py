"""Phase 3 — Memory route unit tests (RED phase).

All tests use the shared client/auth_headers/mock_service fixtures from conftest.py.
"""
from __future__ import annotations

from memory_hub.models.domain import MemoryCategory, SearchResult

# ── POST /api/v1/memory ───────────────────────────────────────────────────────

def test_add_memory_returns_201(client, auth_headers):
    response = client.post(
        "/api/v1/memory",
        json={
            "content": "Ramadan trends up 40%",
            "project": "content-creation",
            "agent_id": "research_agent",
        },
        headers=auth_headers,
    )
    assert response.status_code == 201


def test_add_memory_returns_memory_id(client, auth_headers):
    response = client.post(
        "/api/v1/memory",
        json={"content": "SEO tip", "project": "seo-audit", "agent_id": "seo_agent"},
        headers=auth_headers,
    )
    data = response.json()
    assert "memory_id" in data
    assert data["memory_id"] == "mem-test-id"


def test_add_memory_with_category(client, auth_headers):
    response = client.post(
        "/api/v1/memory",
        json={
            "content": "Brand voice update",
            "project": "content-creation",
            "agent_id": "writer_agent",
            "category": "brand",
        },
        headers=auth_headers,
    )
    assert response.status_code == 201


def test_add_memory_invalid_category_422(client, auth_headers):
    response = client.post(
        "/api/v1/memory",
        json={"content": "x", "project": "p1", "agent_id": "a1", "category": "FAKE"},
        headers=auth_headers,
    )
    assert response.status_code == 422


def test_add_memory_missing_content_422(client, auth_headers):
    response = client.post(
        "/api/v1/memory",
        json={"project": "p1", "agent_id": "a1"},
        headers=auth_headers,
    )
    assert response.status_code == 422


def test_add_memory_no_auth_403(client):
    response = client.post(
        "/api/v1/memory",
        json={"content": "x", "project": "p1", "agent_id": "a1"},
    )
    assert response.status_code == 403


def test_add_memory_invalid_key_403(client):
    response = client.post(
        "/api/v1/memory",
        json={"content": "x", "project": "p1", "agent_id": "a1"},
        headers={"X-API-Key": "wrong-key"},
    )
    assert response.status_code == 403


# ── POST /api/v1/memory/search ────────────────────────────────────────────────

def test_search_is_post_not_get(client, auth_headers):
    """Critical: search must be POST. GET should return 405."""
    response = client.get("/api/v1/memory/search", headers=auth_headers)
    assert response.status_code == 405


def test_search_returns_200(client, auth_headers):
    response = client.post(
        "/api/v1/memory/search",
        json={"query": "ramadan", "project": "content-creation"},
        headers=auth_headers,
    )
    assert response.status_code == 200


def test_search_response_shape(client, auth_headers):
    response = client.post(
        "/api/v1/memory/search",
        json={"query": "test", "project": "p1"},
        headers=auth_headers,
    )
    data = response.json()
    assert "results" in data
    assert "total" in data
    assert "query" in data


def test_search_returns_results(client, auth_headers, mock_service):
    mock_service.search.return_value = [
        SearchResult(
            id="m1",
            content="Ramadan trend",
            project="content-creation",
            agent_id="research_agent",
            score=0.9,
            category=MemoryCategory.TREND,
        )
    ]
    response = client.post(
        "/api/v1/memory/search",
        json={"query": "ramadan", "project": "content-creation"},
        headers=auth_headers,
    )
    data = response.json()
    assert data["total"] == 1
    assert data["results"][0]["content"] == "Ramadan trend"


def test_search_no_auth_403(client):
    response = client.post(
        "/api/v1/memory/search",
        json={"query": "test", "project": "p1"},
    )
    assert response.status_code == 403


# ── POST /api/v1/memory/batch ─────────────────────────────────────────────────

def test_batch_add_returns_201(client, auth_headers):
    response = client.post(
        "/api/v1/memory/batch",
        json={
            "project": "content-creation",
            "agent_id": "research_agent",
            "items": [
                {"content": "item 1", "project": "content-creation",
                 "agent_id": "research_agent", "category": "trend"},
                {"content": "item 2", "project": "content-creation",
                 "agent_id": "research_agent", "category": "brand"},
            ],
        },
        headers=auth_headers,
    )
    assert response.status_code == 201


def test_batch_add_response_shape(client, auth_headers):
    response = client.post(
        "/api/v1/memory/batch",
        json={
            "project": "content-creation",
            "agent_id": "research_agent",
            "items": [
                {"content": "x", "project": "content-creation", "agent_id": "research_agent"},
            ],
        },
        headers=auth_headers,
    )
    data = response.json()
    assert "memory_ids" in data
    assert "count" in data


# ── GET /api/v1/memory/export ─────────────────────────────────────────────────

def test_export_returns_200(client, auth_headers):
    response = client.get(
        "/api/v1/memory/export?project=content-creation",
        headers=auth_headers,
    )
    assert response.status_code == 200


def test_export_response_shape(client, auth_headers):
    response = client.get(
        "/api/v1/memory/export?project=content-creation",
        headers=auth_headers,
    )
    data = response.json()
    assert "memories" in data
    assert "project" in data
    assert data["project"] == "content-creation"


def test_export_missing_project_422(client, auth_headers):
    response = client.get("/api/v1/memory/export", headers=auth_headers)
    assert response.status_code == 422
