select
  date_trunc('hour', event_at) as event_hour,
  event_date,
  extract(hour from event_at)::int as hour_of_day,
  count(*) filter (where behavior_type = 'pv') as pv_events,
  count(distinct user_id) as uv,
  count(distinct user_id) filter (
    where behavior_type = 'fav'
  ) as favorite_users,
  count(distinct user_id) filter (
    where behavior_type = 'cart'
  ) as cart_users,
  count(distinct user_id) filter (
    where behavior_type = 'buy'
  ) as purchase_users,
  count(distinct user_id) filter (
    where behavior_type = 'buy'
  )::numeric / nullif(count(distinct user_id), 0) as purchase_conversion_rate
from {{ ref('stg_user_behavior') }}
group by 1, 2, 3
