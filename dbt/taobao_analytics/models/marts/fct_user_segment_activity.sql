select
  events.user_id,
  events.event_date,
  events.category_id,
  segments.user_segment,
  max((events.behavior_type = 'pv')::int) as has_pv,
  max((events.behavior_type = 'fav')::int) as has_favorite,
  max((events.behavior_type = 'cart')::int) as has_cart,
  max((events.behavior_type = 'buy')::int) as has_purchase
from {{ ref('stg_user_behavior') }} as events
join {{ ref('fct_user_segment') }} as segments using (user_id)
group by 1, 2, 3, 4
