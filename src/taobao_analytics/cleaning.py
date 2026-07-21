from __future__ import annotations

import pandas as pd

REQUIRED_COLUMNS = ["user_id", "item_id", "category_id", "behavior_type", "timestamp"]
VALID_BEHAVIORS = {"pv", "fav", "cart", "buy"}


def clean_user_behavior(frame: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, int]]:
    missing_columns = sorted(set(REQUIRED_COLUMNS) - set(frame.columns))
    if missing_columns:
        raise ValueError(f"Missing required columns: {', '.join(missing_columns)}")

    unknown = sorted(set(frame["behavior_type"].dropna()) - VALID_BEHAVIORS)
    if unknown:
        raise ValueError(f"Unknown behavior types: {', '.join(unknown)}")

    input_rows = len(frame)
    result = frame[REQUIRED_COLUMNS].copy()
    null_key_rows_removed = int(result[REQUIRED_COLUMNS].isna().any(axis=1).sum())
    result = result.dropna()
    event_at = pd.to_datetime(result["timestamp"], unit="s", utc=True, errors="coerce")
    invalid_timestamp_rows_removed = int(event_at.isna().sum())
    result = result.loc[event_at.notna()].copy()
    event_at = event_at.loc[event_at.notna()]
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
        "duplicate_rows_removed": duplicate_rows_removed,
        "output_rows": len(result),
    }
