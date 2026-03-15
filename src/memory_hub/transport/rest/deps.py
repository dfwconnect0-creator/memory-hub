"""FastAPI dependency injection helpers — extract services from app.state."""
from __future__ import annotations

from fastapi import Request

from memory_hub.services.health_service import HealthService
from memory_hub.services.memory_service import MemoryService
from memory_hub.services.registry_service import RegistryService


def get_memory_service(request: Request) -> MemoryService:
    return request.app.state.memory  # type: ignore[no-any-return]


def get_registry(request: Request) -> RegistryService:
    return request.app.state.registry  # type: ignore[no-any-return]


def get_health_service(request: Request) -> HealthService:
    return request.app.state.health  # type: ignore[no-any-return]
