"""Response models for the Memory Hub API."""
from __future__ import annotations

from pydantic import BaseModel

from memory_hub.models.domain import SearchResult


class MemoryAddResponse(BaseModel):
    memory_id: str
    status: str = "ok"


class SearchResponse(BaseModel):
    results: list[SearchResult]
    query: str
    total: int


class BatchAddResponse(BaseModel):
    memory_ids: list[str]
    count: int
    status: str = "ok"


class ErrorResponse(BaseModel):
    message: str
    code: str = "INTERNAL_ERROR"
    trace_id: str | None = None
