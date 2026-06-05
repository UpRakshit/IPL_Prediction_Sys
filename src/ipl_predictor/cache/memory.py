import time
from dataclasses import dataclass


@dataclass
class CacheItem:
    value: dict | list
    expires_at: float


class InMemoryCache:
    def __init__(self) -> None:
        self._items: dict[str, CacheItem] = {}

    async def get_json(self, key: str) -> dict | list | None:
        item = self._items.get(key)
        if not item:
            return None
        if item.expires_at <= time.time():
            self._items.pop(key, None)
            return None
        return item.value

    async def set_json(self, key: str, value: dict | list, ttl_seconds: int) -> None:
        self._items[key] = CacheItem(value=value, expires_at=time.time() + ttl_seconds)
