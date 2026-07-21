from __future__ import annotations

import pandas as pd

REQUIRED_COLUMNS = ["user_id", "item_id", "category_id", "behavior_type", "timestamp"]
VALID_BEHAVIORS = {"pv", "fav", "cart", "buy"}
ANALYSIS_START_AT = pd.Timestamp("2017-11-25 00:00:00", tz="Asia/Shanghai")
ANALYSIS_END_AT = pd.Timestamp("2017-12-03 23:59:59", tz="Asia/Shanghai")


def clean_user_behavior(frame: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, int]]:
    missing_columns = sorted(set(REQUIRED_COLUMNS) - set(frame.columns))
    if missing_columns:
        raise ValueError(f"Missing required columns: {', '.join(missing_columns)}")

    unknown = sorted(
        str(value)
        for value in set(frame["behavior_type"].dropna()) - VALID_BEHAVIORS
    )
    if unknown:
        raise ValueError(f"Unknown behavior types: {', '.join(unknown)}")

    input_rows = len(frame)
    result = frame[REQUIRED_COLUMNS].copy()
    null_key_rows_removed = int(result[REQUIRED_COLUMNS].isna().any(axis=1).sum())
    result = result.dropna()
    numeric_timestamp = pd.to_numeric(result["timestamp"], errors="coerce")
    event_at = pd.to_datetime(numeric_timestamp, unit="s", utc=True, errors="coerce")
    invalid_timestamp_rows_removed = int(event_at.isna().sum())
    result = result.loc[event_at.notna()].copy()
    event_at = event_at.loc[event_at.notna()]
    in_analysis_window = (event_at >= ANALYSIS_START_AT) & (event_at <= ANALYSIS_END_AT)
    out_of_analysis_window_rows_removed = int((~in_analysis_window).sum())
    result = result.loc[in_analysis_window].copy()
    event_at = event_at.loc[in_analysis_window]
    before_deduplicate = len(result)
    result = result.drop_duplicates()
    duplicate_rows_removed = before_deduplicate - len(result)
    result["event_at"] = (
        event_at.loc[result.index].dt.tz_convert("Asia/Shanghai").dt.tz_localize(None)
    )
    result = result.drop(columns="timestamp")
    result["event_date"] = result["event_at"].dt.date
    result = result.sort_values(["event_at", "user_id", "item_id"]).reset_index(drop=True)
    return result, {
        "input_rows": input_rows,
        "null_key_rows_removed": null_key_rows_removed,
        "invalid_timestamp_rows_removed": invalid_timestamp_rows_removed,
        "out_of_analysis_window_rows_removed": out_of_analysis_window_rows_removed,
        "duplicate_rows_removed": duplicate_rows_removed,
        "output_rows": len(result),
    }
