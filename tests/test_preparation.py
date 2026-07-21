from pathlib import Path

import pandas as pd

from taobao_analytics.preparation import prepare_cleaned_csv


def test_prepare_cleaned_csv_is_chunked_and_deduplicates_across_chunks(
    tmp_path: Path,
) -> None:
    input_csv = tmp_path / "raw.csv"
    output_csv = tmp_path / "cleaned.csv"
    input_csv.write_text(
        "user_id,item_id,category_id,behavior_type,timestamp\n"
        "1,10,100,pv,1511568000\n"
        "2,20,200,buy,1511654400\n"
        "1,10,100,pv,1511568000\n"
        "3,30,300,cart,not-a-timestamp\n",
        encoding="utf-8",
    )

    report = prepare_cleaned_csv(input_csv, output_csv, chunksize=2)

    cleaned = pd.read_csv(output_csv)
    assert cleaned["user_id"].tolist() == [1, 2]
    assert report == {
        "input_rows": 4,
        "null_key_rows_removed": 0,
        "invalid_timestamp_rows_removed": 1,
        "out_of_analysis_window_rows_removed": 0,
        "duplicate_rows_removed": 1,
        "output_rows": 2,
    }


def test_prepare_cleaned_csv_accepts_tianchi_headerless_export(tmp_path: Path) -> None:
    input_csv = tmp_path / "UserBehavior.csv"
    output_csv = tmp_path / "cleaned.csv"
    input_csv.write_text(
        "1,10,100,pv,1511568000\n"
        "2,20,200,buy,1511654400\n",
        encoding="utf-8",
    )

    report = prepare_cleaned_csv(input_csv, output_csv, chunksize=1)

    cleaned = pd.read_csv(output_csv)
    assert cleaned["user_id"].tolist() == [1, 2]
    assert cleaned["behavior_type"].tolist() == ["pv", "buy"]
    assert report["input_rows"] == 2
