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
