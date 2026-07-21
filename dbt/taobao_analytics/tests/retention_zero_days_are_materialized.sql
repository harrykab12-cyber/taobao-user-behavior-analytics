with first_events as (
  select user_id, min(event_date) as cohort_date
  from {{ ref('stg_user_behavior') }}
  group by 1
),

cohort_dates as (
  select distinct cohort_date
  from first_events
),

observation_bounds as (
  select max(event_date) as max_event_date
  from {{ ref('stg_user_behavior') }}
),

spine as (
  select
    cohort_dates.cohort_date,
    generated_date::date as activity_date
  from cohort_dates
  cross join observation_bounds
  cross join lateral generate_series(
    cohort_dates.cohort_date,
    observation_bounds.max_event_date,
    interval '1 day'
  ) as generated_date
),

zero_days as (
  select spine.*
  from spine
  where not exists (
    select 1
    from first_events
    join {{ ref('stg_user_behavior') }} as activity using (user_id)
    where first_events.cohort_date = spine.cohort_date
      and activity.event_date = spine.activity_date
  )
)

select zero_days.*
from zero_days
left join {{ ref('fct_retention') }} as actual
  on zero_days.cohort_date = actual.cohort_date
 and zero_days.activity_date - zero_days.cohort_date = actual.day_number
where actual.cohort_date is null
   or actual.retained_users <> 0
   or actual.retention_rate <> 0
