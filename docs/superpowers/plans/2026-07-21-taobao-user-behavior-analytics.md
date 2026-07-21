# 淘宝用户行为数据分析作品集 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a reproducible, portfolio-ready analysis of the Tianchi Taobao user-behavior dataset using pandas, PostgreSQL, dbt, and Superset.

**Architecture:** Python converts a local, untracked raw CSV into a typed, validated behavior table and a data-quality report. PostgreSQL stores the cleaned table; dbt creates staging, daily-metric, retention, funnel, and user-segment models. Superset reads the dbt marts, while the repository contains only code, synthetic sample data, dashboard metadata, screenshots, and a Chinese analysis report.

**Tech Stack:** Python 3.11, pandas, SQLAlchemy, pytest, PostgreSQL 16, dbt-postgres, Docker Compose, Apache Superset.

## Global Constraints

- Store the downloaded Tianchi CSV only at `data/raw/UserBehavior.csv`; `.gitignore` must exclude all files below `data/raw/`.
- Never commit original or derived row-level Tianchi data; only use the deterministic synthetic sample at `data/sample/user_behavior_sample.csv` in Git.
- Use `behavior_type` values `pv`, `fav`, `cart`, and `buy`; reject every other value during Python validation.
- Treat all source timestamps as Unix seconds in `Asia/Shanghai` and output timezone-naive local timestamps for PostgreSQL.
- Use `event_date` for daily metrics, and define a purchase user as a user with at least one `buy` event in the relevant period.
- Read and write full-data CSVs in bounded chunks; use disk-backed cross-chunk deduplication and bounded database inserts.
- Define the funnel as the ordered path `pv → (fav or cart) → buy`, retaining the first qualifying timestamp for each stage.
- Densify retention only through the source maximum `event_date`, with observable no-activity cells represented as zero.
- Define repeat purchasers as users with purchases on at least two distinct dates in the analysis period.
- Define retention as the proportion of cohort users with at least one event on each relative day; cohorts use the first observed event date.
- Every implementation task must begin with a failing automated test and end with a focused Git commit.

---

## File Structure

```text
.
├── .gitignore
├── .env.example
├── docker-compose.yml
├── pyproject.toml
├── README.md
├── data/
│   ├── README.md
│   └── sample/user_behavior_sample.csv
├── dbt/taobao_analytics/
│   ├── dbt_project.yml
│   ├── packages.yml
│   ├── profiles.yml.example
│   ├── models/
│   │   ├── staging/stg_user_behavior.sql
│   │   ├── intermediate/{int_user_daily_behavior,int_user_funnel_path}.sql
│   │   └── marts/{fct_daily_metrics,fct_hourly_metrics,fct_category_metrics,fct_retention,fct_user_funnel,fct_user_segment,fct_user_segment_activity}.sql
│   └── tests/
├── reports/taobao_user_behavior_analysis.md
├── scripts/{prepare_data.py,load_to_postgres.py,build_superset_bundle.py}
├── src/taobao_analytics/{__init__.py,cleaning.py,preparation.py,loading.py,metrics.py,superset_bundle.py}
├── superset/{README.md,dashboard-spec.md,dashboard_manifest.json,native_export/,assets/.gitkeep}
└── tests/{conftest.py,test_cleaning.py,test_loading.py,test_metrics.py}
```

### Task 1: Establish a runnable, data-safe project skeleton

**Files:**
- Create: `.gitignore`
- Create: `.env.example`
- Create: `pyproject.toml`
- Create: `docker-compose.yml`
- Create: `data/README.md`
- Create: `data/sample/user_behavior_sample.csv`
- Create: `src/taobao_analytics/__init__.py`
- Create: `tests/conftest.py`
- Create: `tests/test_package.py`

**Interfaces:**
- Produces: importable `taobao_analytics` package and a PostgreSQL service reachable at the values in `.env.example`.
- Consumes: no earlier project files.

- [ ] **Step 1: Write the failing package test**

```python
# tests/test_package.py
import taobao_analytics


def test_package_exposes_a_version() -> None:
    assert taobao_analytics.__version__ == "0.1.0"
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python -m pytest tests/test_package.py -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'taobao_analytics'`.

- [ ] **Step 3: Create the minimum runnable project configuration and package**

```toml
# pyproject.toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "taobao-user-behavior-analytics"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
  "pandas>=2.2,<3",
  "psycopg[binary]>=3.2,<4",
  "sqlalchemy>=2.0,<3",
]

[project.optional-dependencies]
dev = ["dbt-postgres==1.9.0", "pytest>=8,<9"]

[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]
```

```python
# src/taobao_analytics/__init__.py
"""Reusable functions for the Taobao user-behavior portfolio project."""

__version__ = "0.1.0"
```

```gitignore
# .gitignore
.venv/
__pycache__/
.pytest_cache/
*.py[cod]
.env
data/raw/
data/processed/
dbt/taobao_analytics/target/
dbt/taobao_analytics/logs/
superset/assets/*.png
!superset/assets/.gitkeep
work/
```

```dotenv
# .env.example
POSTGRES_DB=taobao_analytics
POSTGRES_USER=analytics
POSTGRES_PASSWORD=analytics_local_only
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
```

```yaml
# docker-compose.yml
services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: ${POSTGRES_DB:-taobao_analytics}
      POSTGRES_USER: ${POSTGRES_USER:-analytics}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-analytics_local_only}
    ports:
      - "${POSTGRES_PORT:-5432}:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-analytics} -d ${POSTGRES_DB:-taobao_analytics}"]
      interval: 5s
      timeout: 5s
      retries: 10

volumes:
  postgres_data:
```

Create `data/README.md` with the official Tianchi dataset URL, field schema, local download path, and an explicit statement that raw data must not be committed. Create `data/sample/user_behavior_sample.csv` with header `user_id,item_id,category_id,behavior_type,timestamp` and eight synthetic rows covering all four behavior types. Create an empty `tests/conftest.py` and `superset/assets/.gitkeep`.

- [ ] **Step 4: Install and run the test to verify it passes**

Run: `python -m pip install -e '.[dev]' && python -m pytest tests/test_package.py -v`

Expected: PASS with `1 passed`.

- [ ] **Step 5: Check data safety and commit**

Run: `git check-ignore data/raw/UserBehavior.csv && git add .gitignore .env.example pyproject.toml docker-compose.yml data src tests superset/assets/.gitkeep && git commit -m "chore: scaffold analytics project safely"`

Expected: `data/raw/UserBehavior.csv` is ignored and one focused commit is created.

### Task 2: Implement tested pandas cleaning and data-quality reporting

**Files:**
- Create: `src/taobao_analytics/cleaning.py`
- Create: `scripts/prepare_data.py`
- Create: `tests/test_cleaning.py`

**Interfaces:**
- Produces: `clean_user_behavior(frame: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, int]]`.
- Consumes: columns `user_id`, `item_id`, `category_id`, `behavior_type`, and `timestamp` from a source CSV.
- Contract: returned frame columns are `user_id`, `item_id`, `category_id`, `behavior_type`, `event_at`, and `event_date`; duplicate rows and rows with null key fields are removed.

- [ ] **Step 1: Write the failing cleaning tests**

```python
# tests/test_cleaning.py
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
    raw = pd.DataFrame([[1, 10, 100, "refund", 1511568000]], columns=["user_id", "item_id", "category_id", "behavior_type", "timestamp"])

    with pytest.raises(ValueError, match="Unknown behavior types: refund"):
        clean_user_behavior(raw)


def test_cleaning_reports_rows_removed_for_missing_keys_and_bad_timestamps() -> None:
    raw = pd.DataFrame(
        [[1, 10, 100, "pv", "not-a-timestamp"], [None, 20, 200, "buy", 1511654400]],
        columns=["user_id", "item_id", "category_id", "behavior_type", "timestamp"],
    )

    cleaned, report = clean_user_behavior(raw)

    assert cleaned.empty
    assert report["null_key_rows_removed"] == 1
    assert report["invalid_timestamp_rows_removed"] == 1
```

- [ ] **Step 2: Run the cleaning tests to verify they fail**

Run: `python -m pytest tests/test_cleaning.py -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'taobao_analytics.cleaning'`.

- [ ] **Step 3: Implement the minimum cleaning module and CLI**

```python
# src/taobao_analytics/cleaning.py
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
    result["event_at"] = event_at.loc[result.index].dt.tz_convert("Asia/Shanghai").dt.tz_localize(None)
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
```

```python
# scripts/prepare_data.py
from __future__ import annotations

import argparse
import json
from pathlib import Path

from taobao_analytics.preparation import prepare_cleaned_csv


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input_csv", type=Path)
    parser.add_argument("output_csv", type=Path)
    args = parser.parse_args()
    if not args.input_csv.exists():
        raise FileNotFoundError(f"Raw data not found: {args.input_csv}. See data/README.md.")
    report = prepare_cleaned_csv(args.input_csv, args.output_csv)
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run the cleaning tests to verify they pass**

Run: `python -m pytest tests/test_cleaning.py -v`

Expected: PASS with `2 passed`.

- [ ] **Step 5: Run the sample through the CLI and commit**

Run: `python scripts/prepare_data.py data/sample/user_behavior_sample.csv data/processed/sample_cleaned.csv && git add src scripts tests && git commit -m "feat: add tested behavior data cleaning"`

Expected: a JSON quality report is printed; `data/processed/sample_cleaned.csv` remains ignored.

### Task 3: Implement tested PostgreSQL loading

**Files:**
- Create: `src/taobao_analytics/loading.py`
- Create: `scripts/load_to_postgres.py`
- Create: `tests/test_loading.py`

**Interfaces:**
- Produces: `load_cleaned_events(frame: pd.DataFrame, engine: Engine, table_name: str = "raw_user_behavior") -> int`.
- Consumes: cleaned frame returned by `clean_user_behavior` and a SQLAlchemy PostgreSQL engine.
- Contract: replaces the named raw table and returns the inserted row count.

- [ ] **Step 1: Write the failing loader test**

```python
# tests/test_loading.py
import pandas as pd
from sqlalchemy import create_engine, text

from taobao_analytics.loading import load_cleaned_events


def test_loader_replaces_table_and_returns_inserted_row_count() -> None:
    engine = create_engine("sqlite://")
    frame = pd.DataFrame({"user_id": [1, 2], "behavior_type": ["pv", "buy"]})

    inserted = load_cleaned_events(frame, engine, "raw_user_behavior")

    with engine.connect() as connection:
        count = connection.execute(text("select count(*) from raw_user_behavior")).scalar_one()
    assert inserted == 2
    assert count == 2
```

- [ ] **Step 2: Run the loader test to verify it fails**

Run: `python -m pytest tests/test_loading.py -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'taobao_analytics.loading'`.

- [ ] **Step 3: Implement the minimum loader and CLI**

```python
# src/taobao_analytics/loading.py
from __future__ import annotations

import pandas as pd
from sqlalchemy.engine import Engine


def load_cleaned_events(frame: pd.DataFrame, engine: Engine, table_name: str = "raw_user_behavior") -> int:
    frame.to_sql(
        table_name,
        engine,
        if_exists="replace",
        index=False,
        method=None,
        chunksize=10_000,
    )
    return len(frame)
```

```python
# scripts/load_to_postgres.py
from __future__ import annotations

import argparse
import os
from pathlib import Path

from sqlalchemy import create_engine

from taobao_analytics.loading import load_cleaned_csv


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input_csv", type=Path)
    args = parser.parse_args()
    if not args.input_csv.exists():
        raise FileNotFoundError(f"Cleaned data not found: {args.input_csv}")
    database_url = os.environ.get("DATABASE_URL", "postgresql+psycopg://analytics:analytics_local_only@localhost:5432/taobao_analytics")
    inserted = load_cleaned_csv(
        args.input_csv,
        create_engine(database_url),
        schema=os.environ.get("RAW_SCHEMA", "public"),
    )
    print(f"Loaded {inserted} rows into raw_user_behavior")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run the loader test to verify it passes**

Run: `python -m pytest tests/test_loading.py -v`

Expected: PASS with `1 passed`.

- [ ] **Step 5: Start PostgreSQL, validate the sample load, and commit**

Run: `docker compose up -d postgres && python scripts/load_to_postgres.py data/processed/sample_cleaned.csv && git add src scripts tests && git commit -m "feat: add PostgreSQL event loading"`

Expected: the compose health check passes and the CLI reports the sample row count.

### Task 4: Create dbt source, staging, and daily-metric models

**Files:**
- Create: `dbt/taobao_analytics/dbt_project.yml`
- Create: `dbt/taobao_analytics/packages.yml`
- Create: `dbt/taobao_analytics/profiles.yml.example`
- Create: `dbt/taobao_analytics/models/staging/sources.yml`
- Create: `dbt/taobao_analytics/models/staging/stg_user_behavior.sql`
- Create: `dbt/taobao_analytics/models/marts/fct_daily_metrics.sql`
- Create: `dbt/taobao_analytics/models/marts/schema.yml`

**Interfaces:**
- Produces: dbt relations `stg_user_behavior` and `fct_daily_metrics`.
- Consumes: PostgreSQL relation `raw_user_behavior` written by Task 3.
- Contract: `fct_daily_metrics` has one row per `event_date`, with PV, UV, behavior-user counts, purchase conversion, and repeat-purchaser count.

- [ ] **Step 1: Write the failing dbt model test**

```yaml
# dbt/taobao_analytics/models/marts/schema.yml
version: 2

models:
  - name: fct_daily_metrics
    columns:
      - name: event_date
        tests: [not_null, unique]
      - name: pv
        tests: [not_null]
      - name: purchase_conversion_rate
        tests:
          - dbt_utils.expression_is_true:
              expression: "between 0 and 1"
```

- [ ] **Step 2: Run dbt to verify the model is missing**

Run: `cd dbt/taobao_analytics && dbt deps && dbt test --select fct_daily_metrics`

Expected: FAIL because `fct_daily_metrics` does not exist.

- [ ] **Step 3: Implement the dbt project and SQL models**

```yaml
# dbt/taobao_analytics/dbt_project.yml
name: taobao_analytics
version: 1.0.0
config-version: 2
profile: taobao_analytics
model-paths: ["models"]
models:
  taobao_analytics:
    staging:
      +materialized: view
    marts:
      +materialized: table
```

```yaml
# dbt/taobao_analytics/packages.yml
packages:
  - package: dbt-labs/dbt_utils
    version: 1.3.0
```

```yaml
# dbt/taobao_analytics/profiles.yml.example
taobao_analytics:
  target: dev
  outputs:
    dev:
      type: postgres
      host: "{{ env_var('POSTGRES_HOST', 'localhost') }}"
      user: "{{ env_var('POSTGRES_USER', 'analytics') }}"
      password: "{{ env_var('POSTGRES_PASSWORD', 'analytics_local_only') }}"
      port: "{{ env_var('POSTGRES_PORT', '5432') | int }}"
      dbname: "{{ env_var('POSTGRES_DB', 'taobao_analytics') }}"
      schema: "{{ env_var('DBT_SCHEMA', 'analytics') }}"
      threads: 4
```

```yaml
# dbt/taobao_analytics/models/staging/sources.yml
version: 2
sources:
  - name: raw
    schema: "{{ env_var('RAW_SCHEMA', 'public') }}"
    tables:
      - name: raw_user_behavior
        columns:
          - name: user_id
            tests: [not_null]
          - name: behavior_type
            tests:
              - accepted_values:
                  values: ["pv", "fav", "cart", "buy"]
```

```sql
-- dbt/taobao_analytics/models/staging/stg_user_behavior.sql
select
  user_id::bigint as user_id,
  item_id::bigint as item_id,
  category_id::bigint as category_id,
  behavior_type::text as behavior_type,
  event_at::timestamp as event_at,
  event_date::date as event_date
from {{ source('raw', 'raw_user_behavior') }}
```

```sql
-- dbt/taobao_analytics/models/marts/fct_daily_metrics.sql
with daily as (
  select
    event_date,
    count(*) filter (where behavior_type = 'pv') as pv,
    count(distinct user_id) as uv,
    count(distinct user_id) filter (where behavior_type = 'fav') as favorite_users,
    count(distinct user_id) filter (where behavior_type = 'cart') as cart_users,
    count(distinct user_id) filter (where behavior_type = 'buy') as purchase_users
  from {{ ref('stg_user_behavior') }}
  group by 1
), purchase_days as (
  select distinct user_id, event_date
  from {{ ref('stg_user_behavior') }}
  where behavior_type = 'buy'
), purchase_day_counts as (
  select user_id, count(*) as purchase_day_count
  from purchase_days
  group by 1
), repeat_purchasers as (
  select purchase_days.event_date, count(*) as repeat_purchase_users
  from purchase_days
  join purchase_day_counts using (user_id)
  where purchase_day_count >= 2
  group by 1
)
select
  daily.*,
  coalesce(repeat_purchasers.repeat_purchase_users, 0) as repeat_purchase_users,
  purchase_users::numeric / nullif(uv, 0) as purchase_conversion_rate
from daily
left join repeat_purchasers using (event_date)
```

- [ ] **Step 4: Run dbt model build and tests**

Run: `cp profiles.yml.example ~/.dbt/profiles.yml && cd dbt/taobao_analytics && dbt build --select stg_user_behavior fct_daily_metrics`

Expected: PASS with source tests, staging build, mart build, and daily metric tests all successful.

- [ ] **Step 5: Commit the basic dbt layer**

Run: `git add dbt/taobao_analytics && git commit -m "feat: add dbt staging and daily metrics"`

Expected: one focused dbt commit.

### Task 5: Build and test funnel, retention, and user-segment marts

**Files:**
- Create: `dbt/taobao_analytics/models/intermediate/int_user_daily_behavior.sql`
- Create: `dbt/taobao_analytics/models/intermediate/int_user_funnel_path.sql`
- Create: `dbt/taobao_analytics/models/marts/fct_user_funnel.sql`
- Create: `dbt/taobao_analytics/models/marts/fct_retention.sql`
- Create: `dbt/taobao_analytics/models/marts/fct_user_segment.sql`
- Create: `dbt/taobao_analytics/models/marts/fct_hourly_metrics.sql`
- Create: `dbt/taobao_analytics/models/marts/fct_category_metrics.sql`
- Create: `dbt/taobao_analytics/models/marts/fct_user_segment_activity.sql`
- Modify: `dbt/taobao_analytics/models/marts/schema.yml`
- Create: `dbt/taobao_analytics/tests/funnel_counts_are_monotonic.sql`

**Interfaces:**
- Produces: `int_user_daily_behavior`, `int_user_funnel_path`, `fct_user_funnel`, `fct_retention`, and `fct_user_segment`.
- Consumes: `stg_user_behavior` from Task 4.
- Contract: funnel stages follow timestamp order with `fav` or `cart` as the allowed middle stage; retention includes zero cells through the source maximum date; every analyzed user has exactly one segment.

- [ ] **Step 1: Write the failing singular funnel test**

```sql
-- dbt/taobao_analytics/tests/funnel_counts_are_monotonic.sql
with stages as (
  select
    max(user_count) filter (where stage_order = 1) as pv_users,
    max(user_count) filter (where stage_order = 2) as intent_users,
    max(user_count) filter (where stage_order = 3) as purchase_users
  from {{ ref('fct_user_funnel') }}
)
select * from stages
where not (pv_users >= intent_users and intent_users >= purchase_users)
```

- [ ] **Step 2: Run the test to verify it fails because the model is absent**

Run: `cd dbt/taobao_analytics && dbt test --select funnel_counts_are_monotonic`

Expected: FAIL because `fct_user_funnel` is absent.

- [ ] **Step 3: Implement the analytical marts**

```sql
-- dbt/taobao_analytics/models/intermediate/int_user_daily_behavior.sql
select
  user_id,
  event_date,
  max((behavior_type = 'pv')::int) as has_pv,
  max((behavior_type = 'fav')::int) as has_favorite,
  max((behavior_type = 'cart')::int) as has_cart,
  max((behavior_type = 'buy')::int) as has_purchase
from {{ ref('stg_user_behavior') }}
group by 1, 2
```

```sql
-- dbt/taobao_analytics/models/intermediate/int_user_funnel_path.sql
with users as (
  select distinct user_id from {{ ref('stg_user_behavior') }}
), first_page_views as (
  select user_id, min(event_at) as first_pv_at
  from {{ ref('stg_user_behavior') }}
  where behavior_type = 'pv'
  group by 1
), first_intent_events as (
  select distinct on (first_page_views.user_id)
    first_page_views.user_id,
    events.event_at as first_intent_at,
    events.behavior_type as first_intent_type
  from first_page_views
  join {{ ref('stg_user_behavior') }} events
    on first_page_views.user_id = events.user_id
   and events.behavior_type in ('fav', 'cart')
   and events.event_at > first_page_views.first_pv_at
  order by first_page_views.user_id, events.event_at
), first_purchases as (
  select first_intent_events.user_id, min(events.event_at) as first_purchase_at
  from first_intent_events
  join {{ ref('stg_user_behavior') }} events
    on first_intent_events.user_id = events.user_id
   and events.behavior_type = 'buy'
   and events.event_at > first_intent_events.first_intent_at
  group by 1
)
select users.user_id, first_pv_at, first_intent_at, first_intent_type, first_purchase_at
from users
left join first_page_views using (user_id)
left join first_intent_events using (user_id)
left join first_purchases using (user_id)
```

```sql
-- dbt/taobao_analytics/models/marts/fct_user_funnel.sql
with counts as (
  select
    count(*) filter (where first_pv_at is not null) as pv_users,
    count(*) filter (where first_intent_at is not null) as intent_users,
    count(*) filter (where first_purchase_at is not null) as purchase_users
  from {{ ref('int_user_funnel_path') }}
)
select 1 as stage_order, '浏览' as stage_name, pv_users as user_count from counts
union all
select 2, '意向（收藏或加购）', intent_users from counts
union all
select 3, '购买', purchase_users from counts
```

```sql
-- dbt/taobao_analytics/models/marts/fct_retention.sql
with observation_bounds as (
  select max(event_date) as max_event_date from {{ ref('stg_user_behavior') }}
), first_events as (
  select user_id, min(event_date) as cohort_date
  from {{ ref('stg_user_behavior') }} group by 1
), cohort_sizes as (
  select cohort_date, count(*) as cohort_users from first_events group by 1
), spine as (
  select cohort_date, cohort_users, generated_date::date as activity_date
  from cohort_sizes cross join observation_bounds
  cross join lateral generate_series(cohort_date, max_event_date, interval '1 day') generated_date
), activity as (
  select distinct user_id, event_date from {{ ref('stg_user_behavior') }}
), retained_activity as (
  select first_events.cohort_date, activity.event_date as activity_date,
         count(distinct activity.user_id) as retained_users
  from first_events join activity using (user_id)
  group by 1, 2
)
select cohort_date, activity_date - cohort_date as day_number, cohort_users,
       coalesce(retained_users, 0) as retained_users,
       coalesce(retained_users, 0)::numeric / nullif(cohort_users, 0) as retention_rate
from spine
left join retained_activity using (cohort_date, activity_date)
```

```sql
-- dbt/taobao_analytics/models/marts/fct_user_segment.sql
with user_summary as (
  select
    user_id,
    bool_or(behavior_type = 'buy') as has_purchase,
    bool_or(behavior_type = 'cart') as has_cart,
    bool_or(behavior_type = 'fav') as has_favorite,
    count(distinct event_date) filter (where behavior_type = 'buy') as purchase_days
  from {{ ref('stg_user_behavior') }}
  group by 1
)
select
  user_id,
  case
    when purchase_days >= 2 then '复购型'
    when has_purchase then '购买型'
    when has_cart then '加购未购型'
    when has_favorite then '意向型'
    else '浏览型'
  end as user_segment
from user_summary
```

- [ ] **Step 4: Run the new models and all dbt tests**

Run: `cd dbt/taobao_analytics && dbt build`

Expected: PASS; the singular funnel test returns zero rows.

- [ ] **Step 5: Commit the behavioral analytics layer**

Run: `git add dbt/taobao_analytics && git commit -m "feat: add funnel retention and user segmentation marts"`

Expected: one focused dbt analytics commit.

### Task 6: Add portfolio-ready Superset dashboard assets and business report

**Files:**
- Create: `superset/README.md`
- Create: `superset/dashboard-spec.md`
- Create: `superset/dashboard_manifest.json`
- Create: `superset/native_export/`
- Create: `superset/bootstrap.sh`
- Create: `superset/superset_config.py`
- Create: `scripts/build_superset_bundle.py`
- Create: `reports/taobao_user_behavior_analysis.md`
- Create: `tests/test_metrics.py`
- Create: `src/taobao_analytics/metrics.py`

**Interfaces:**
- Produces: import instructions and dashboard specification for three dashboard pages, a documented business report, and `calculate_conversion_rate(numerator: int, denominator: int) -> float` for checked headline metrics.
- Consumes: dbt mart names and exported Superset database connection configuration from Tasks 4-5.

- [ ] **Step 1: Write the failing metric test**

```python
# tests/test_metrics.py
import pytest

from taobao_analytics.metrics import calculate_conversion_rate


def test_conversion_rate_returns_zero_when_denominator_is_zero() -> None:
    assert calculate_conversion_rate(0, 0) == 0.0


def test_conversion_rate_rejects_negative_inputs() -> None:
    with pytest.raises(ValueError, match="non-negative"):
        calculate_conversion_rate(-1, 10)
```

- [ ] **Step 2: Run the metric test to verify it fails**

Run: `python -m pytest tests/test_metrics.py -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'taobao_analytics.metrics'`.

- [ ] **Step 3: Implement the metric helper and document dashboard/report content**

```python
# src/taobao_analytics/metrics.py
from __future__ import annotations


def calculate_conversion_rate(numerator: int, denominator: int) -> float:
    if numerator < 0 or denominator < 0:
        raise ValueError("numerator and denominator must be non-negative")
    return 0.0 if denominator == 0 else numerator / denominator
```

Write `superset/dashboard-spec.md` with this exact dashboard structure:

```markdown
# 仪表盘规格

## 1. 经营与漏斗概览
- 指标卡：`pv` 行为事件数、UV、购买用户数、购买转化率。
- 图表：日 PV/UV 趋势、`pv → (fav 或 cart) → buy` 有序三阶段用户漏斗。

## 2. 用户增长与留存
- 指标卡：新增用户、日活用户、次日留存率。
- 图表：小时活跃分布、首日分群留存热力图。

## 3. 用户分层与品类运营
- 图表：五类用户分层占比、加购未购用户数、购买用户 Top 类目。
- 筛选器：日期、类目、用户分层。
```

Write `superset/README.md` with the pinned Superset 4.1.2 startup/import path, PostgreSQL connection settings, dbt mart-to-dataset mappings, and the full-data-only screenshot boundary. Store the native import template under `superset/native_export/` and map fields in `superset/dashboard_manifest.json`, including `fct_hourly_metrics`, `fct_category_metrics`, and `fct_user_segment_activity`.

Write `reports/taobao_user_behavior_analysis.md` with sections “业务背景”, “指标口径”, “分析发现”, “运营建议”, and “数据局限”. The report must describe findings as placeholders only after actual full-data runs; it must not invent results from the synthetic sample.

- [ ] **Step 4: Run all Python tests**

Run: `python -m pytest -v`

Expected: PASS with all package, cleaning, loading, and metric tests successful.

- [ ] **Step 5: Commit the reporting and dashboard artifacts**

Run: `git add src tests superset reports && git commit -m "docs: add dashboard specification and analysis report"`

Expected: one focused portfolio-artifacts commit.

### Task 7: Complete the recruiter-facing README and end-to-end verification

**Files:**
- Create: `README.md`
- Modify: `data/README.md`
- Modify: `reports/taobao_user_behavior_analysis.md`

**Interfaces:**
- Produces: a single Chinese-language entry point that lets a reviewer understand the project, reproduce it locally, inspect data boundaries, and find the analysis results.
- Consumes: all committed project files from Tasks 1-6.

- [ ] **Step 1: Write the failing documentation test**

```python
# tests/test_readme.py
from pathlib import Path


def test_readme_links_to_reproducible_steps_and_data_license_notice() -> None:
    text = Path("README.md").read_text(encoding="utf-8")
    assert "docker compose up -d postgres" in text
    assert "dbt build" in text
    assert "原始数据不提交" in text
    assert "天池" in text
```

- [ ] **Step 2: Run the documentation test to verify it fails**

Run: `python -m pytest tests/test_readme.py -v`

Expected: FAIL with `FileNotFoundError: README.md`.

- [ ] **Step 3: Write the recruiter-facing README**

Create `README.md` with this outline and exact command path:

```markdown
# 淘宝用户行为分析：漏斗、留存与用户分层

> 使用真实匿名化的天池淘宝用户行为数据完成的个人数据分析作品集。

## 项目亮点
- pandas 数据清洗与质量报告
- PostgreSQL + dbt 指标模型与测试
- Superset 运营看板
- 漏斗、留存、复购与用户分层分析

## 数据来源与边界
数据来源为阿里云天池“淘宝用户购物行为数据集”。原始数据不提交到仓库，仅限按数据集规则用于学习研究；请从官方页面下载到 `data/raw/UserBehavior.csv`。

## 本地复现
```bash
python -m pip install -e '.[dev]'
cp .env.example .env
docker compose up -d postgres
python scripts/prepare_data.py data/raw/UserBehavior.csv data/processed/user_behavior_cleaned.csv
python scripts/load_to_postgres.py data/processed/user_behavior_cleaned.csv
cp dbt/taobao_analytics/profiles.yml.example ~/.dbt/profiles.yml
cd dbt/taobao_analytics && dbt deps && dbt build
```

## 目录、指标口径、看板与分析报告
Link to `data/README.md`, `superset/dashboard-spec.md`, and `reports/taobao_user_behavior_analysis.md`.
```

Update the report only after the full-data run, keeping every numeric claim linked to a saved dbt query or chart. Do not claim revenue, GMV, price, or order-level conclusions because the source has no such fields.

- [ ] **Step 4: Run the complete automated verification**

Run: `python -m pytest -v && git diff --check && git status --short`

Expected: all tests pass, whitespace check is clean, and only intentional documentation changes remain.

- [ ] **Step 5: Commit final documentation and prepare the GitHub push**

Run: `git add README.md data/README.md reports/taobao_user_behavior_analysis.md tests/test_readme.py && git commit -m "docs: add reproducible portfolio README" && git log --oneline --decorate -8`

Expected: the commit history shows the complete project progression. Create the remote repository `taobao-user-behavior-analytics`, add it as `origin`, push `main`, and verify the README renders correctly on GitHub.

## Plan Self-Review

- Spec coverage: Tasks 1-3 cover the safe, reproducible Python and PostgreSQL path; Tasks 4-5 cover all promised dbt models and validations; Task 6 covers the Superset handoff and business report; Task 7 covers the recruiter-facing README and full verification.
- Placeholder scan: All implementation paths, function signatures, test commands, and commit messages are explicit. The business report intentionally waits for real data outputs, preventing fabricated findings.
- Type consistency: `clean_user_behavior` produces the fields consumed by PostgreSQL loading and dbt sources; dbt marts named in the dashboard assets are created in Tasks 4-5; metric helper and test use the same signature.
