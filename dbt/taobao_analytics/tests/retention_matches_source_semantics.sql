with observation_bounds as (
  select max(event_date) as max_event_date
  from {{ ref('stg_user_behavior') }}
),

first_events as (
  select user_id, min(event_date) as cohort_date
  from {{ ref('stg_user_behavior') }}
  group by 1
),

cohort_sizes as (
  select cohort_date, count(*) as cohort_users
  from first_events
  group by 1
),

spine as (
  select
    cohort_sizes.cohort_date,
    cohort_sizes.cohort_users,
    generated_date::date as activity_date
  from cohort_sizes
  cross join observation_bounds
  cross join lateral generate_series(
    cohort_sizes.cohort_date,
    observation_bounds.max_event_date,
    interval '1 day'
  ) as generated_date
),

activity as (
  select distinct user_id, event_date
  from {{ ref('stg_user_behavior') }}
),

retained as (
  select
    first_events.cohort_date,
    activity.event_date as activity_date,
    count(distinct activity.user_id) as retained_users
  from first_events
  join activity using (user_id)
  group by 1, 2
),

expected as (
  select
    spine.cohort_date,
    spine.activity_date - spine.cohort_date as day_number,
    spine.cohort_users,
    coalesce(retained.retained_users, 0) as retained_users,
    coalesce(retained.retained_users, 0)::numeric
      / nullif(spine.cohort_users, 0) as retention_rate
  from spine
  left join retained using (cohort_date, activity_date)
),

actual as (
  select cohort_date, day_number, cohort_users, retained_users, retention_rate
  from {{ ref('fct_retention') }}
)

select
  coalesce(expected.cohort_date, actual.cohort_date) as cohort_date,
  coalesce(expected.day_number, actual.day_number) as day_number
from expected
full outer join actual
  on expected.cohort_date = actual.cohort_date
 and expected.day_number = actual.day_number
where expected.cohort_date is null
   or actual.cohort_date is null
   or actual.cohort_users is distinct from expected.cohort_users
   or actual.retained_users is distinct from expected.retained_users
   or actual.retention_rate is distinct from expected.retention_rate
