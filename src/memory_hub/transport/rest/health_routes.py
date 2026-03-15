"""Health route: GET /health — public, no auth required."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from memory_hub.services.health_service import HealthService
from memory_hub.transport.rest.deps import get_health_service

router = APIRouter(tags=["health"])


@router.get("/health")
async def health(
    service: HealthService = Depends(get_health_service),
) -> dict[str, Any]:
    return await service.check_health()
