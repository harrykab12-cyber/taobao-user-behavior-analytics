with first_events as (
  select
    user_id,
    min(event_date) as cohort_date
  from {{ ref('stg_user_behavior') }}
  group by 1
),

activity as (
  select distinct
    user_id,
    event_date
  from {{ ref('stg_user_behavior') }}
),

cohort_sizes as (
  select
    cohort_date,
    count(*) as cohort_users
  from first_events
  group by 1
),

expected as (
  select
    first_events.cohort_date,
    activity.event_date - first_events.cohort_date as day_number,
    count(distinct activity.user_id) as retained_users,
    count(distinct activity.user_id)::numeric
      / nullif(cohort_sizes.cohort_users, 0) as retention_rate
  from first_events
  join activity using (user_id)
  join cohort_sizes using (cohort_date)
  group by 1, 2, cohort_sizes.cohort_users
),

actual as (
  select
    cohort_date,
    day_number,
    retained_users,
    retention_rate
  from {{ ref('fct_retention') }}
)

select
  coalesce(expected.cohort_date, actual.cohort_date) as cohort_date,
  coalesce(expected.day_number, actual.day_number) as day_number,
  expected.retained_users as expected_retained_users,
  actual.retained_users as actual_retained_users,
  expected.retention_rate as expected_retention_rate,
  actual.retention_rate as actual_retention_rate
from expected
full outer join actual
  on expected.cohort_date = actual.cohort_date
 and expected.day_number = actual.day_number
where expected.cohort_date is null
   or actual.cohort_date is null
   or actual.retained_users is distinct from expected.retained_users
   or actual.retention_rate is distinct from expected.retention_rate
