# Task 2 report: tested pandas cleaning and data-quality reporting

## Scope delivered

- Added `clean_user_behavior(frame)` in `src/taobao_analytics/cleaning.py`.
- Added the `scripts/prepare_data.py` CSV-to-CSV command-line workflow.
- Added tests covering duplicate removal and timezone conversion, unknown behavior rejection, and missing-key/invalid-timestamp reporting.

## RED evidence

Command:

```text
python -m pytest tests/test_cleaning.py -v
```

Result before implementation: exit code 2; test collection failed with the expected error:

```text
ModuleNotFoundError: No module named 'taobao_analytics.cleaning'
```

## GREEN evidence

Focused command:

```text
python -m pytest tests/test_cleaning.py -v
```

Result after implementation: exit code 0; `3 passed in 0.43s`.

Full command:

```text
python -m pytest -v
```

Result: exit code 0; `4 passed in 0.43s`.

CLI command:

```text
python scripts/prepare_data.py data/sample/user_behavior_sample.csv data/processed/sample_cleaned.csv
```

Output:

```json
{"input_rows": 8, "null_key_rows_removed": 0, "invalid_timestamp_rows_removed": 0, "duplicate_rows_removed": 0, "output_rows": 8}
```

`data/processed/sample_cleaned.csv` was generated successfully and remains ignored by Git.

## Self-review

- Required columns and the exact `pv`, `fav`, `cart`, `buy` behavior whitelist are enforced.
- Unix-second timestamps are parsed as UTC, converted to Asia/Shanghai, then stored timezone-naive.
- Returned data uses the contracted six columns and is sorted deterministically.
- Raw data is neither added nor committed.
- `git diff --check` reported no whitespace errors.

## Review-finding fix: non-string unknown behavior types

### Change

- Converted unknown behavior values to strings before sorting and formatting the validation error, so numeric invalid values raise the contracted `ValueError` instead of a `TypeError`.
- Added `test_cleaning_rejects_numeric_unknown_behavior_types_with_value_error` for `behavior_type=9`.

### RED evidence

Command:

```text
python -m pytest tests/test_cleaning.py -v
```

Output before the fix: exit code 1; `3 passed, 1 failed in 0.53s`. The new regression test failed because `clean_user_behavior` raised:

```text
TypeError: sequence item 0: expected str instance, int found
```

### Verification

Command:

```text
python -m pytest tests/test_cleaning.py -v
```

Output: exit code 0; `4 passed in 0.39s`.

Command:

```text
python -m pytest -v
```

Output: exit code 0; `5 passed in 0.39s`.
