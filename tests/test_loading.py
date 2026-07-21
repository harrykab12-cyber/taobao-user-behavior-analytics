import pandas as pd
from sqlalchemy import create_engine, text

from taobao_analytics.loading import load_cleaned_events


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
