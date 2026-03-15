"""MemoryService: scoped memory operations (add, search, batch)."""
from __future__ import annotations

from memory_hub.interfaces.memory_store import MemoryStore
from memory_hub.models.domain import MemoryCategory, MemoryEntry, SearchResult


class MemoryService:
    """Business logic layer for memory operations. Injects scoping on every call."""

    def __init__(self, store: MemoryStore) -> None:
        self._store = store

    async def add(
        self,
        content: str,
        project: str,
        agent_id: str,
        category: MemoryCategory = MemoryCategory.GENERAL,
        metadata: dict[str, str] | None = None,
    ) -> str:
        """Add a memory scoped to project + agent_id. Returns the memory ID."""
        entry = MemoryEntry(
            content=content,
            project=project,
            agent_id=agent_id,
            category=category,
            metadata=metadata or {},
        )
        return await self._store.add(entry)

    async def search(
        self,
        query: str,
        project: str,
        agent_id: str | None = None,
        limit: int = 10,
    ) -> list[SearchResult]:
        """Search memories scoped to a project (and optionally an agent)."""
        return await self._store.search(
            query=query, project=project, agent_id=agent_id, limit=limit
        )

    async def batch_add(
        self,
        items: list[dict[str, str]],
        project: str,
        agent_id: str,
    ) -> list[str]:
        """Add multiple memories. Each item must have 'content' and optionally 'category'."""
        results: list[str] = []
        for item in items:
            category = MemoryCategory(item.get("category", "general"))
            memory_id = await self.add(
                content=item["content"],
                project=project,
                agent_id=agent_id,
                category=category,
            )
            results.append(memory_id)
        return results

    async def delete(self, memory_id: str) -> bool:
        """Delete a single memory by ID."""
        return await self._store.delete(memory_id)

    async def export(self, project: str) -> list[MemoryEntry]:
        """Export all memories for a project."""
        return await self._store.export(project)
