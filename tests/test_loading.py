import pandas as pd
from sqlalchemy import create_engine, text

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
    tmp_path,
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

    inserted = load_cleaned_csv(input_csv, engine, chunksize=2)

    with engine.connect() as connection:
        user_ids = connection.execute(
            text("select user_id from raw_user_behavior order by user_id")
        ).scalars().all()
    assert inserted == 5
    assert user_ids == [1, 2, 3, 4, 5]


def test_load_cleaned_csv_forwards_configured_raw_schema(tmp_path, monkeypatch) -> None:
    input_csv = tmp_path / "cleaned.csv"
    pd.DataFrame({"user_id": [1], "behavior_type": ["pv"]}).to_csv(
        input_csv, index=False
    )
    calls: list[dict[str, object]] = []

    def recording_to_sql(self, *args, **kwargs):
        calls.append(kwargs.copy())

    monkeypatch.setattr(pd.DataFrame, "to_sql", recording_to_sql)

    inserted = load_cleaned_csv(
        input_csv,
        create_engine("sqlite://"),
        schema="configured_raw",
    )

    assert inserted == 1
    assert calls[0]["schema"] == "configured_raw"
