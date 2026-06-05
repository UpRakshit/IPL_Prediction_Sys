from pathlib import Path

import joblib
from sklearn.dummy import DummyClassifier

from ipl_predictor.ml.features import PredictionFeatures


class WinProbabilityModel:
    def __init__(self, model_path: str) -> None:
        self.model_path = Path(model_path)
        self.model = self._load_or_default()

    def predict_home_win_probability(self, features: PredictionFeatures) -> float:
        probabilities = self.model.predict_proba(features.as_frame())[0]
        classes = list(self.model.classes_)
        if 1 not in classes:
            return 0.5
        return float(probabilities[classes.index(1)])

    def _load_or_default(self):
        if self.model_path.exists():
            return joblib.load(self.model_path)

        fallback = DummyClassifier(strategy="prior")
        fallback.fit([[0, 0, 0, 0], [1, 1, 1, 0]], [0, 1])
        return fallback
