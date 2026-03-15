"""Auth middleware: validates X-API-Key header on every request."""
from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from memory_hub.interfaces.agent_registry import AgentRegistry

# Paths that bypass auth
_PUBLIC_PATHS = {"/health", "/api/v1/health"}


class AuthMiddleware(BaseHTTPMiddleware):
    """Rejects requests missing or with invalid X-API-Key header."""

    def __init__(self, app, registry: AgentRegistry) -> None:
        super().__init__(app)
        self._registry = registry

    async def dispatch(self, request: Request, call_next) -> Response:  # type: ignore[override]
        if request.url.path in _PUBLIC_PATHS:
            return await call_next(request)

        api_key = request.headers.get("X-API-Key")
        if not api_key:
            return JSONResponse(
                {"message": "Missing X-API-Key header", "code": "MISSING_AUTH"},
                status_code=403,
            )

        agent_id = self._registry.validate_key(api_key)
        if agent_id is None:
            return JSONResponse(
                {"message": "Invalid API key", "code": "INVALID_AUTH"},
                status_code=403,
            )

        request.state.agent_id = agent_id
        return await call_next(request)
