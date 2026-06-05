from fastapi import APIRouter, Depends

from ipl_predictor.api.dependencies import get_season_service
from ipl_predictor.core.errors import ProviderNotConfiguredError
from ipl_predictor.services.season_service import SeasonService

router = APIRouter(tags=["season"])


@router.get("/api/season/matches")
async def season_matches(
    series_id: str | None = None, service: SeasonService = Depends(get_season_service)
):
    try:
        return await service.matches(series_id)
    except ProviderNotConfiguredError:
        return []


@router.get("/api/season/points-table")
async def points_table(
    series_id: str | None = None, service: SeasonService = Depends(get_season_service)
):
    try:
        return await service.points_table(series_id)
    except ProviderNotConfiguredError:
        return []


@router.get("/api/players/stats")
async def player_stats(
    player_id: str | None = None, service: SeasonService = Depends(get_season_service)
):
    try:
        return await service.player_stats(player_id)
    except ProviderNotConfiguredError:
        return []
