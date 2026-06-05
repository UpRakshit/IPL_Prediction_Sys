from ipl_predictor.live.schemas import Match
from ipl_predictor.providers.base import CricketDataProvider
from ipl_predictor.services.normalizers import match_from_provider


class SeasonService:
    def __init__(self, provider: CricketDataProvider) -> None:
        self.provider = provider

    async def matches(self, series_id: str | None = None) -> list[Match]:
        return [match_from_provider(raw) for raw in await self.provider.series_matches(series_id)]

    async def points_table(self, series_id: str | None = None) -> list[dict]:
        table: dict[str, dict] = {}
        for match in await self.matches(series_id):
            for team in match.teams:
                table.setdefault(
                    team.id,
                    {"team": team, "played": 0, "won": 0, "lost": 0, "points": 0, "net_run_rate": 0.0},
                )
            if match.result_summary and "won" in match.result_summary.lower():
                winner = next(
                    (team for team in match.teams if team.name.lower() in match.result_summary.lower()),
                    None,
                )
                if winner:
                    table[winner.id]["won"] += 1
                    table[winner.id]["points"] += 2
                    for team in match.teams:
                        table[team.id]["played"] += 1
                        if team.id != winner.id:
                            table[team.id]["lost"] += 1
        return sorted(table.values(), key=lambda row: (-row["points"], row["team"].name))

    async def player_stats(self, player_id: str | None = None) -> list[dict]:
        return await self.provider.player_stats(player_id)
