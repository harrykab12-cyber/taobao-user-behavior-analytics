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
