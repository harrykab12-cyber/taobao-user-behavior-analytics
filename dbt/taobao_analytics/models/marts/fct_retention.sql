with first_events as (
  select user_id, min(event_date) as cohort_date
  from {{ ref('stg_user_behavior') }}
  group by 1
), activity as (
  select distinct user_id, event_date
  from {{ ref('stg_user_behavior') }}
), cohort_sizes as (
  select cohort_date, count(*) as cohort_users
  from first_events
  group by 1
)
select
  first_events.cohort_date,
  activity.event_date - first_events.cohort_date as day_number,
  count(distinct activity.user_id) as retained_users,
  count(distinct activity.user_id)::numeric / nullif(cohort_sizes.cohort_users, 0) as retention_rate
from first_events
join activity using (user_id)
join cohort_sizes using (cohort_date)
group by 1, 2, cohort_sizes.cohort_users
