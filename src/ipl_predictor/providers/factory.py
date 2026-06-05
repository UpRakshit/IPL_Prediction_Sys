from ipl_predictor.cache.base import Cache
from ipl_predictor.config import Settings
from ipl_predictor.providers.base import CricketDataProvider
from ipl_predictor.providers.cricapi import CricApiProvider
from ipl_predictor.providers.espn import ESPNProvider
from ipl_predictor.providers.simulation import SimulationProvider


def build_provider(settings: Settings, cache: Cache) -> CricketDataProvider:
    provider = settings.live_provider.lower()

    if provider == "simulation":
        return SimulationProvider()

    if provider == "espn":
        return ESPNProvider(cache)

    if provider in {"cricapi", "cricketdata"}:
        if not settings.cricapi_api_key:
            # No credentials — use ESPN real data (no key required)
            return ESPNProvider(cache)
        return CricApiProvider(settings, cache)

    raise ValueError(f"Unsupported LIVE_PROVIDER={settings.live_provider!r}")
