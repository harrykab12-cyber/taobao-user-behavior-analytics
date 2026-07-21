with stages as (
  select
    max(user_count) filter (where stage_order = 1) as pv_users,
    max(user_count) filter (where stage_order = 2) as intent_users,
    max(user_count) filter (where stage_order = 3) as purchase_users,
    count(*) as stage_rows
  from {{ ref('fct_user_funnel') }}
)

select *
from stages
where stage_rows <> 3
   or pv_users is null
   or intent_users is null
   or purchase_users is null
   or not (pv_users >= intent_users and intent_users >= purchase_users)
