from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pandas as pd
from sqlalchemy import inspect, text
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


def _staging_table_name(engine: Engine, table_name: str) -> str:
    suffix = f"__staging_{uuid4().hex[:12]}"
    max_length = engine.dialect.max_identifier_length
    return f"{table_name[: max_length - len(suffix)]}{suffix}"


def _qualified_table_name(
    engine: Engine, table_name: str, schema: str | None
) -> str:
    quote = engine.dialect.identifier_preparer.quote_identifier
    quoted_table = quote(table_name)
    return f"{quote(schema)}.{quoted_table}" if schema else quoted_table


def _drop_table_if_exists(
    engine: Engine, table_name: str, schema: str | None
) -> None:
    qualified_table = _qualified_table_name(engine, table_name, schema)
    with engine.begin() as connection:
        connection.execute(text(f"DROP TABLE IF EXISTS {qualified_table}"))


def _atomic_replace_table(
    engine: Engine,
    staging_table: str,
    table_name: str,
    schema: str | None,
) -> None:
    """Replace target rows from a fully loaded staging table in one transaction."""
    qualified_staging = _qualified_table_name(engine, staging_table, schema)
    qualified_target = _qualified_table_name(engine, table_name, schema)
    quoted_target = engine.dialect.identifier_preparer.quote_identifier(table_name)
    with engine.begin() as connection:
        if inspect(connection).has_table(table_name, schema=schema):
            clear_statement = (
                f"TRUNCATE TABLE {qualified_target}"
                if engine.dialect.name == "postgresql"
                else f"DELETE FROM {qualified_target}"
            )
            connection.execute(text(clear_statement))
            connection.execute(
                text(
                    f"INSERT INTO {qualified_target} "
                    f"SELECT * FROM {qualified_staging}"
                )
            )
            connection.execute(text(f"DROP TABLE {qualified_staging}"))
        else:
            connection.execute(
                text(f"ALTER TABLE {qualified_staging} RENAME TO {quoted_target}")
            )


def load_cleaned_csv(
    input_csv: Path,
    engine: Engine,
    table_name: str = "raw_user_behavior",
    *,
    chunksize: int = 100_000,
    schema: str | None = None,
) -> int:
    """Atomically replace a table from a CSV without loading the file into memory."""
    if chunksize <= 0:
        raise ValueError("chunksize must be positive")

    staging_table = _staging_table_name(engine, table_name)
    inserted_rows = 0
    wrote_first_chunk = False
    try:
        for chunk in pd.read_csv(input_csv, chunksize=chunksize):
            _write_cleaned_events(
                chunk,
                engine,
                staging_table,
                if_exists="append" if wrote_first_chunk else "replace",
                schema=schema,
            )
            wrote_first_chunk = True
            inserted_rows += len(chunk)

        if not wrote_first_chunk:
            _write_cleaned_events(
                pd.read_csv(input_csv, nrows=0),
                engine,
                staging_table,
                if_exists="replace",
                schema=schema,
            )
        _atomic_replace_table(engine, staging_table, table_name, schema)
    except BaseException as load_error:
        try:
            _drop_table_if_exists(engine, staging_table, schema)
        except Exception as cleanup_error:
            load_error.add_note(f"Failed to clean staging table: {cleanup_error}")
        raise
    return inserted_rows
