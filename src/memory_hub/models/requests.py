"""Request models for the Memory Hub API."""
from __future__ import annotations

from pydantic import BaseModel, Field

from memory_hub.models.domain import MemoryCategory


class MemoryAddRequest(BaseModel):
    content: str
    project: str
    agent_id: str
    category: MemoryCategory = MemoryCategory.GENERAL
    metadata: dict[str, str] = Field(default_factory=dict)


class SearchRequest(BaseModel):
    query: str
    project: str
    agent_id: str | None = None
    limit: int = 10


class BatchAddRequest(BaseModel):
    items: list[MemoryAddRequest]
    project: str
    agent_id: str
