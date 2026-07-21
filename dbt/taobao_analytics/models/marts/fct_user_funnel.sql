with stages as (
  select
    user_id,
    bool_or(behavior_type = 'pv') as has_pv,
    bool_or(behavior_type = 'fav') as has_favorite,
    bool_or(behavior_type = 'cart') as has_cart,
    bool_or(behavior_type = 'buy') as has_purchase
  from {{ ref('stg_user_behavior') }}
  group by 1
)
select
  count(*) filter (where has_pv) as pv_users,
  count(*) filter (where has_pv and has_favorite) as favorite_users,
  count(*) filter (where has_pv and has_favorite and has_cart) as cart_users,
  count(*) filter (where has_pv and has_favorite and has_cart and has_purchase) as purchase_users
from stages
