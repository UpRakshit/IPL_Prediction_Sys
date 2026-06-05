from typing import Protocol


class CricketDataProvider(Protocol):
    async def current_matches(self) -> list[dict]:
        """Return live/recent/upcoming matches from the external provider."""

    async def match_info(self, match_id: str) -> dict | None:
        """Return provider match metadata."""

    async def match_scorecard(self, match_id: str) -> dict | None:
        """Return scorecard and innings data for a match."""

    async def series_matches(self, series_id: str | None = None) -> list[dict]:
        """Return season or series matches."""

    async def player_stats(self, player_id: str | None = None) -> list[dict]:
        """Return player statistics when supported by the provider."""
