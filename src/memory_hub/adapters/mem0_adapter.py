"""Mem0Adapter: wraps mem0.Memory and implements the MemoryStore Protocol."""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any

from mem0 import Memory  # type: ignore[import-untyped]

from memory_hub.config import Settings
from memory_hub.models.domain import MemoryCategory, MemoryEntry, SearchResult

logger = logging.getLogger(__name__)


def _build_qdrant_config(settings: Settings) -> dict[str, Any]:
    """Return Qdrant vector-store config: always local (cloud is backup only)."""
    path = str(Path(settings.QDRANT_LOCAL_PATH).expanduser())
    logger.info("Qdrant: using local storage at %s", path)
    return {
        "collection_name": "memory_hub",
        "embedding_model_dims": 3072,
        "path": path,
    }


def _build_mem0_config(settings: Settings) -> dict[str, Any]:
    """Build mem0 config using Gemini for both LLM and embeddings (free tier)."""
    return {
        "llm": {
            "provider": "gemini",
            "config": {
                "model": "gemini-2.5-flash",
                "api_key": settings.GEMINI_API_KEY,
            },
        },
        "embedder": {
            "provider": "gemini",
            "config": {
                "model": "gemini-embedding-001",
                "embedding_dims": 3072,
                "api_key": settings.GEMINI_API_KEY,
            },
        },
        "vector_store": {
            "provider": "qdrant",
            "config": _build_qdrant_config(settings),
        },
    }


class Mem0Adapter:
    """Storage backend that delegates to mem0. Implements MemoryStore Protocol."""

    def __init__(self, settings: Settings) -> None:
        config = _build_mem0_config(settings)
        self._memory: Memory = Memory.from_config(config)

    @property
    def qdrant_client(self) -> Any:
        """Return the underlying QdrantClient held by mem0 (avoids opening a second lock)."""
        return self._memory.vector_store.client

    async def add(self, entry: MemoryEntry) -> str:
        """Store a memory scoped to project (user_id) + agent_id."""
        result = await asyncio.to_thread(
            self._memory.add,
            entry.content,
            user_id=entry.project,
            agent_id=entry.agent_id,
            metadata={**entry.metadata, "category": entry.category.value},
        )
        return self._extract_id(result)

    async def search(
        self,
        query: str,
        project: str,
        agent_id: str | None = None,
        limit: int = 10,
    ) -> list[SearchResult]:
        """Search memories within a project scope."""
        kwargs: dict[str, Any] = {"user_id": project, "limit": limit}
        if agent_id:
            kwargs["agent_id"] = agent_id

        raw = await asyncio.to_thread(self._memory.search, query, **kwargs)
        memories = raw if isinstance(raw, list) else raw.get("results", [])

        return [
            SearchResult(
                id=m.get("id", ""),
                content=m.get("memory", m.get("content", "")),
                project=project,
                agent_id=m.get("agent_id") or agent_id or "",
                score=m.get("score", 0.0),
                category=MemoryCategory(
                    m.get("metadata", {}).get("category", "general")
                ),
                metadata={
                    k: str(v)
                    for k, v in m.get("metadata", {}).items()
                    if k != "category"
                },
            )
            for m in memories
        ]

    async def delete(self, memory_id: str) -> bool:
        """Delete a memory by ID."""
        await asyncio.to_thread(self._memory.delete, memory_id)
        return True

    async def export(self, project: str) -> list[MemoryEntry]:
        """Export all memories for a project."""
        raw = await asyncio.to_thread(self._memory.get_all, user_id=project)
        memories = raw if isinstance(raw, list) else raw.get("results", [])

        return [
            MemoryEntry(
                content=m.get("memory", ""),
                project=project,
                agent_id=m.get("agent_id", ""),
                metadata={
                    k: str(v)
                    for k, v in m.get("metadata", {}).items()
                    if k != "category"
                },
                category=MemoryCategory(
                    m.get("metadata", {}).get("category", "general")
                ),
            )
            for m in memories
        ]

    @staticmethod
    def _extract_id(result: Any) -> str:
        """Extract memory ID from mem0's add() response."""
        if isinstance(result, dict):
            # {"results": [{"id": "...", ...}]}
            results = result.get("results", [])
            if results and isinstance(results[0], dict):
                return str(results[0].get("id", ""))
            return str(result.get("id", ""))
        if isinstance(result, list) and result:
            first = result[0]
            if isinstance(first, dict):
                return str(first.get("id", ""))
        return str(result)
