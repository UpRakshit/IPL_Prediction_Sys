from fastapi import APIRouter, Depends, HTTPException

from ipl_predictor.api.dependencies import get_live_match_service
from ipl_predictor.services.live_match_service import LiveMatchService

router = APIRouter(tags=["predictions"])


@router.get("/api/predictions/{match_id}/next-over")
@router.get("/matches/{match_id}/next-over", include_in_schema=False)
async def next_over_forecast(match_id: str, service: LiveMatchService = Depends(get_live_match_service)):
    try:
        return await service.next_over_forecast(match_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Match not found") from exc


@router.get("/api/predictions/{match_id}/win-probability")
@router.get("/predict/{match_id}", include_in_schema=False)
async def win_probability(match_id: str, service: LiveMatchService = Depends(get_live_match_service)):
    try:
        center = await service.match_center(match_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Match not found") from exc
    return {
        "match": center.match,
        "prediction": {
            "team": center.forecast.batting_team,
            "win_probability": center.forecast.win_probability,
        },
        "next_over": center.forecast,
        "model_note": "Rule-based v0 engine; replaceable with trained ML model.",
    }
