from ipl_predictor.config import Settings
from ipl_predictor.live.base import LiveCricketClient
from ipl_predictor.live.entitysport_client import EntitySportClient


def build_live_client(settings: Settings) -> LiveCricketClient:
    provider = settings.live_provider.lower()
    if provider == "entitysport":
        return EntitySportClient(settings.entitysport_base_url, settings.entitysport_api_key)
    raise ValueError(
        "Legacy LiveCricketClient supports only EntitySport. Use providers.factory for CricAPI."
    )
