# IPL Prediction Platform

Production-oriented backend for a Cricbuzz-style cricket app with live match data, season history, and real-time prediction.

## Architecture

- **Frontend target:** Next.js App Router + Tailwind CSS. The current static UI is kept only as a temporary local shell.
- **Backend:** FastAPI service layer, ready for Next.js to consume through backend APIs.
- **Live provider:** CricAPI / CricketData.org via backend proxy. The frontend never calls the provider directly.
- **Caching:** In-memory TTL cache now; Redis can be added behind `cache.factory` without changing routes.
- **Database:** PostgreSQL schema in `db/schema.sql` for matches, teams, players, ball-by-ball data, predictions, points table, and player stats.
- **Prediction:** Rule-based v0 engine in `src/ipl_predictor/prediction/engine.py`, designed to be replaced by a trained ML model later.

## Folder Structure

```text
src/ipl_predictor/
  api/
    app.py
    dependencies.py
    routes/
      health.py
      matches.py
      predictions.py
      season.py
  cache/
    base.py
    memory.py
    factory.py
  providers/
    base.py
    cricapi.py
    factory.py
  services/
    live_match_service.py
    season_service.py
    normalizers.py
  prediction/
    engine.py
  repositories/
    interfaces.py
db/
  schema.sql
```

## Environment

```bash
LIVE_PROVIDER=cricapi
CRICAPI_BASE_URL=https://api.cricapi.com/v1
CRICAPI_API_KEY=
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/ipl_predictor
REDIS_URL=
CACHE_TTL_LIVE_SECONDS=15
CACHE_TTL_SEASON_SECONDS=300
LIVE_POLL_SECONDS=20
```

## Run

```bash
source .venv/bin/activate
uvicorn ipl_predictor.api.app:app --reload
```

Open:

- Backend app shell: `http://127.0.0.1:8000`
- API docs: `http://127.0.0.1:8000/docs`
- Health: `http://127.0.0.1:8000/health`

## Run The Next.js Web App

```bash
cd apps/web
npm install
npm run dev
```

Open:

- Live match page: `http://127.0.0.1:3000`
- Next.js backend proxy: `http://127.0.0.1:3000/api/live/match`

The live page renders matches in this order:

1. Live match
2. Most recent completed match
3. Next upcoming match
4. Quiet empty state

## Backend Endpoints

```text
GET /api/matches/current
GET /api/matches/current-or-next
GET /api/matches/{match_id}
GET /api/matches/{match_id}/center
GET /api/matches/{match_id}/squads
GET /api/predictions/{match_id}/next-over
GET /api/predictions/{match_id}/win-probability
GET /api/season/matches
GET /api/season/points-table
GET /api/players/stats
```

## Notes

When provider credentials are unavailable, live endpoints return empty responses instead of hardcoded matches. Configure `CRICAPI_API_KEY` in `.env` to enable real current match detection and scorecard fetching.
