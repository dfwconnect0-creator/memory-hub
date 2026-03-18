"""Tests for sync_scheduler._seconds_until helper."""
from __future__ import annotations

from datetime import datetime

from memory_hub.services.sync_scheduler import _seconds_until


def test_seconds_until_future_today():
    # now=01:00, target=02:00 → 3600 seconds
    now = datetime(2026, 3, 18, 1, 0, 0)
    assert _seconds_until("02:00", now=now) == 3600.0


def test_seconds_until_past_today_schedules_tomorrow():
    # now=03:00, target=02:00 → 23 hours until tomorrow at 02:00
    now = datetime(2026, 3, 18, 3, 0, 0)
    assert _seconds_until("02:00", now=now) == 23 * 3600.0


def test_seconds_until_same_time_schedules_tomorrow():
    # now exactly equals target → schedule 24h later
    now = datetime(2026, 3, 18, 2, 0, 0)
    assert _seconds_until("02:00", now=now) == 24 * 3600.0


def test_seconds_until_midnight_target():
    # now=23:00, target=00:00 → 1 hour
    now = datetime(2026, 3, 18, 23, 0, 0)
    assert _seconds_until("00:00", now=now) == 3600.0
