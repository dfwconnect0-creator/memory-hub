"""FastAPI app factory with lifespan dependency wiring."""
from __future__ import annotations

import asyncio
import contextlib
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
    sync_service: Any | None = None,
) -> FastAPI:
    """App factory.

    In production call with no args — services are built from .env + agents.yaml.
    In tests pass pre-built mocks to avoid external dependencies.
    """
    _registry = registry or _build_registry()
    _memory_service = memory_service  # resolved lazily in lifespan if None
    _sync_service = sync_service  # wired in Phase 4 for production; passed explicitly in tests

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> Any:
        stop_event: asyncio.Event | None = None
        scheduler_task: asyncio.Task | None = None  # type: ignore[type-arg]

        # Wire services into app.state so route deps can access them
        app.state.registry = _registry
        app.state.health = HealthService(registry=_registry)
        app.state.sync = _sync_service  # may be overridden below in production

        if _memory_service is not None:
            # Test path: use injected mock, no scheduler
            app.state.memory = _memory_service
        else:
            # Production path: build from .env + start scheduler
            from memory_hub.adapters.mem0_adapter import Mem0Adapter
            from memory_hub.config import Settings
            from memory_hub.services.sync_scheduler import start_sync_scheduler
            from memory_hub.services.sync_service import SyncService

            settings = Settings()  # type: ignore[call-arg]
            app.state.settings = settings
            mem0_store = Mem0Adapter(settings)

            if settings.COGNEE_ENABLED and settings.COGNEE_DUAL_WRITE:
                from memory_hub.adapters.cognee_adapter import CogneeAdapter
                from memory_hub.services.dual_memory_service import DualMemoryService

                cognee_store = CogneeAdapter(settings)
                app.state.memory = DualMemoryService(
                    mem0_store=mem0_store,
                    cognee_store=cognee_store,
                )
                app.state.cognee_store = cognee_store  # for direct access
            else:
                app.state.memory = MemoryService(store=mem0_store)

            # Wire production sync service — inject existing qdrant client to avoid
            # opening a second file-locked handle on the same storage path.
            sync_svc = SyncService(settings, local_client=mem0_store.qdrant_client)
            app.state.sync = sync_svc

            if settings.SYNC_ENABLED and sync_svc.can_sync():
                stop_event = asyncio.Event()
                scheduler_task = asyncio.create_task(
                    start_sync_scheduler(sync_svc, settings.SYNC_SCHEDULE, stop_event)
                )

        yield

        # Shutdown: stop scheduler gracefully
        if scheduler_task is not None and not scheduler_task.done():
            if stop_event is not None:
                stop_event.set()
            scheduler_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await scheduler_task

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

    settings = Settings()  # type: ignore[call-arg]
    agents_data = load_agents_config(settings.AGENTS_YAML_PATH)
    return RegistryService(settings=settings, agents_data=agents_data)
