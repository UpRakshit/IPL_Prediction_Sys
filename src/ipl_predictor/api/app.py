from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from ipl_predictor.api.routes import health, matches, predictions, season
from ipl_predictor.core.errors import AppError

STATIC_DIR = Path(__file__).with_name("static")


def create_app() -> FastAPI:
    app = FastAPI(
        title="IPL Prediction Platform API",
        version="0.2.0",
        description="Backend for live IPL scores, season history, and real-time prediction.",
    )
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.exception_handler(AppError)
    async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})

    @app.get("/", include_in_schema=False)
    async def web_app():
        return FileResponse(STATIC_DIR / "index.html")

    app.include_router(health.router)
    app.include_router(matches.router)
    app.include_router(predictions.router)
    app.include_router(season.router)
    return app


app = create_app()
