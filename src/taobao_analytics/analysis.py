from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd

from taobao_analytics.cleaning import VALID_BEHAVIORS

ANALYSIS_COLUMNS = [
    "user_id",
    "item_id",
    "category_id",
    "behavior_type",
    "event_at",
    "event_date",
]


def _write_rows(path: Path, rows: list[dict[str, object]], columns: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def _minimum_event_by_user(
    input_csv: Path,
    behaviors: set[str],
    *,
    chunksize: int,
    after: dict[int, str] | None = None,
) -> dict[int, str]:
    """Return each user's first event for a stage, optionally after a prior stage."""
    result: dict[int, str] = {}
    for chunk in pd.read_csv(input_csv, usecols=["user_id", "behavior_type", "event_at"], chunksize=chunksize):
        events = chunk.loc[chunk["behavior_type"].isin(behaviors)].copy()
        if after is not None:
            events["previous_event_at"] = events["user_id"].map(after)
            events = events.loc[
                events["previous_event_at"].notna()
                & (events["event_at"] > events["previous_event_at"])
            ]
        for user_id, event_at in events.groupby("user_id", sort=False)["event_at"].min().items():
            user_key = int(user_id)
            timestamp = str(event_at)
            previous_timestamp = result.get(user_key)
            if previous_timestamp is None or timestamp < previous_timestamp:
                result[user_key] = timestamp
    return result


def _ordered_funnel(input_csv: Path, *, chunksize: int) -> dict[str, int]:
    first_pv = _minimum_event_by_user(input_csv, {"pv"}, chunksize=chunksize)
    first_intent = _minimum_event_by_user(
        input_csv, {"fav", "cart"}, chunksize=chunksize, after=first_pv
    )
    first_purchase = _minimum_event_by_user(
        input_csv, {"buy"}, chunksize=chunksize, after=first_intent
    )
    return {
        "pv_users": len(first_pv),
        "intent_users": len(first_intent),
        "purchase_users": len(first_purchase),
    }


def analyze_cleaned_events(
    input_csv: Path,
    output_directory: Path,
    *,
    chunksize: int = 1_000_000,
) -> dict[str, object]:
    """Create reproducible, privacy-safe aggregate evidence from cleaned event data."""
    if chunksize <= 0:
        raise ValueError("chunksize must be positive")
    output_directory.mkdir(parents=True, exist_ok=True)

    event_rows = 0
    event_counts: Counter[str] = Counter()
    global_users: set[int] = set()
    global_behavior_users = {behavior: set() for behavior in VALID_BEHAVIORS}
    purchase_events_by_category: Counter[int] = Counter()
    user_first_date: dict[int, str] = {}
    purchase_day_count: Counter[int] = Counter()
    purchase_users_by_date: dict[str, set[int]] = {}
    retained_users: Counter[tuple[str, str]] = Counter()
    cohort_sizes: Counter[str] = Counter()
    daily_rows: list[dict[str, object]] = []
    hourly_rows: list[dict[str, object]] = []
    date_mismatch_rows = 0
    invalid_behavior_rows = 0
    first_event_at: str | None = None
    last_event_at: str | None = None

    current_day: str | None = None
    day_users: set[int] = set()
    day_behavior_users = {behavior: set() for behavior in VALID_BEHAVIORS}
    day_event_counts: Counter[str] = Counter()
    current_hour: str | None = None
    hour_users: set[int] = set()
    hour_behavior_users = {behavior: set() for behavior in VALID_BEHAVIORS}
    hour_event_counts: Counter[str] = Counter()

    def finalize_hour() -> None:
        if current_hour is None or current_day is None:
            return
        hour = int(current_hour[-2:])
        uv = len(hour_users)
        purchases = len(hour_behavior_users["buy"])
        hourly_rows.append(
            {
                "event_hour": current_hour + ":00:00",
                "event_date": current_day,
                "hour_of_day": hour,
                "pv_events": hour_event_counts["pv"],
                "uv": uv,
                "favorite_users": len(hour_behavior_users["fav"]),
                "cart_users": len(hour_behavior_users["cart"]),
                "purchase_users": purchases,
                "purchase_conversion_rate": purchases / uv if uv else 0.0,
            }
        )
        day_users.update(hour_users)
        for behavior in VALID_BEHAVIORS:
            day_behavior_users[behavior].update(hour_behavior_users[behavior])
            day_event_counts[behavior] += hour_event_counts[behavior]

    def finalize_day() -> None:
        if current_day is None:
            return
        new_users = 0
        for user_id in day_users:
            cohort_date = user_first_date.get(user_id)
            if cohort_date is None:
                cohort_date = current_day
                user_first_date[user_id] = cohort_date
                cohort_sizes[cohort_date] += 1
                new_users += 1
            retained_users[(cohort_date, current_day)] += 1
        for user_id in day_behavior_users["buy"]:
            purchase_day_count[user_id] += 1
        purchase_users_by_date[current_day] = set(day_behavior_users["buy"])

        uv = len(day_users)
        purchases = len(day_behavior_users["buy"])
        daily_rows.append(
            {
                "event_date": current_day,
                "pv_events": day_event_counts["pv"],
                "uv": uv,
                "favorite_users": len(day_behavior_users["fav"]),
                "cart_users": len(day_behavior_users["cart"]),
                "purchase_users": purchases,
                "new_users": new_users,
                "purchase_conversion_rate": purchases / uv if uv else 0.0,
            }
        )

    for chunk in pd.read_csv(input_csv, usecols=ANALYSIS_COLUMNS, chunksize=chunksize):
        unknown = set(chunk["behavior_type"].dropna()) - VALID_BEHAVIORS
        if unknown:
            invalid_behavior_rows += int(chunk["behavior_type"].isin(unknown).sum())
        if chunk.empty:
            continue
        event_rows += len(chunk)
        event_counts.update(chunk["behavior_type"].value_counts().to_dict())
        global_users.update(map(int, chunk["user_id"].unique()))
        date_mismatch_rows += int(
            (chunk["event_at"].str.slice(0, 10) != chunk["event_date"].astype(str)).sum()
        )
        first_event_at = first_event_at or str(chunk.iloc[0]["event_at"])
        last_event_at = str(chunk.iloc[-1]["event_at"])

        chunk["event_hour"] = chunk["event_at"].str.slice(0, 13)
        for event_hour, hour_frame in chunk.groupby("event_hour", sort=False):
            event_date = str(hour_frame.iloc[0]["event_date"])
            if current_hour is not None and event_hour != current_hour:
                finalize_hour()
                hour_users.clear()
                for behavior in VALID_BEHAVIORS:
                    hour_behavior_users[behavior].clear()
                hour_event_counts.clear()
            if current_day is not None and event_date != current_day:
                finalize_day()
                day_users.clear()
                for behavior in VALID_BEHAVIORS:
                    day_behavior_users[behavior].clear()
                day_event_counts.clear()
            current_hour = str(event_hour)
            current_day = event_date

            hour_users.update(map(int, hour_frame["user_id"].unique()))
            for behavior in VALID_BEHAVIORS:
                behavior_events = hour_frame.loc[hour_frame["behavior_type"] == behavior]
                hour_event_counts[behavior] += len(behavior_events)
                users = set(map(int, behavior_events["user_id"].unique()))
                hour_behavior_users[behavior].update(users)
                global_behavior_users[behavior].update(users)
            purchases = hour_frame.loc[hour_frame["behavior_type"] == "buy", "category_id"]
            purchase_events_by_category.update(map(int, purchases))

    finalize_hour()
    finalize_day()

    for row in daily_rows:
        purchase_users = purchase_users_by_date[row["event_date"]]
        row["repeat_purchase_users"] = sum(
            purchase_day_count[user_id] >= 2 for user_id in purchase_users
        )

    observed_dates = [str(row["event_date"]) for row in daily_rows]
    retention_rows: list[dict[str, object]] = []
    for cohort_date in sorted(cohort_sizes):
        for day_number, activity_date in enumerate(
            date for date in observed_dates if date >= cohort_date
        ):
            retained = retained_users[(cohort_date, activity_date)]
            retention_rows.append(
                {
                    "cohort_date": cohort_date,
                    "activity_date": activity_date,
                    "day_number": day_number,
                    "cohort_users": cohort_sizes[cohort_date],
                    "retained_users": retained,
                    "retention_rate": retained / cohort_sizes[cohort_date],
                }
            )

    repeat_users = {user_id for user_id, days in purchase_day_count.items() if days >= 2}
    purchase_users = global_behavior_users["buy"]
    cart_only_users = global_behavior_users["cart"] - purchase_users
    intent_only_users = global_behavior_users["fav"] - purchase_users - global_behavior_users["cart"]
    browse_only_users = global_users - purchase_users - global_behavior_users["cart"] - global_behavior_users["fav"]
    segment_rows = [
        {"user_segment": "复购型", "user_count": len(repeat_users)},
        {"user_segment": "购买型", "user_count": len(purchase_users - repeat_users)},
        {"user_segment": "加购未购型", "user_count": len(cart_only_users)},
        {"user_segment": "意向型", "user_count": len(intent_only_users)},
        {"user_segment": "浏览型", "user_count": len(browse_only_users)},
    ]
    funnel = _ordered_funnel(input_csv, chunksize=chunksize)
    funnel_rows = [
        {
            "stage_order": 1,
            "stage_code": "pv",
            "stage_name": "浏览",
            "user_count": funnel["pv_users"],
            "conversion_from_previous": 1.0,
            "conversion_from_pv": 1.0,
        },
        {
            "stage_order": 2,
            "stage_code": "intent",
            "stage_name": "意向（收藏或加购）",
            "user_count": funnel["intent_users"],
            "conversion_from_previous": funnel["intent_users"] / funnel["pv_users"] if funnel["pv_users"] else 0.0,
            "conversion_from_pv": funnel["intent_users"] / funnel["pv_users"] if funnel["pv_users"] else 0.0,
        },
        {
            "stage_order": 3,
            "stage_code": "buy",
            "stage_name": "购买",
            "user_count": funnel["purchase_users"],
            "conversion_from_previous": funnel["purchase_users"] / funnel["intent_users"] if funnel["intent_users"] else 0.0,
            "conversion_from_pv": funnel["purchase_users"] / funnel["pv_users"] if funnel["pv_users"] else 0.0,
        },
    ]
    top_categories = [
        {"category_id": category_id, "purchase_events": purchase_events}
        for category_id, purchase_events in purchase_events_by_category.most_common(20)
    ]
    summary: dict[str, object] = {
        "source": str(input_csv),
        "event_rows": event_rows,
        "unique_users": len(global_users),
        "event_counts": dict(sorted(event_counts.items())),
        "time_range": {"min_event_at": first_event_at, "max_event_at": last_event_at},
        "quality_checks": {
            "invalid_behavior_rows": invalid_behavior_rows,
            "event_date_mismatch_rows": date_mismatch_rows,
        },
        "funnel": funnel,
    }

    _write_rows(output_directory / "daily_metrics.csv", daily_rows, list(daily_rows[0]))
    _write_rows(output_directory / "hourly_metrics.csv", hourly_rows, list(hourly_rows[0]))
    _write_rows(
        output_directory / "retention.csv",
        retention_rows,
        ["cohort_date", "activity_date", "day_number", "cohort_users", "retained_users", "retention_rate"],
    )
    _write_rows(output_directory / "funnel.csv", funnel_rows, list(funnel_rows[0]))
    _write_rows(output_directory / "segment_summary.csv", segment_rows, ["user_segment", "user_count"])
    _write_rows(output_directory / "top_purchase_categories.csv", top_categories, ["category_id", "purchase_events"])
    (output_directory / "quality_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return summary
