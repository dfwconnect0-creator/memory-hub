"""FastAPI app factory with lifespan dependency wiring."""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI

from memory_hub.middleware.auth import AuthMiddleware
from memory_hub.services.health_service import HealthService
from memory_hub.services.memory_service import MemoryService
from memory_hub.services.registry_service import RegistryService
from memory_hub.transport.rest.agent_routes import router as agent_router
from memory_hub.transport.rest.health_routes import router as health_router
from memory_hub.transport.rest.memory_routes import router as memory_router


def create_app(
    memory_service: MemoryService | None = None,
    registry: RegistryService | None = None,
) -> FastAPI:
    """App factory.

    In production call with no args — services are built from .env + agents.yaml.
    In tests pass pre-built mocks to avoid external dependencies.
    """
    _registry = registry or _build_registry()
    _memory_service = memory_service  # resolved lazily in lifespan if None

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> Any:
        # Wire services into app.state so route deps can access them
        app.state.registry = _registry
        app.state.health = HealthService(registry=_registry)

        if _memory_service is not None:
            app.state.memory = _memory_service
        else:
            from memory_hub.adapters.mem0_adapter import Mem0Adapter
            from memory_hub.config import Settings

            settings = Settings()
            app.state.memory = MemoryService(store=Mem0Adapter(settings))

        yield
        # Shutdown: nothing to clean up yet

    app = FastAPI(
        title="Memory Hub v5",
        version="0.1.0",
        description="Multi-agent persistent memory hub",
        lifespan=lifespan,
    )

    # Auth middleware — uses the eagerly-resolved registry
    app.add_middleware(AuthMiddleware, registry=_registry)

    # Routes
    app.include_router(memory_router, prefix="/api/v1")
    app.include_router(health_router, prefix="/api/v1")
    app.include_router(agent_router, prefix="/api/v1")

    return app


def _build_registry() -> RegistryService:
    """Create RegistryService from .env + agents.yaml (production path)."""
    from memory_hub.config import Settings, load_agents_config

    settings = Settings()
    agents_data = load_agents_config(settings.AGENTS_YAML_PATH)
    return RegistryService(settings=settings, agents_data=agents_data)
