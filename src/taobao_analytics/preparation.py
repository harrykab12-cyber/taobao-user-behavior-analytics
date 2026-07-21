from __future__ import annotations

import os
import sqlite3
import tempfile
from pathlib import Path

import pandas as pd

from taobao_analytics.cleaning import REQUIRED_COLUMNS, clean_user_behavior

OUTPUT_COLUMNS = [
    "user_id",
    "item_id",
    "category_id",
    "behavior_type",
    "event_at",
    "event_date",
]


def _csv_read_options(input_csv: Path) -> dict[str, object]:
    """Accept both repository fixtures and Tianchi's headerless CSV export."""
    columns = pd.read_csv(input_csv, nrows=0).columns.tolist()
    if set(REQUIRED_COLUMNS).issubset(columns):
        return {}
    return {"header": None, "names": REQUIRED_COLUMNS}


def prepare_cleaned_csv(
    input_csv: Path,
    output_csv: Path,
    *,
    chunksize: int = 500_000,
) -> dict[str, int]:
    """Clean a CSV with bounded memory and disk-backed global deduplication."""
    if chunksize <= 0:
        raise ValueError("chunksize must be positive")

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    totals = {
        "input_rows": 0,
        "null_key_rows_removed": 0,
        "invalid_timestamp_rows_removed": 0,
        "duplicate_rows_removed": 0,
        "output_rows": 0,
    }

    with tempfile.TemporaryDirectory(
        prefix="taobao-prepare-", dir=output_csv.parent
    ) as temporary_directory:
        database_path = Path(temporary_directory) / "deduplication.sqlite3"
        with sqlite3.connect(database_path) as connection:
            connection.execute(
                """
                create table cleaned_events (
                    user_id integer not null,
                    item_id integer not null,
                    category_id integer not null,
                    behavior_type text not null,
                    event_at text not null,
                    event_date text not null,
                    unique (
                        user_id,
                        item_id,
                        category_id,
                        behavior_type,
                        event_at,
                        event_date
                    )
                )
                """
            )

            for chunk in pd.read_csv(
                input_csv, chunksize=chunksize, **_csv_read_options(input_csv)
            ):
                cleaned, report = clean_user_behavior(chunk)
                for key in (
                    "input_rows",
                    "null_key_rows_removed",
                    "invalid_timestamp_rows_removed",
                    "duplicate_rows_removed",
                ):
                    totals[key] += report[key]

                changes_before = connection.total_changes
                connection.executemany(
                    """
                    insert or ignore into cleaned_events (
                        user_id,
                        item_id,
                        category_id,
                        behavior_type,
                        event_at,
                        event_date
                    ) values (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        (
                            int(row.user_id),
                            int(row.item_id),
                            int(row.category_id),
                            str(row.behavior_type),
                            row.event_at.isoformat(sep=" "),
                            str(row.event_date),
                        )
                        for row in cleaned.itertuples(index=False)
                    ),
                )
                inserted_rows = connection.total_changes - changes_before
                totals["duplicate_rows_removed"] += len(cleaned) - inserted_rows

            totals["output_rows"] = connection.execute(
                "select count(*) from cleaned_events"
            ).fetchone()[0]

            with tempfile.NamedTemporaryFile(
                mode="w",
                suffix=".csv",
                prefix="taobao-cleaned-",
                dir=output_csv.parent,
                delete=False,
            ) as temporary_output:
                temporary_output_path = Path(temporary_output.name)

            try:
                wrote_rows = False
                query = """
                    select
                        user_id,
                        item_id,
                        category_id,
                        behavior_type,
                        event_at,
                        event_date
                    from cleaned_events
                    order by event_at, user_id, item_id
                """
                for output_chunk in pd.read_sql_query(
                    query, connection, chunksize=chunksize
                ):
                    output_chunk.to_csv(
                        temporary_output_path,
                        mode="a" if wrote_rows else "w",
                        header=not wrote_rows,
                        index=False,
                    )
                    wrote_rows = True
                if not wrote_rows:
                    pd.DataFrame(columns=OUTPUT_COLUMNS).to_csv(
                        temporary_output_path, index=False
                    )
                os.replace(temporary_output_path, output_csv)
            finally:
                temporary_output_path.unlink(missing_ok=True)

    return totals
