# Task 5 Implementation Report

## Status

Implemented the funnel, cohort-retention, and user-segmentation dbt layer requested by Task 5. The implementation deliberately contains no GMV, revenue, price, or monetary claims because the source contract only exposes user-behavior events.

## Scope

Created:

- `dbt/taobao_analytics/models/intermediate/int_user_daily_behavior.sql`
- `dbt/taobao_analytics/models/marts/fct_user_funnel.sql`
- `dbt/taobao_analytics/models/marts/fct_retention.sql`
- `dbt/taobao_analytics/models/marts/fct_user_segment.sql`
- `dbt/taobao_analytics/tests/funnel_counts_are_monotonic.sql`

Updated:

- `dbt/taobao_analytics/models/marts/schema.yml`

No files outside Task 5 scope were intentionally changed or included in the Task 5 commit.

## Behavioral design

### Daily user behavior

`int_user_daily_behavior` produces one row per `user_id` and `event_date`, with integer flags for page view, favorite, cart, and purchase activity.

### Sequential funnel

`fct_user_funnel` first reduces the event stream to one set of lifetime behavior flags per user. Its counts use the exact cumulative predicates from the plan:

1. Page-view users have a page view.
2. Favorite users have both a page view and a favorite.
3. Cart users have a page view, a favorite, and a cart event.
4. Purchase users have all four events: page view, favorite, cart, and purchase.

This set inclusion makes every downstream stage a subset of its predecessor. The singular test selects violations of `pv_users >= favorite_users >= cart_users >= purchase_users`; a valid result therefore returns zero rows.

### Cohort retention

`fct_retention` assigns each user to `min(event_date)`, the user's first observed event date. Activity is deduplicated to one row per user and event date, and `day_number` is calculated as activity date minus cohort date. Cohort size is counted from the one-row-per-user first-event relation and joined by cohort date, so the denominator represents all users in that cohort. Division uses `nullif(cohort_users, 0)` as an additional guard.

Schema tests require a unique `(cohort_date, day_number)` grain, non-null cohort fields, non-negative relative days, and retention rates between zero and one.

### User segments

`fct_user_segment` aggregates once by user, which gives exactly one segment per analyzed user. Segment precedence is:

1. `复购型`: purchases on at least two distinct event dates.
2. `购买型`: at least one purchase.
3. `加购未购型`: cart activity without a qualifying purchase segment.
4. `意向型`: favorite activity without a higher-priority segment.
5. `浏览型`: all remaining analyzed users.

The repeat-purchaser rule counts `count(distinct event_date)` only for `buy` events; multiple purchases on one date do not qualify as repeat purchasing. Schema tests enforce one non-null, unique `user_id` and one accepted non-null segment value.

## TDD evidence

### RED

The singular test was created before the funnel model:

```sql
select *
from {{ ref('fct_user_funnel') }}
where not (pv_users >= favorite_users and favorite_users >= cart_users and cart_users >= purchase_users)
```

The required dbt command was then attempted from `dbt/taobao_analytics`:

```text
$ dbt test --select funnel_counts_are_monotonic
zsh:1: command not found: dbt
exit code: 127
```

Because the runtime could not parse the graph, the intended missing-model RED condition was also checked directly before implementation:

```text
$ test -f models/marts/fct_user_funnel.sql
exit code: 1
```

This proves the singular test referenced a model that was absent at the RED point. It does not constitute a dbt test execution.

### GREEN

After implementing the model, a static reference-presence check found both `stg_user_behavior` and `fct_user_funnel`. Focused semantic searches confirmed all four cumulative funnel predicates and the exact singular-test inequality. The singular test is structured to return zero rows whenever the cumulative predicates are evaluated by dbt/PostgreSQL.

The repository Python tests completed successfully:

```text
$ pytest -q
........                                                                 [100%]
8 passed in 0.51s
```

Additional static validation completed with exit code zero:

- Ruby YAML parsing of `models/marts/schema.yml`
- `git diff --check`
- model-reference file presence
- exact sequential funnel predicate checks
- first-event cohort, relative-day, and guarded-denominator checks
- distinct purchase-date repeat-purchaser check
- singular monotonic-test predicate check

## Runtime limitation

Neither dbt nor a PostgreSQL execution path is available in this environment. Consequently, `dbt build` and the database-backed singular/schema tests were not run, and this report does not claim that a dbt build passed. The final integration step is to run `dbt deps` if needed and `dbt build` against the configured PostgreSQL profile in an environment with dbt installed.

## Concerns

- SQL behavior is validated statically rather than through PostgreSQL execution because the required runtime is unavailable.
- The repository's existing `dbt_utils` dependency is required by the schema tests.

## Review-finding fixes

The Task 5 review findings were addressed with focused dbt tests only. Static comparison against Git confirmed that `int_user_daily_behavior.sql`, `fct_retention.sql`, and `fct_user_segment.sql` remain unchanged because their current SQL already implements the reviewed semantics.

Created:

- `dbt/taobao_analytics/models/intermediate/schema.yml`
- `dbt/taobao_analytics/tests/retention_matches_source_semantics.sql`
- `dbt/taobao_analytics/tests/user_segments_match_source_semantics.sql`

No Task 6 asset or file was modified.

### Daily behavior test coverage

The intermediate schema now asserts:

- unique `(user_id, event_date)` rows with `dbt_utils.unique_combination_of_columns`;
- non-null `user_id` and `event_date` keys;
- non-null values for all four behavior flags;
- numeric accepted values `{0, 1}` for `has_pv`, `has_favorite`, `has_cart`, and `has_purchase`.

The accepted-value tests set `quote: false`, so dbt emits numeric rather than string literals for the integer flag columns.

### Retention semantic comparison

`retention_matches_source_semantics.sql` independently derives from `stg_user_behavior`:

1. each user's cohort date as `min(event_date)`;
2. distinct user-day activity;
3. cohort size from the complete first-event user set;
4. retained users per cohort-relative day;
5. retention rate using retained users divided by the full cohort size.

It full-outer-joins the expected result to `fct_retention` at `(cohort_date, day_number)` grain. Missing rows, extra rows, retained-count differences, and retention-rate differences are all returned as failures. A correct mart therefore produces zero rows.

### User-segment semantic comparison

`user_segments_match_source_semantics.sql` derives the complete distinct user set from `stg_user_behavior`, recomputes the full segment CASE precedence, and defines repeat purchasers as users with purchases on at least two distinct `event_date` values. It full-outer-joins that expected relation to `fct_user_segment`, returning missing users, extra users, or classification differences as failures. A correct mart therefore produces zero rows.

## Review-fix validation evidence

### RED evidence

Before the fix, all three required focused-test files were absent:

```text
dbt/taobao_analytics/models/intermediate/schema.yml: exit 1
dbt/taobao_analytics/tests/retention_matches_source_semantics.sql: exit 1
dbt/taobao_analytics/tests/user_segments_match_source_semantics.sql: exit 1
```

The dbt and PostgreSQL executables were also confirmed absent, so a database-backed RED run was not possible.

### Static validation

A structured Ruby audit parsed the intermediate YAML and checked 31 focused assertions covering:

- exact composite uniqueness columns;
- required non-null and numeric binary-domain tests;
- resolution of every `ref()` to an existing dbt model interface;
- cohort-date, distinct-activity, cohort-size, retained-count, and rate recomputation;
- full retention result-set and measure comparison;
- complete source-user comparison;
- repeat-purchaser use of distinct purchase dates;
- exact segment CASE precedence and mismatch detection.

Result:

```text
static dbt test audit: 31 assertions passed
model SQL unchanged: verified
```

YAML parsing and whitespace validation also completed successfully:

```text
intermediate schema YAML parsed
all focused test files are non-empty
git diff --check: exit 0
```

### Python regression suite

```text
$ pytest -q
........                                                                 [100%]
8 passed in 0.78s
```

### Database-backed test limitation

The focused command was attempted from `dbt/taobao_analytics`:

```text
$ dbt test --select int_user_daily_behavior retention_matches_source_semantics user_segments_match_source_semantics
zsh: command not found: dbt
focused dbt test exit: 127

$ psql --version
zsh: command not found: psql
PostgreSQL client exit: 127
```

Accordingly, this fix does not claim a database-backed dbt test pass. The focused tests must still be executed against the configured PostgreSQL profile in an environment containing dbt, PostgreSQL connectivity, and the existing `dbt_utils` dependency.
