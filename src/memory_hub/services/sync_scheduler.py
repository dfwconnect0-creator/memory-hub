"""Sync scheduler: runs nightly local-to-cloud backup at a configured time."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from memory_hub.services.sync_service import SyncService

logger = logging.getLogger(__name__)


def _seconds_until(time_str: str, now: datetime | None = None) -> float:
    """Return seconds until the next occurrence of time_str (HH:MM, 24h).

    If the target time has already passed today, schedules for tomorrow.
    """
    if now is None:
        now = datetime.now()
    h, m = (int(x) for x in time_str.split(":"))
    target = now.replace(hour=h, minute=m, second=0, microsecond=0)
    if target <= now:
        target += timedelta(days=1)
    return (target - now).total_seconds()


async def start_sync_scheduler(
    sync_service: SyncService,
    schedule_time_str: str,
    stop_event: asyncio.Event,
) -> None:
    """Loop forever, waking at schedule_time_str each day to run sync."""
    logger.info("Sync scheduler started, daily schedule: %s", schedule_time_str)
    while not stop_event.is_set():
        seconds = _seconds_until(schedule_time_str)
        logger.info(
            "Next sync scheduled in %.0f seconds (%.2f hours)",
            seconds,
            seconds / 3600,
        )

        # Wait in 60-second chunks so shutdown is responsive
        while seconds > 0 and not stop_event.is_set():
            chunk = min(60.0, seconds)
            await asyncio.sleep(chunk)
            seconds -= chunk

        if stop_event.is_set():
            break

        logger.info("Running scheduled sync...")
        try:
            result = await sync_service.sync()
            logger.info("Scheduled sync result: %s", result)
        except Exception as e:
            logger.exception("Scheduled sync raised unexpectedly: %s", e)

    logger.info("Sync scheduler stopped")
