from typing import Protocol

from ipl_predictor.live.schemas import Match


class MatchRepository(Protocol):
    async def upsert_match(self, match: Match, raw_payload: dict) -> None:
        """Persist normalized match data and provider payload."""

    async def list_matches(self, series_id: str | None = None) -> list[Match]:
        """Return persisted season matches."""


class PredictionRepository(Protocol):
    async def save_prediction(self, match_id: str, prediction: dict) -> None:
        """Persist one prediction snapshot."""
