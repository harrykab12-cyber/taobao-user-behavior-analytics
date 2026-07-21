from __future__ import annotations

import argparse
import json
from pathlib import Path

from taobao_analytics.preparation import prepare_cleaned_csv


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input_csv", type=Path)
    parser.add_argument("output_csv", type=Path)
    args = parser.parse_args()
    if not args.input_csv.exists():
        raise FileNotFoundError(f"Raw data not found: {args.input_csv}. See data/README.md.")
    report = prepare_cleaned_csv(args.input_csv, args.output_csv)
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
