import warnings

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
        "out_of_analysis_window_rows_removed": 0,
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


def test_cleaning_removes_events_outside_tianchi_observation_window() -> None:
    raw = pd.DataFrame(
        [
            [1, 10, 100, "pv", 1511544070],
            [2, 20, 200, "pv", 1505117799],
        ],
        columns=["user_id", "item_id", "category_id", "behavior_type", "timestamp"],
    )

    cleaned, report = clean_user_behavior(raw)

    assert cleaned["user_id"].tolist() == [1]
    assert report["out_of_analysis_window_rows_removed"] == 1


def test_cleaning_rejects_numeric_unknown_behavior_types_with_value_error() -> None:
    raw = pd.DataFrame(
        [[1, 10, 100, 9, 1511568000]],
        columns=["user_id", "item_id", "category_id", "behavior_type", "timestamp"],
    )

    with pytest.raises(ValueError, match="Unknown behavior types: 9"):
        clean_user_behavior(raw)


def test_cleaning_reports_rows_removed_for_missing_keys_and_bad_timestamps() -> None:
    raw = pd.DataFrame(
        [
            [1, 10, 100, "pv", "not-a-timestamp"],
            [None, 20, 200, "buy", 1511654400],
        ],
        columns=["user_id", "item_id", "category_id", "behavior_type", "timestamp"],
    )

    with warnings.catch_warnings(record=True) as observed_warnings:
        warnings.simplefilter("always")
        cleaned, report = clean_user_behavior(raw)

    assert cleaned.empty
    assert report["null_key_rows_removed"] == 1
    assert report["invalid_timestamp_rows_removed"] == 1
    assert not [
        warning for warning in observed_warnings if warning.category is FutureWarning
    ]


def test_cleaning_parses_mixed_numeric_strings_without_future_warning() -> None:
    raw = pd.DataFrame(
        [
            [1, 10, 100, "pv", "1511568000"],
            [2, 20, 200, "buy", "not-a-timestamp"],
        ],
        columns=["user_id", "item_id", "category_id", "behavior_type", "timestamp"],
    )

    with warnings.catch_warnings(record=True) as observed_warnings:
        warnings.simplefilter("always")
        cleaned, report = clean_user_behavior(raw)

    assert len(cleaned) == 1
    assert report["invalid_timestamp_rows_removed"] == 1
    assert not [
        warning for warning in observed_warnings if warning.category is FutureWarning
    ]
