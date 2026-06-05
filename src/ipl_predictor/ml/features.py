from dataclasses import dataclass

import pandas as pd

from ipl_predictor.live.schemas import Match, Squad


@dataclass(frozen=True)
class PredictionFeatures:
    venue_known: int
    toss_known: int
    batting_first_known: int
    squad_player_count_delta: int

    def as_frame(self) -> pd.DataFrame:
        return pd.DataFrame([self.__dict__])


def live_match_features(match: Match, squads: list[Squad]) -> PredictionFeatures:
    player_counts = {squad.team.id: len(squad.players) for squad in squads}
    first_count = player_counts.get(match.teams[0].id, 0) if match.teams else 0
    second_count = player_counts.get(match.teams[1].id, 0) if len(match.teams) > 1 else 0
    return PredictionFeatures(
        venue_known=int(bool(match.venue)),
        toss_known=int(bool(match.toss_winner_id)),
        batting_first_known=int(bool(match.batting_first_id)),
        squad_player_count_delta=first_count - second_count,
    )


def cricsheet_match_features(deliveries: pd.DataFrame) -> pd.DataFrame:
    required = {"match_id", "batting_team", "bowling_team", "runs_off_bat", "extras", "wides", "noballs"}
    missing = required - set(deliveries.columns)
    if missing:
        raise ValueError(f"Cricsheet CSV is missing required columns: {sorted(missing)}")

    frame = deliveries.copy()
    frame["total_runs"] = frame["runs_off_bat"].fillna(0) + frame["extras"].fillna(0)
    legal = frame["wides"].isna() & frame["noballs"].isna()
    frame["legal_ball"] = legal.astype(int)

    batting = (
        frame.groupby(["match_id", "batting_team"], as_index=False)
        .agg(team_runs=("total_runs", "sum"), legal_balls=("legal_ball", "sum"))
        .rename(columns={"batting_team": "team"})
    )
    bowling = (
        frame.groupby(["match_id", "bowling_team"], as_index=False)
        .size()
        .rename(columns={"bowling_team": "team", "size": "balls_bowled"})
    )
    return batting.merge(bowling, on=["match_id", "team"], how="outer").fillna(0)
