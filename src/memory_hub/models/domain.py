"""Domain models: core entities shared across all layers."""
from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class MemoryCategory(StrEnum):
    TREND = "trend"
    BRAND = "brand"
    CAMPAIGN = "campaign"
    AUDIENCE = "audience"
    CAREER = "career"
    TASK = "task"
    CODE = "code"
    GENERAL = "general"


class AgentPermissions(BaseModel):
    read_shared: bool = True
    write_shared: bool = True


class AgentConfig(BaseModel):
    name: str
    framework: str
    project: str
    role: str
    other_mcps: list[str] = Field(default_factory=list)
    permissions: AgentPermissions = Field(default_factory=AgentPermissions)


class MemoryEntry(BaseModel):
    """A single memory unit to be stored."""

    content: str
    project: str
    agent_id: str
    category: MemoryCategory = MemoryCategory.GENERAL
    metadata: dict[str, str] = Field(default_factory=dict)


class SearchResult(BaseModel):
    """A memory retrieved from the store."""

    id: str
    content: str
    project: str
    agent_id: str
    score: float
    category: MemoryCategory = MemoryCategory.GENERAL
    metadata: dict[str, str] = Field(default_factory=dict)
    created_at: datetime | None = None
