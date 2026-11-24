"""Train the spam model.

Usage:
    python train.py                       # trains on data/emails.csv
    python train.py --data path/to.csv    # trains on your own dataset
"""
import argparse
import json

from model import DEFAULT_DATA, train


def main():
    parser = argparse.ArgumentParser(description="Train the spam email classifier")
    parser.add_argument("--data", default=str(DEFAULT_DATA), help="CSV with label and text columns")
    parser.add_argument("--test-size", type=float, default=0.2, help="Share of data held out for evaluation")
    args = parser.parse_args()

    metrics = train(args.data, test_size=args.test_size)
    print(json.dumps(metrics, indent=2))
    print("\nModel saved to models/spam_model.joblib")


if __name__ == "__main__":
    main()
