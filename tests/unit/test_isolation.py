"""Phase 2 — Cross-project isolation tests (RED phase)."""
from unittest.mock import AsyncMock

import pytest

from memory_hub.models.domain import MemoryCategory, SearchResult


@pytest.fixture
def mock_store():
    store = AsyncMock()
    store.add.return_value = "mem-456"
    store.search.return_value = []
    return store


async def test_add_tagged_with_correct_project(mock_store):
    from memory_hub.services.memory_service import MemoryService
    service = MemoryService(store=mock_store)
    await service.add(
        content="SEO keyword research", project="seo-audit", agent_id="seo_agent"
    )
    entry = mock_store.add.call_args[0][0]
    assert entry.project == "seo-audit"
    assert entry.agent_id == "seo_agent"


async def test_search_scoped_to_correct_project(mock_store):
    from memory_hub.services.memory_service import MemoryService
    service = MemoryService(store=mock_store)
    await service.search(query="ramadan", project="content-creation")
    call = mock_store.search.call_args
    # project kwarg must be "content-creation"
    project_passed = call[1].get("project") or (call[0][1] if len(call[0]) > 1 else None)
    assert project_passed == "content-creation"


async def test_project_a_search_does_not_bleed_into_project_b(mock_store):
    """Searching project B should never return project A memories."""
    # Store returns seo-audit memory when queried
    mock_store.search.return_value = [
        SearchResult(
            id="m1",
            content="content-creation memory",
            project="content-creation",
            agent_id="research_agent",
            score=0.95,
            category=MemoryCategory.TREND,
        )
    ]
    from memory_hub.services.memory_service import MemoryService
    service = MemoryService(store=mock_store)
    # The service must pass "seo-audit" as project — the store is responsible
    # for filtering, but the service must scope the call correctly
    await service.search(query="ramadan", project="seo-audit")
    call = mock_store.search.call_args
    project_passed = call[1].get("project") or (call[0][1] if len(call[0]) > 1 else None)
    # The service must NOT pass "content-creation" to the seo-audit search
    assert project_passed == "seo-audit"


async def test_different_agents_same_project(mock_store):
    """Two agents in same project — both tagged with their own agent_id."""
    from memory_hub.services.memory_service import MemoryService
    service = MemoryService(store=mock_store)
    await service.add(
        content="Research note", project="content-creation", agent_id="research_agent"
    )
    await service.add(content="Writing note", project="content-creation", agent_id="writer_agent")
    assert mock_store.add.call_count == 2
    entries = [call[0][0] for call in mock_store.add.call_args_list]
    assert entries[0].agent_id == "research_agent"
    assert entries[1].agent_id == "writer_agent"
    assert all(e.project == "content-creation" for e in entries)
