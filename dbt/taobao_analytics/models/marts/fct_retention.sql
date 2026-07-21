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

cohort_date_spine as (
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
)

select
  cohort_date_spine.cohort_date,
  cohort_date_spine.activity_date - cohort_date_spine.cohort_date as day_number,
  cohort_date_spine.cohort_users,
  coalesce(retained.retained_users, 0) as retained_users,
  coalesce(retained.retained_users, 0)::numeric
    / nullif(cohort_date_spine.cohort_users, 0) as retention_rate
from cohort_date_spine
left join retained using (cohort_date, activity_date)
