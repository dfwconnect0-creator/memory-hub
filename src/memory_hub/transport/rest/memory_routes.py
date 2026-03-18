"""Memory routes: add, search, batch, export, sync."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request

from memory_hub.models.requests import BatchAddRequest, MemoryAddRequest, SearchRequest
from memory_hub.models.responses import BatchAddResponse, MemoryAddResponse, SearchResponse
from memory_hub.services.memory_service import MemoryService
from memory_hub.transport.rest.deps import get_memory_service

router = APIRouter(tags=["memory"])


@router.post("/memory", status_code=201, response_model=MemoryAddResponse)
async def add_memory(
    body: MemoryAddRequest,
    service: MemoryService = Depends(get_memory_service),
) -> MemoryAddResponse:
    memory_id = await service.add(
        content=body.content,
        project=body.project,
        agent_id=body.agent_id,
        category=body.category,
        metadata=body.metadata,
    )
    return MemoryAddResponse(memory_id=memory_id)


@router.post("/memory/search", response_model=SearchResponse)
async def search_memories(
    body: SearchRequest,
    service: MemoryService = Depends(get_memory_service),
) -> SearchResponse:
    results = await service.search(
        query=body.query,
        project=body.project,
        agent_id=body.agent_id,
        limit=body.limit,
    )
    return SearchResponse(results=results, query=body.query, total=len(results))


@router.post("/memory/batch", status_code=201, response_model=BatchAddResponse)
async def batch_add_memories(
    body: BatchAddRequest,
    service: MemoryService = Depends(get_memory_service),
) -> BatchAddResponse:
    items = [
        {"content": item.content, "category": item.category.value}
        for item in body.items
    ]
    memory_ids = await service.batch_add(
        items=items,
        project=body.project,
        agent_id=body.agent_id,
    )
    return BatchAddResponse(memory_ids=memory_ids, count=len(memory_ids))


@router.post("/sync")
async def trigger_sync(request: Request) -> dict[str, Any]:
    """Trigger a manual backup of local memories to Qdrant Cloud. Master key only."""
    if getattr(request.state, "agent_id", None) != "hub":
        raise HTTPException(status_code=403, detail="Master key required")

    sync_service = getattr(request.app.state, "sync", None)
    if sync_service is None:
        raise HTTPException(status_code=503, detail="Sync service not configured")

    if not sync_service.can_sync():
        raise HTTPException(status_code=400, detail="Cloud credentials not configured")

    result: dict[str, Any] = await sync_service.sync()
    return result


@router.get("/memory/export")
async def export_memories(
    project: str,
    service: MemoryService = Depends(get_memory_service),
) -> dict:  # type: ignore[type-arg]
    memories = await service.export(project=project)
    return {
        "project": project,
        "memories": [m.model_dump() for m in memories],
        "count": len(memories),
    }
