"""DualMemoryService: writes to both mem0 and Cognee simultaneously.

mem0 is the primary backend (fast, returns IDs immediately).
Cognee is the secondary backend (deep knowledge graph, fire-and-forget).
Search merges results from both backends, deduplicating by content similarity.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from memory_hub.interfaces.memory_store import MemoryStore
from memory_hub.models.domain import MemoryCategory, MemoryEntry, SearchResult
from memory_hub.services.memory_service import MemoryService

logger = logging.getLogger(__name__)


class DualMemoryService(MemoryService):
    """Extends MemoryService to write to both mem0 (fast) and Cognee (deep).

    - add(): writes to mem0 first (returns ID fast), then fires Cognee in background
    - search(): queries both backends and merges results
    - delete/export: delegates to mem0 (primary)
    """

    def __init__(
        self,
        mem0_store: MemoryStore,
        cognee_store: MemoryStore,
    ) -> None:
        # Primary backend — all MemoryService methods delegate to this
        super().__init__(store=mem0_store)
        self._cognee_store = cognee_store

    async def add(
        self,
        content: str,
        project: str,
        agent_id: str,
        category: MemoryCategory = MemoryCategory.GENERAL,
        metadata: dict[str, str] | None = None,
    ) -> str:
        """Add to mem0 (fast), fire-and-forget to Cognee."""
        # 1. Write to mem0 — returns immediately
        memory_id = await super().add(
            content=content,
            project=project,
            agent_id=agent_id,
            category=category,
            metadata=metadata,
        )

        # 2. Fire-and-forget: ingest into Cognee knowledge graph
        entry = MemoryEntry(
            content=content,
            project=project,
            agent_id=agent_id,
            category=category,
            metadata=metadata or {},
        )
        asyncio.create_task(self._safe_cognee_add(entry))

        return memory_id

    async def _safe_cognee_add(self, entry: MemoryEntry) -> None:
        """Add to Cognee with error handling — never crashes the caller."""
        try:
            await self._cognee_store.add(entry)
            logger.info("Cognee add succeeded for: %.50s...", entry.content)
        except Exception as e:
            logger.warning("Cognee add failed (non-fatal): %s", e)

    async def search(
        self,
        query: str,
        project: str,
        agent_id: str | None = None,
        limit: int = 10,
    ) -> list[SearchResult]:
        """Search both backends and merge results."""
        # Run both searches in parallel
        mem0_task = super().search(
            query=query, project=project, agent_id=agent_id, limit=limit
        )
        cognee_task = self._safe_cognee_search(
            query=query, project=project, agent_id=agent_id, limit=limit
        )

        mem0_results, cognee_results = await asyncio.gather(
            mem0_task, cognee_task
        )

        # Merge: mem0 results first (primary), then Cognee results
        merged = self._merge_results(mem0_results, cognee_results, limit)
        return merged

    async def _safe_cognee_search(
        self,
        query: str,
        project: str,
        agent_id: str | None = None,
        limit: int = 10,
    ) -> list[SearchResult]:
        """Search Cognee with error handling — returns empty on failure."""
        try:
            return await self._cognee_store.search(
                query=query, project=project, agent_id=agent_id, limit=limit
            )
        except Exception as e:
            logger.warning("Cognee search failed (non-fatal): %s", e)
            return []

    @staticmethod
    def _merge_results(
        primary: list[SearchResult],
        secondary: list[SearchResult],
        limit: int,
    ) -> list[SearchResult]:
        """Merge results from two backends, deduplicating by content.

        Primary results take priority. Secondary results are appended
        if their content doesn't overlap with primary results.
        """
        seen_content: set[str] = set()
        merged: list[SearchResult] = []

        # Add primary results first
        for r in primary:
            key = r.content.strip().lower()[:100]
            if key not in seen_content:
                seen_content.add(key)
                merged.append(r)

        # Add secondary results that don't duplicate primary
        for r in secondary:
            if len(merged) >= limit:
                break
            key = r.content.strip().lower()[:100]
            if key not in seen_content:
                seen_content.add(key)
                merged.append(r)

        return merged[:limit]

    async def cognify(self) -> dict[str, Any]:
        """Explicitly trigger Cognee's cognify pipeline.

        This is exposed as a separate action because cognify can be slow
        and GPU-intensive (uses Ollama for entity extraction).
        """
        if hasattr(self._cognee_store, "cognify"):
            result: dict[str, Any] = await self._cognee_store.cognify()  # type: ignore[union-attr]
            return result
        return {"status": "error", "message": "Cognee store has no cognify method"}
