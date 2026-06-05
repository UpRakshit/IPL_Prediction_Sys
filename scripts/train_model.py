import argparse
from pathlib import Path

from ipl_predictor.ml.train import train_baseline


def main() -> None:
    parser = argparse.ArgumentParser(description="Train IPL prediction baseline model.")
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--model-out", type=Path, default=Path("models/baseline.joblib"))
    args = parser.parse_args()

    result = train_baseline(args.data_dir, args.model_out)
    print(result)


if __name__ == "__main__":
    main()
