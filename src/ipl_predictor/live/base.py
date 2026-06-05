from abc import ABC, abstractmethod

from ipl_predictor.live.schemas import Match, MatchCenter, OverForecast, Squad


class LiveCricketClient(ABC):
    @abstractmethod
    async def current_matches(self) -> list[Match]:
        """Return current or upcoming matches relevant to prediction."""

    @abstractmethod
    async def match(self, match_id: str) -> Match:
        """Return one match by provider match id."""

    @abstractmethod
    async def squads(self, match_id: str) -> list[Squad]:
        """Return match squads or likely playing XIs."""

    @abstractmethod
    async def match_center(self, match_id: str) -> MatchCenter:
        """Return scorecard, commentary, squads, state, and forecast for a match."""

    @abstractmethod
    async def next_over_forecast(self, match_id: str) -> OverForecast:
        """Return prediction for the next over."""
