with expected as (
  select 1 as stage_order, count(*) filter (where first_pv_at is not null) as user_count
  from {{ ref('int_user_funnel_path') }}
  union all
  select 2, count(*) filter (where first_intent_at is not null)
  from {{ ref('int_user_funnel_path') }}
  union all
  select 3, count(*) filter (where first_purchase_at is not null)
  from {{ ref('int_user_funnel_path') }}
),

actual as (
  select stage_order, user_count
  from {{ ref('fct_user_funnel') }}
)

select coalesce(expected.stage_order, actual.stage_order) as stage_order
from expected
full outer join actual using (stage_order)
where expected.stage_order is null
   or actual.stage_order is null
   or actual.user_count is distinct from expected.user_count
