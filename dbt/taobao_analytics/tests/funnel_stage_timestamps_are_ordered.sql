select *
from {{ ref('int_user_funnel_path') }}
where (first_intent_at is not null and first_pv_at is null)
   or (first_intent_at is not null and first_intent_at <= first_pv_at)
   or (first_purchase_at is not null and first_intent_at is null)
   or (first_purchase_at is not null and first_purchase_at <= first_intent_at)
