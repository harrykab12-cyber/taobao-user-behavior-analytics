select
  user_id,
  event_date,
  max((behavior_type = 'pv')::int) as has_pv,
  max((behavior_type = 'fav')::int) as has_favorite,
  max((behavior_type = 'cart')::int) as has_cart,
  max((behavior_type = 'buy')::int) as has_purchase
from {{ ref('stg_user_behavior') }}
group by 1, 2
