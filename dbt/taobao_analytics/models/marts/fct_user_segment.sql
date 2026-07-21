with user_summary as (
  select
    user_id,
    bool_or(behavior_type = 'buy') as has_purchase,
    bool_or(behavior_type = 'cart') as has_cart,
    bool_or(behavior_type = 'fav') as has_favorite,
    count(distinct event_date) filter (where behavior_type = 'buy') as purchase_days
  from {{ ref('stg_user_behavior') }}
  group by 1
)
select
  user_id,
  case
    when purchase_days >= 2 then '复购型'
    when has_purchase then '购买型'
    when has_cart then '加购未购型'
    when has_favorite then '意向型'
    else '浏览型'
  end as user_segment
from user_summary
