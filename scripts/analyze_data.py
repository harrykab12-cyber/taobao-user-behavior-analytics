from __future__ import annotations

import argparse
import json
from pathlib import Path

from taobao_analytics.analysis import analyze_cleaned_events


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create aggregate evidence from a cleaned Taobao behavior CSV."
    )
    parser.add_argument("input_csv", type=Path)
    parser.add_argument("output_directory", type=Path)
    parser.add_argument("--chunksize", type=int, default=1_000_000)
    args = parser.parse_args()
    if not args.input_csv.exists():
        raise FileNotFoundError(f"Cleaned data not found: {args.input_csv}")
    print(
        json.dumps(
            analyze_cleaned_events(
                args.input_csv, args.output_directory, chunksize=args.chunksize
            ),
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
