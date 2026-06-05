from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from ipl_predictor.ml.features import cricsheet_match_features


def load_cricsheet_csvs(data_dir: Path) -> pd.DataFrame:
    files = sorted(data_dir.glob("*.csv"))
    if not files:
        raise FileNotFoundError(f"No Cricsheet CSV files found in {data_dir}")
    return pd.concat((pd.read_csv(file) for file in files), ignore_index=True)


def build_training_table(deliveries: pd.DataFrame) -> pd.DataFrame:
    team_match = cricsheet_match_features(deliveries)
    team_match["run_rate"] = team_match["team_runs"] / (team_match["legal_balls"].clip(lower=1) / 6)

    paired = team_match.merge(team_match, on="match_id", suffixes=("_home", "_away"))
    paired = paired[paired["team_home"] < paired["team_away"]].copy()
    paired["home_win"] = (paired["team_runs_home"] > paired["team_runs_away"]).astype(int)
    paired["run_rate_delta"] = paired["run_rate_home"] - paired["run_rate_away"]
    paired["balls_bowled_delta"] = paired["balls_bowled_home"] - paired["balls_bowled_away"]
    return paired[["run_rate_delta", "balls_bowled_delta", "home_win"]]


def train_baseline(data_dir: Path, model_out: Path) -> dict:
    deliveries = load_cricsheet_csvs(data_dir)
    table = build_training_table(deliveries)
    if table["home_win"].nunique() < 2:
        raise ValueError("Training data needs both win and loss examples")

    x = table[["run_rate_delta", "balls_bowled_delta"]]
    y = table["home_win"]
    x_train, x_test, y_train, y_test = train_test_split(x, y, test_size=0.2, random_state=7)

    model = Pipeline(
        [
            ("scale", StandardScaler()),
            ("classifier", HistGradientBoostingClassifier(random_state=7)),
        ]
    )
    model.fit(x_train, y_train)
    model_out.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, model_out)
    return {"rows": len(table), "accuracy": float(model.score(x_test, y_test)), "model": str(model_out)}
