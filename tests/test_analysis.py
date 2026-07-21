from pathlib import Path

import pandas as pd

from taobao_analytics.analysis import analyze_cleaned_events


def test_analyze_cleaned_events_builds_daily_funnel_retention_and_segments(
    tmp_path: Path,
) -> None:
    input_csv = tmp_path / "cleaned.csv"
    output_directory = tmp_path / "evidence"
    pd.DataFrame(
        [
            [1, 10, 100, "pv", "2020-01-01 08:00:00", "2020-01-01"],
            [2, 20, 200, "pv", "2020-01-01 09:00:00", "2020-01-01"],
            [1, 10, 100, "cart", "2020-01-01 10:00:00", "2020-01-01"],
            [1, 10, 100, "buy", "2020-01-01 11:00:00", "2020-01-01"],
            [3, 30, 300, "fav", "2020-01-02 10:00:00", "2020-01-02"],
            [2, 20, 200, "buy", "2020-01-02 11:00:00", "2020-01-02"],
        ],
        columns=[
            "user_id",
            "item_id",
            "category_id",
            "behavior_type",
            "event_at",
            "event_date",
        ],
    ).to_csv(input_csv, index=False)

    summary = analyze_cleaned_events(input_csv, output_directory, chunksize=2)

    assert summary["event_rows"] == 6
    assert summary["unique_users"] == 3
    assert summary["funnel"] == {"pv_users": 2, "intent_users": 1, "purchase_users": 1}

    daily = pd.read_csv(output_directory / "daily_metrics.csv")
    assert daily.loc[0, ["pv_events", "uv", "new_users", "purchase_users"]].tolist() == [2, 2, 2, 1]

    retention = pd.read_csv(output_directory / "retention.csv")
    assert retention.loc[retention["day_number"] == 1, "retained_users"].tolist() == [1]

    segments = pd.read_csv(output_directory / "segment_summary.csv")
    assert dict(zip(segments["user_segment"], segments["user_count"])) == {
        "复购型": 0,
        "购买型": 2,
        "加购未购型": 0,
        "意向型": 1,
        "浏览型": 0,
    }
