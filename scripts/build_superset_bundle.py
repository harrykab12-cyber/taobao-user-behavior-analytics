from __future__ import annotations

import argparse
import os
from pathlib import Path

from taobao_analytics.superset_bundle import build_superset_bundle


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--template-directory",
        type=Path,
        default=Path("superset/native_export"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("superset/dist/taobao_analytics_dashboard.zip"),
    )
    parser.add_argument(
        "--database-uri",
        default=os.environ.get(
            "SUPERSET_ANALYTICS_DATABASE_URI",
            "postgresql+psycopg2://analytics:analytics_local_only@postgres:5432/taobao_analytics",
        ),
    )
    parser.add_argument(
        "--schema",
        default=os.environ.get("DBT_SCHEMA", "analytics"),
    )
    args = parser.parse_args()
    build_superset_bundle(
        args.template_directory,
        args.output,
        args.database_uri,
        args.schema,
    )
    print(f"Built Superset import bundle: {args.output}")


if __name__ == "__main__":
    main()
