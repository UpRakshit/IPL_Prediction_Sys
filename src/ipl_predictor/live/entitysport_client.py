import httpx

from ipl_predictor.live.base import LiveCricketClient
from ipl_predictor.live.schemas import (
    Match,
    MatchCenter,
    MatchState,
    OverForecast,
    Player,
    Squad,
    Team,
)


class EntitySportClient(LiveCricketClient):
    """Thin adapter for EntitySport.

    EntitySport endpoint paths vary by subscription/product version. Keep provider-specific
    mapping here so the API and ML code remain stable when the feed contract changes.
    """

    def __init__(self, base_url: str, api_key: str) -> None:
        if not api_key:
            raise ValueError("ENTITYSPORT_API_KEY is required for LIVE_PROVIDER=entitysport")
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key

    async def _get(self, path: str, **params: str) -> dict:
        query = {"token": self.api_key, **params}
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(f"{self.base_url}/{path.lstrip('/')}", params=query)
            response.raise_for_status()
            return response.json()

    async def current_matches(self) -> list[Match]:
        payload = await self._get("matches", status="live")
        return [self._parse_match(item) for item in payload.get("response", {}).get("items", [])]

    async def match(self, match_id: str) -> Match:
        payload = await self._get(f"matches/{match_id}/info")
        return self._parse_match(payload.get("response", {}))

    async def squads(self, match_id: str) -> list[Squad]:
        payload = await self._get(f"matches/{match_id}/squads")
        response = payload.get("response", {})
        squads: list[Squad] = []
        for item in response.get("squads", []):
            team = Team(
                id=str(item.get("team_id", "")),
                name=item.get("team_name", "Unknown team"),
                short_name=item.get("team_short_name"),
            )
            squads.append(Squad(team=team, players=[]))
        return squads

    async def match_center(self, match_id: str) -> MatchCenter:
        match = await self.match(match_id)
        squads = await self.squads(match_id)
        forecast = await self.next_over_forecast(match_id)
        batting_team = match.teams[0] if match.teams else Team(id="unknown", name="Unknown")
        bowling_team = match.teams[1] if len(match.teams) > 1 else batting_team
        placeholder = Player(id="unknown", name="Awaiting feed")
        return MatchCenter(
            match=match,
            status_line="Live scorecard mapping is not configured for this EntitySport plan yet.",
            state=MatchState(
                batting_team=batting_team,
                bowling_team=bowling_team,
                striker=placeholder,
                non_striker=placeholder,
                bowler=placeholder,
                current_run_rate=0,
                projected_score=0,
                last_event="Connect the scorecard and commentary endpoints for your API plan.",
            ),
            innings=[],
            squads=squads,
            commentary=[],
            forecast=forecast,
        )

    async def next_over_forecast(self, match_id: str) -> OverForecast:
        match = await self.match(match_id)
        batting_team = match.teams[0] if match.teams else Team(id="unknown", name="Unknown")
        bowling_team = match.teams[1] if len(match.teams) > 1 else batting_team
        return OverForecast(
            match_id=match_id,
            next_over="next over",
            batting_team=batting_team,
            bowling_team=bowling_team,
            expected_runs=8.0,
            run_range="5-11",
            wicket_probability=0.16,
            boundary_probability=0.34,
            dot_ball_probability=0.36,
            win_probability=0.5,
            momentum="Waiting for live score context",
            suggested_strategy="Connect ball-by-ball feed fields to unlock contextual suggestions.",
            factors=["Provider connected", "Scorecard parser pending", "Using neutral prior"],
        )

    @staticmethod
    def _parse_match(item: dict) -> Match:
        raw_teams = []
        for key in ("teama", "teamb"):
            value = item.get(key)
            if isinstance(value, dict):
                raw_teams.append(value)
            elif isinstance(value, list):
                raw_teams.extend(value)

        teams = [
            Team(
                id=str(team.get("team_id", team.get("tid", ""))),
                name=team.get("name", team.get("title", "Unknown team")),
                short_name=team.get("abbr"),
            )
            for team in raw_teams
            if isinstance(team, dict)
        ]
        return Match(
            id=str(item.get("match_id", item.get("id", ""))),
            name=item.get("title", item.get("subtitle", "Cricket match")),
            status=str(item.get("status_str", item.get("status", "unknown"))),
            series=item.get("competition", {}).get("title")
            if isinstance(item.get("competition"), dict)
            else None,
            match_number=item.get("subtitle"),
            venue=item.get("venue", {}).get("name") if isinstance(item.get("venue"), dict) else None,
            start_time_utc=item.get("date_start_utc"),
            teams=teams,
        )
