select *
from {{ ref('fct_user_funnel') }}
where not (pv_users >= favorite_users and favorite_users >= cart_users and cart_users >= purchase_users)
