from fastapi import APIRouter, Depends, HTTPException

from ipl_predictor.api.dependencies import get_live_match_service
from ipl_predictor.core.errors import ProviderNotConfiguredError
from ipl_predictor.services.live_match_service import LiveMatchService

router = APIRouter(tags=["matches"])


@router.get("/api/matches/current")
@router.get("/matches/current", include_in_schema=False)
async def current_matches(service: LiveMatchService = Depends(get_live_match_service)):
    try:
        return await service.current_matches()
    except ProviderNotConfiguredError:
        return []


@router.get("/api/matches/current-or-next")
async def current_or_next_match(service: LiveMatchService = Depends(get_live_match_service)):
    try:
        match = await service.current_or_next_match()
    except ProviderNotConfiguredError:
        return {"match": None}
    return {"match": match}


@router.get("/api/matches/{match_id}")
async def match(match_id: str, service: LiveMatchService = Depends(get_live_match_service)):
    try:
        return await service.match(match_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Match not found") from exc


@router.get("/api/matches/{match_id}/center")
@router.get("/matches/{match_id}/center", include_in_schema=False)
async def match_center(match_id: str, service: LiveMatchService = Depends(get_live_match_service)):
    try:
        return await service.match_center(match_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Match center not found") from exc


@router.get("/api/matches/{match_id}/squads")
@router.get("/matches/{match_id}/squads", include_in_schema=False)
async def match_squads(match_id: str, service: LiveMatchService = Depends(get_live_match_service)):
    try:
        return await service.squads(match_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Match not found") from exc
