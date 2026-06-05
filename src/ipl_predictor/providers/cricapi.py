import httpx

from ipl_predictor.cache.base import Cache
from ipl_predictor.config import Settings
from ipl_predictor.core.errors import ProviderError, ProviderNotConfiguredError
from ipl_predictor.providers.base import CricketDataProvider


class CricApiProvider(CricketDataProvider):
    """CricAPI/CricketData.org adapter.

    The provider is intentionally raw: it returns provider dictionaries and lets the
    service layer normalize them for our app. This keeps endpoint-specific changes isolated.
    """

    def __init__(self, settings: Settings, cache: Cache) -> None:
        self.base_url = settings.cricapi_base_url.rstrip("/")
        self.api_key = settings.cricapi_api_key
        self.cache = cache
        self.live_ttl = settings.cache_ttl_live_seconds
        self.season_ttl = settings.cache_ttl_season_seconds

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    async def current_matches(self) -> list[dict]:
        payload = await self._get("currentMatches", ttl_seconds=self.live_ttl, offset="0")
        return self._data_list(payload)

    async def match_info(self, match_id: str) -> dict | None:
        payload = await self._get("match_info", ttl_seconds=self.live_ttl, id=match_id)
        data = payload.get("data") if isinstance(payload, dict) else None
        return data if isinstance(data, dict) else None

    async def match_scorecard(self, match_id: str) -> dict | None:
        payload = await self._get("match_scorecard", ttl_seconds=self.live_ttl, id=match_id)
        data = payload.get("data") if isinstance(payload, dict) else None
        return data if isinstance(data, dict) else None

    async def series_matches(self, series_id: str | None = None) -> list[dict]:
        params = {"id": series_id} if series_id else {}
        payload = await self._get("series_info", ttl_seconds=self.season_ttl, **params)
        data = payload.get("data") if isinstance(payload, dict) else None
        if isinstance(data, dict):
            matches = data.get("matchList") or data.get("matches") or []
            return matches if isinstance(matches, list) else []
        return self._data_list(payload)

    async def player_stats(self, player_id: str | None = None) -> list[dict]:
        if not player_id:
            return []
        payload = await self._get("players_info", ttl_seconds=self.season_ttl, id=player_id)
        data = payload.get("data") if isinstance(payload, dict) else None
        return [data] if isinstance(data, dict) else []

    async def _get(self, endpoint: str, ttl_seconds: int, **params: str | None) -> dict:
        if not self.configured:
            raise ProviderNotConfiguredError("Live cricket provider is not configured")

        query = {"apikey": self.api_key, **{k: v for k, v in params.items() if v is not None}}
        cache_key = f"cricapi:{endpoint}:{sorted(query.items())}"
        cached = await self.cache.get_json(cache_key)
        if isinstance(cached, dict):
            return cached

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.get(f"{self.base_url}/{endpoint}", params=query)
                response.raise_for_status()
                payload = response.json()
        except httpx.HTTPError as exc:
            raise ProviderError(str(exc)) from exc

        if isinstance(payload, dict):
            await self.cache.set_json(cache_key, payload, ttl_seconds)
            return payload
        raise ProviderError("Provider returned non-JSON object")

    @staticmethod
    def _data_list(payload: dict) -> list[dict]:
        data = payload.get("data")
        return data if isinstance(data, list) else []
