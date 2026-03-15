"""Protocol contract for health check implementations."""
from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class HealthCheck(Protocol):
    """Contract for health and metrics reporting."""

    async def check_health(self) -> dict[str, Any]:
        """Return health status dict. Must include 'status' key."""
        ...

    async def get_metrics(self) -> dict[str, Any]:
        """Return runtime metrics (memory usage, request counts, etc.)."""
        ...
