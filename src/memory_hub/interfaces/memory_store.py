"""Protocol contract for any memory storage backend."""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from memory_hub.models.domain import MemoryEntry, SearchResult


@runtime_checkable
class MemoryStore(Protocol):
    """Any class implementing these methods can be used as a memory backend."""

    async def add(self, entry: MemoryEntry) -> str:
        """Store a memory. Returns its ID."""
        ...

    async def search(
        self,
        query: str,
        project: str,
        agent_id: str | None = None,
        limit: int = 10,
    ) -> list[SearchResult]:
        """Search memories within a project scope."""
        ...

    async def delete(self, memory_id: str) -> bool:
        """Delete a memory by ID. Returns True if deleted."""
        ...

    async def export(self, project: str) -> list[MemoryEntry]:
        """Export all memories for a project."""
        ...
