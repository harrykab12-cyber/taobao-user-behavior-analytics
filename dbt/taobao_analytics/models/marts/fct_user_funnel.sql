with counts as (
  select
    count(*) filter (where first_pv_at is not null) as pv_users,
    count(*) filter (where first_intent_at is not null) as intent_users,
    count(*) filter (where first_purchase_at is not null) as purchase_users
  from {{ ref('int_user_funnel_path') }}
),

stages as (
  select 1 as stage_order, 'pv' as stage_code, '浏览' as stage_name, pv_users as user_count
  from counts
  union all
  select 2, 'intent', '意向（收藏或加购）', intent_users
  from counts
  union all
  select 3, 'buy', '购买', purchase_users
  from counts
)

select
  stage_order,
  stage_code,
  stage_name,
  user_count,
  case
    when stage_order = 1 then 1.0
    else coalesce(
      user_count::numeric
        / nullif(lag(user_count) over (order by stage_order), 0),
      0.0
    )
  end as conversion_from_previous,
  case
    when stage_order = 1 then 1.0
    else coalesce(
      user_count::numeric
        / nullif(first_value(user_count) over (order by stage_order), 0),
      0.0
    )
  end as conversion_from_pv
from stages
