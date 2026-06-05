from ipl_predictor.cache.base import Cache
from ipl_predictor.cache.memory import InMemoryCache
from ipl_predictor.config import Settings


def build_cache(settings: Settings) -> Cache:
    # Redis can be added behind this factory without changing services or routes.
    # The in-memory adapter keeps local development and tests dependency-light.
    return InMemoryCache()
