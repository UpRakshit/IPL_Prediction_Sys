from functools import lru_cache

from fastapi import Depends

from ipl_predictor.cache.base import Cache
from ipl_predictor.cache.factory import build_cache
from ipl_predictor.config import Settings, get_settings
from ipl_predictor.prediction.engine import RuleBasedPredictionEngine
from ipl_predictor.providers.base import CricketDataProvider
from ipl_predictor.providers.factory import build_provider
from ipl_predictor.services.live_match_service import LiveMatchService
from ipl_predictor.services.season_service import SeasonService


@lru_cache
def get_cache_singleton() -> Cache:
    return build_cache(get_settings())


def get_cache() -> Cache:
    return get_cache_singleton()


def get_provider(
    settings: Settings = Depends(get_settings), cache: Cache = Depends(get_cache)
) -> CricketDataProvider:
    return build_provider(settings, cache)


def get_prediction_engine() -> RuleBasedPredictionEngine:
    return RuleBasedPredictionEngine()


def get_live_match_service(
    provider: CricketDataProvider = Depends(get_provider),
    predictor: RuleBasedPredictionEngine = Depends(get_prediction_engine),
) -> LiveMatchService:
    return LiveMatchService(provider, predictor)


def get_season_service(provider: CricketDataProvider = Depends(get_provider)) -> SeasonService:
    return SeasonService(provider)
