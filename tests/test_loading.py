import pandas as pd
import pytest
from sqlalchemy import create_engine, inspect, text

import taobao_analytics.loading as loading
from taobao_analytics.loading import load_cleaned_csv, load_cleaned_events


def test_loader_replaces_table_and_returns_inserted_row_count() -> None:
    engine = create_engine("sqlite://")
    pd.DataFrame({"user_id": [999], "behavior_type": ["pv"]}).to_sql(
        "raw_user_behavior", engine, index=False
    )
    frame = pd.DataFrame({"user_id": [1, 2], "behavior_type": ["pv", "buy"]})

    inserted = load_cleaned_events(frame, engine, "raw_user_behavior")

    with engine.connect() as connection:
        count = connection.execute(text("select count(*) from raw_user_behavior")).scalar_one()
    assert inserted == 2
    assert count == 2


def test_loader_uses_bounded_insert_batches(monkeypatch) -> None:
    engine = create_engine("sqlite://")
    frame = pd.DataFrame({"user_id": [1, 2], "behavior_type": ["pv", "buy"]})
    original_to_sql = pd.DataFrame.to_sql
    calls: list[dict[str, object]] = []

    def recording_to_sql(self, *args, **kwargs):
        calls.append(kwargs.copy())
        return original_to_sql(self, *args, **kwargs)

    monkeypatch.setattr(pd.DataFrame, "to_sql", recording_to_sql)

    load_cleaned_events(frame, engine)

    assert calls[0]["method"] is None
    assert calls[0]["chunksize"] == 10_000


def test_load_cleaned_csv_replaces_once_then_appends_bounded_chunks(
    tmp_path, monkeypatch
) -> None:
    engine = create_engine("sqlite://")
    input_csv = tmp_path / "cleaned.csv"
    pd.DataFrame(
        {
            "user_id": [1, 2, 3, 4, 5],
            "behavior_type": ["pv", "pv", "cart", "fav", "buy"],
        }
    ).to_csv(input_csv, index=False)
    pd.DataFrame({"user_id": [999], "behavior_type": ["pv"]}).to_sql(
        "raw_user_behavior", engine, index=False
    )
    original_to_sql = pd.DataFrame.to_sql
    writes: list[tuple[str, str]] = []

    def recording_to_sql(self, name, *args, **kwargs):
        writes.append((name, kwargs["if_exists"]))
        return original_to_sql(self, name, *args, **kwargs)

    monkeypatch.setattr(pd.DataFrame, "to_sql", recording_to_sql)

    inserted = load_cleaned_csv(input_csv, engine, chunksize=2)

    with engine.connect() as connection:
        user_ids = connection.execute(
            text("select user_id from raw_user_behavior order by user_id")
        ).scalars().all()
    assert inserted == 5
    assert user_ids == [1, 2, 3, 4, 5]
    assert all(name != "raw_user_behavior" for name, _ in writes)
    assert [if_exists for _, if_exists in writes] == ["replace", "append", "append"]
    assert inspect(engine).get_table_names() == ["raw_user_behavior"]


def test_load_cleaned_csv_keeps_live_table_when_a_later_chunk_fails(
    tmp_path, monkeypatch
) -> None:
    engine = create_engine("sqlite://")
    input_csv = tmp_path / "cleaned.csv"
    pd.DataFrame(
        {"user_id": [1, 2, 3], "behavior_type": ["pv", "cart", "buy"]}
    ).to_csv(input_csv, index=False)
    pd.DataFrame({"user_id": [999], "behavior_type": ["pv"]}).to_sql(
        "raw_user_behavior", engine, index=False
    )
    original_write = loading._write_cleaned_events
    write_count = 0

    def fail_second_write(*args, **kwargs):
        nonlocal write_count
        write_count += 1
        if write_count == 2:
            raise RuntimeError("simulated second-chunk failure")
        return original_write(*args, **kwargs)

    monkeypatch.setattr(loading, "_write_cleaned_events", fail_second_write)

    with pytest.raises(RuntimeError, match="second-chunk failure"):
        load_cleaned_csv(input_csv, engine, chunksize=2)

    with engine.connect() as connection:
        user_ids = connection.execute(
            text("select user_id from raw_user_behavior")
        ).scalars().all()
    assert user_ids == [999]
    assert inspect(engine).get_table_names() == ["raw_user_behavior"]


def test_load_cleaned_csv_preserves_existing_target_relation_metadata(
    tmp_path,
) -> None:
    engine = create_engine("sqlite://")
    input_csv = tmp_path / "cleaned.csv"
    pd.DataFrame({"user_id": [1], "behavior_type": ["buy"]}).to_csv(
        input_csv, index=False
    )
    pd.DataFrame({"user_id": [999], "behavior_type": ["pv"]}).to_sql(
        "raw_user_behavior", engine, index=False
    )
    with engine.begin() as connection:
        connection.execute(
            text(
                "create index raw_user_behavior_user_id_idx "
                "on raw_user_behavior (user_id)"
            )
        )

    load_cleaned_csv(input_csv, engine)

    indexes = inspect(engine).get_indexes("raw_user_behavior")
    assert [index["name"] for index in indexes] == [
        "raw_user_behavior_user_id_idx"
    ]


def test_load_cleaned_csv_forwards_configured_raw_schema(tmp_path, monkeypatch) -> None:
    input_csv = tmp_path / "cleaned.csv"
    pd.DataFrame({"user_id": [1], "behavior_type": ["pv"]}).to_csv(
        input_csv, index=False
    )
    calls: list[dict[str, object]] = []

    def recording_to_sql(self, *args, **kwargs):
        calls.append(kwargs.copy())

    monkeypatch.setattr(pd.DataFrame, "to_sql", recording_to_sql)
    monkeypatch.setattr(loading, "_atomic_replace_table", lambda *args: None)

    inserted = load_cleaned_csv(
        input_csv,
        create_engine("sqlite://"),
        schema="configured_raw",
    )

    assert inserted == 1
    assert calls[0]["schema"] == "configured_raw"
