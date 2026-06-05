from typing import Protocol


class Cache(Protocol):
    async def get_json(self, key: str) -> dict | list | None:
        """Return cached JSON-compatible data."""

    async def set_json(self, key: str, value: dict | list, ttl_seconds: int) -> None:
        """Cache JSON-compatible data for a TTL."""
