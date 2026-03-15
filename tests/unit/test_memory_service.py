"""Phase 2 — MemoryService tests (RED phase)."""
from unittest.mock import AsyncMock

import pytest


@pytest.fixture
def mock_store():
    store = AsyncMock()
    store.add.return_value = "mem-123"
    store.search.return_value = []
    store.delete.return_value = True
    return store


async def test_add_memory_scoped_to_project(mock_store):
    from memory_hub.services.memory_service import MemoryService
    service = MemoryService(store=mock_store)
    await service.add(
        content="Test memory", project="content-creation", agent_id="research_agent"
    )
    mock_store.add.assert_called_once()
    call_entry = mock_store.add.call_args[0][0]
    assert call_entry.project == "content-creation"
    assert call_entry.agent_id == "research_agent"


async def test_add_returns_memory_id(mock_store):
    from memory_hub.services.memory_service import MemoryService
    service = MemoryService(store=mock_store)
    result = await service.add(content="Test", project="p1", agent_id="a1")
    assert result == "mem-123"


async def test_search_passes_project_scope(mock_store):
    from memory_hub.services.memory_service import MemoryService
    service = MemoryService(store=mock_store)
    await service.search(query="ramadan", project="content-creation")
    mock_store.search.assert_called_once()
    call_kwargs = mock_store.search.call_args
    # project must be passed
    assert call_kwargs[1].get("project") == "content-creation" or (
        len(call_kwargs[0]) > 1 and call_kwargs[0][1] == "content-creation"
    )


async def test_search_returns_list(mock_store):
    from memory_hub.models.domain import MemoryCategory, SearchResult
    mock_store.search.return_value = [
        SearchResult(
            id="m1",
            content="Ramadan trend",
            project="content-creation",
            agent_id="research_agent",
            score=0.9,
            category=MemoryCategory.TREND,
        )
    ]
    from memory_hub.services.memory_service import MemoryService
    service = MemoryService(store=mock_store)
    results = await service.search(query="ramadan", project="content-creation")
    assert len(results) == 1
    assert results[0].content == "Ramadan trend"


async def test_add_sets_category(mock_store):
    from memory_hub.models.domain import MemoryCategory
    from memory_hub.services.memory_service import MemoryService
    service = MemoryService(store=mock_store)
    await service.add(
        content="SEO tip",
        project="seo-audit",
        agent_id="seo_agent",
        category=MemoryCategory.CODE,
    )
    call_entry = mock_store.add.call_args[0][0]
    assert call_entry.category == MemoryCategory.CODE


async def test_batch_add(mock_store):
    from memory_hub.services.memory_service import MemoryService
    service = MemoryService(store=mock_store)
    items = [
        {"content": "item 1", "category": "trend"},
        {"content": "item 2", "category": "brand"},
    ]
    results = await service.batch_add(
        items=items, project="content-creation", agent_id="research_agent"
    )
    assert mock_store.add.call_count == 2
    assert len(results) == 2
