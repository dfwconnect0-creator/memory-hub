"""SyncService: copies local Qdrant collection to Qdrant Cloud as a backup."""
from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from memory_hub.config import Settings

logger = logging.getLogger(__name__)


class SyncService:
    """Copies local Qdrant collection to Qdrant Cloud as a backup."""

    def __init__(self, settings: Settings, local_client: QdrantClient | None = None) -> None:
        self._settings = settings
        # Injected client reuses the existing file-locked handle (avoids double-lock error).
        # Falls back to opening its own handle when running standalone (e.g. CLI / tests).
        self._local_client = local_client

    def can_sync(self) -> bool:
        """Return True only if cloud credentials are both non-empty."""
        return bool(self._settings.QDRANT_URL and self._settings.QDRANT_API_KEY)

    async def sync(self) -> dict[str, Any]:
        """Copy all local memory_hub points to Qdrant Cloud."""
        start = time.monotonic()
        settings = self._settings
        try:
            local_client = self._local_client or QdrantClient(
                path=str(Path(settings.QDRANT_LOCAL_PATH).expanduser())
            )
            cloud_client = QdrantClient(
                url=settings.QDRANT_URL,
                api_key=settings.QDRANT_API_KEY,
            )

            if not local_client.collection_exists("memory_hub"):
                logger.info("Sync skipped: local collection 'memory_hub' does not exist")
                return {
                    "status": "skipped",
                    "reason": "no local collection yet",
                    "points_synced": 0,
                }

            if not cloud_client.collection_exists("memory_hub"):
                logger.info("Cloud collection missing — creating it")
                cloud_client.recreate_collection(
                    collection_name="memory_hub",
                    vectors_config=VectorParams(size=3072, distance=Distance.COSINE),
                )

            total_synced = 0
            offset = None
            while True:
                points, next_offset = local_client.scroll(
                    collection_name="memory_hub",
                    limit=100,
                    offset=offset,
                    with_payload=True,
                    with_vectors=True,
                )
                if points:
                    # scroll() returns Record objects; upsert() requires PointStruct
                    structs = [
                        PointStruct(
                            id=p.id,
                            payload=p.payload or {},
                            vector=p.vector or {},
                        )
                        for p in points
                    ]
                    cloud_client.upsert(
                        collection_name="memory_hub",
                        points=structs,
                    )
                    total_synced += len(points)
                    logger.info("Synced batch of %d points", len(points))
                if next_offset is None:
                    break
                offset = next_offset

            elapsed = time.monotonic() - start
            logger.info(
                "Sync complete: %d points synced in %.2fs", total_synced, elapsed
            )
            return {
                "status": "ok",
                "points_synced": total_synced,
                "duration_seconds": round(elapsed, 2),
            }
        except Exception as e:
            logger.exception("Sync failed: %s", e)
            return {"status": "error", "message": str(e)}
