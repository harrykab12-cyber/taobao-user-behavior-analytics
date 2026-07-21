from __future__ import annotations

from pathlib import Path

import pandas as pd
from sqlalchemy.engine import Engine

INSERT_CHUNK_SIZE = 10_000


def _write_cleaned_events(
    frame: pd.DataFrame,
    engine: Engine,
    table_name: str,
    *,
    if_exists: str,
    schema: str | None = None,
) -> None:
    frame.to_sql(
        table_name,
        engine,
        if_exists=if_exists,
        index=False,
        method=None,
        chunksize=INSERT_CHUNK_SIZE,
        schema=schema,
    )


def load_cleaned_events(
    frame: pd.DataFrame,
    engine: Engine,
    table_name: str = "raw_user_behavior",
) -> int:
    _write_cleaned_events(frame, engine, table_name, if_exists="replace")
    return len(frame)


def load_cleaned_csv(
    input_csv: Path,
    engine: Engine,
    table_name: str = "raw_user_behavior",
    *,
    chunksize: int = 100_000,
    schema: str | None = None,
) -> int:
    """Replace a table from a CSV without holding the complete file in memory."""
    if chunksize <= 0:
        raise ValueError("chunksize must be positive")

    inserted_rows = 0
    wrote_first_chunk = False
    for chunk in pd.read_csv(input_csv, chunksize=chunksize):
        _write_cleaned_events(
            chunk,
            engine,
            table_name,
            if_exists="append" if wrote_first_chunk else "replace",
            schema=schema,
        )
        wrote_first_chunk = True
        inserted_rows += len(chunk)

    if not wrote_first_chunk:
        _write_cleaned_events(
            pd.read_csv(input_csv, nrows=0),
            engine,
            table_name,
            if_exists="replace",
            schema=schema,
        )
    return inserted_rows
