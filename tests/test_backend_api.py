from fastapi.testclient import TestClient

from ipl_predictor.api.app import app
from ipl_predictor.api.dependencies import get_live_match_service, get_season_service
from ipl_predictor.live.schemas import Match, Team
from ipl_predictor.prediction.engine import PredictionContext, RuleBasedPredictionEngine
from ipl_predictor.providers.base import CricketDataProvider
from ipl_predictor.services.live_match_service import LiveMatchService
from ipl_predictor.services.season_service import SeasonService


class FakeProvider(CricketDataProvider):
    async def current_matches(self) -> list[dict]:
        return [
            {
                "id": "fixture-1",
                "name": "Gujarat Titans vs Rajasthan Royals",
                "matchType": "t20",
                "status": "live",
                "venue": "New Chandigarh",
                "dateTimeGMT": "2026-05-29T14:00:00",
                "teams": ["Gujarat Titans", "Rajasthan Royals"],
                "score": [{"r": 47, "w": 1, "o": 5.0, "inning": "Gujarat Titans Inning 1"}],
            }
        ]

    async def match_info(self, match_id: str) -> dict | None:
        if match_id != "fixture-1":
            return None
        return (await self.current_matches())[0]

    async def match_scorecard(self, match_id: str) -> dict | None:
        if match_id != "fixture-1":
            return None
        return {
            "id": "fixture-1",
            "scorecard": [
                {
                    "inning": "Gujarat Titans Inning 1",
                    "totals": {"R": 47, "W": 1, "O": 5.0, "RR": 9.4},
                    "batting": [
                        {"batsman": {"id": "gill", "name": "Shubman Gill"}, "r": 25, "b": 17, "4s": 3, "6s": 1, "sr": 147.06},
                        {"batsman": {"id": "buttler", "name": "Jos Buttler"}, "r": 18, "b": 12, "4s": 2, "6s": 1, "sr": 150.0},
                    ],
                    "bowling": [
                        {"bowler": {"id": "archer", "name": "Jofra Archer"}, "o": 2.0, "m": 0, "r": 16, "w": 1, "eco": 8.0}
                    ],
                }
            ],
        }

    async def series_matches(self, series_id: str | None = None) -> list[dict]:
        return await self.current_matches()

    async def player_stats(self, player_id: str | None = None) -> list[dict]:
        return [{"player_id": player_id or "gill", "runs": 600}]


def fake_live_service() -> LiveMatchService:
    return LiveMatchService(FakeProvider(), RuleBasedPredictionEngine())


def fake_season_service() -> SeasonService:
    return SeasonService(FakeProvider())


def test_health_reports_provider_configuration_state():
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["provider"] == "cricapi"


def test_current_matches_use_service_layer():
    app.dependency_overrides[get_live_match_service] = fake_live_service
    client = TestClient(app)

    response = client.get("/api/matches/current")

    app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json()[0]["id"] == "fixture-1"


def test_match_center_returns_scorecard_and_prediction():
    app.dependency_overrides[get_live_match_service] = fake_live_service
    client = TestClient(app)

    response = client.get("/api/matches/fixture-1/center")

    app.dependency_overrides.clear()
    body = response.json()
    assert response.status_code == 200
    assert body["innings"][0]["runs"] == 47
    assert body["forecast"]["expected_runs"] > 0
    # feature_importance is now dynamic per phase; assert structure rather than exact keys
    fi = body["forecast"]["feature_importance"]
    assert len(fi) >= 3, "forecast should expose at least 3 feature importance entries"
    assert abs(sum(fi.values()) - 1.0) < 0.05, "feature importance weights should sum to ~1.0"


def test_season_points_table_endpoint_is_available():
    app.dependency_overrides[get_season_service] = fake_season_service
    client = TestClient(app)

    response = client.get("/api/season/points-table")

    app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json()[0]["team"]["name"] == "Gujarat Titans"


def test_web_app_is_served():
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    assert "CricketAI Match Centre" in response.text


def test_prediction_engine_never_returns_out_of_range_probability():
    engine = RuleBasedPredictionEngine()
    match = Match(
        id="m1",
        name="A vs B",
        status="live",
        teams=[Team(id="a", name="A"), Team(id="b", name="B")],
    )

    forecast = engine.predict(PredictionContext(match=match, runs=120, wickets=8, overs=15.0))

    assert 0 <= forecast.win_probability <= 1
