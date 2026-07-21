import pandas as pd
import pytest

from taobao_analytics.cleaning import clean_user_behavior


def test_cleaning_converts_unix_seconds_and_removes_duplicate_rows() -> None:
    raw = pd.DataFrame(
        [
            [1, 10, 100, "pv", 1511568000],
            [1, 10, 100, "pv", 1511568000],
            [2, 20, 200, "buy", 1511654400],
        ],
        columns=["user_id", "item_id", "category_id", "behavior_type", "timestamp"],
    )

    cleaned, report = clean_user_behavior(raw)

    assert cleaned["event_at"].dt.strftime("%Y-%m-%d %H:%M:%S").tolist() == [
        "2017-11-25 08:00:00",
        "2017-11-26 08:00:00",
    ]
    assert cleaned["event_date"].astype(str).tolist() == ["2017-11-25", "2017-11-26"]
    assert report == {
        "input_rows": 3,
        "null_key_rows_removed": 0,
        "invalid_timestamp_rows_removed": 0,
        "duplicate_rows_removed": 1,
        "output_rows": 2,
    }


def test_cleaning_rejects_unknown_behavior_types() -> None:
    raw = pd.DataFrame(
        [[1, 10, 100, "refund", 1511568000]],
        columns=["user_id", "item_id", "category_id", "behavior_type", "timestamp"],
    )

    with pytest.raises(ValueError, match="Unknown behavior types: refund"):
        clean_user_behavior(raw)


def test_cleaning_reports_rows_removed_for_missing_keys_and_bad_timestamps() -> None:
    raw = pd.DataFrame(
        [
            [1, 10, 100, "pv", "not-a-timestamp"],
            [None, 20, 200, "buy", 1511654400],
        ],
        columns=["user_id", "item_id", "category_id", "behavior_type", "timestamp"],
    )

    cleaned, report = clean_user_behavior(raw)

    assert cleaned.empty
    assert report["null_key_rows_removed"] == 1
    assert report["invalid_timestamp_rows_removed"] == 1
