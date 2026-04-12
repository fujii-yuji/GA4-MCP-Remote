"""Process-wide semaphore registry (initialized from ASGI lifespan)."""

from __future__ import annotations

from ga4_remote_mcp.config.settings import Settings
from ga4_remote_mcp.policy.semaphores import PropertySemaphoreRegistry

_registry: PropertySemaphoreRegistry | None = None


def init_property_semaphores(settings: Settings) -> None:
    global _registry
    _registry = PropertySemaphoreRegistry(settings)


def get_property_semaphores() -> PropertySemaphoreRegistry:
    if _registry is None:
        msg = "PropertySemaphoreRegistry not initialized"
        raise RuntimeError(msg)
    return _registry
