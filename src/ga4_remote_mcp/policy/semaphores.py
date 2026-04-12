"""Per-property concurrency limits."""

from __future__ import annotations

import asyncio

from ga4_remote_mcp.config.settings import Settings


class PropertySemaphoreRegistry:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._lock = asyncio.Lock()
        self._semaphores: dict[str, asyncio.Semaphore] = {}

    async def acquire(self, property_id: str) -> asyncio.Semaphore:
        async with self._lock:
            if property_id not in self._semaphores:
                n = self._settings.max_concurrent_per_property
                self._semaphores[property_id] = asyncio.Semaphore(n)
            return self._semaphores[property_id]
