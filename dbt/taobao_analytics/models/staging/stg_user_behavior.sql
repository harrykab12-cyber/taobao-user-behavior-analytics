select
  user_id::bigint as user_id,
  item_id::bigint as item_id,
  category_id::bigint as category_id,
  behavior_type::text as behavior_type,
  event_at::timestamp as event_at,
  event_date::date as event_date
from {{ source('raw', 'raw_user_behavior') }}
