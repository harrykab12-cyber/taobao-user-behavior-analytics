from __future__ import annotations

import argparse
import os
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine

from taobao_analytics.loading import load_cleaned_events


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input_csv", type=Path)
    args = parser.parse_args()
    if not args.input_csv.exists():
        raise FileNotFoundError(f"Cleaned data not found: {args.input_csv}")

    database_url = os.environ.get(
        "DATABASE_URL",
        "postgresql+psycopg://analytics:analytics_local_only@localhost:5432/taobao_analytics",
    )
    inserted = load_cleaned_events(pd.read_csv(args.input_csv), create_engine(database_url))
    print(f"Loaded {inserted} rows into raw_user_behavior")


if __name__ == "__main__":
    main()
