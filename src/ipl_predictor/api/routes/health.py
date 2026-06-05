from fastapi import APIRouter, Depends

from ipl_predictor.config import Settings, get_settings

router = APIRouter(tags=["health"])


@router.get("/health")
async def health(settings: Settings = Depends(get_settings)) -> dict:
    return {
        "status": "ok",
        "provider": settings.live_provider,
        "provider_configured": bool(settings.cricapi_api_key or settings.entitysport_api_key),
        "database_configured": bool(settings.database_url),
        "redis_configured": bool(settings.redis_url),
    }
