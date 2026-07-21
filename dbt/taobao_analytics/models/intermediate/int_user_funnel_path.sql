with users as (
  select distinct user_id
  from {{ ref('stg_user_behavior') }}
),

first_page_views as (
  select user_id, min(event_at) as first_pv_at
  from {{ ref('stg_user_behavior') }}
  where behavior_type = 'pv'
  group by 1
),

first_intent_events as (
  select distinct on (page_views.user_id)
    page_views.user_id,
    events.event_at as first_intent_at,
    events.behavior_type as first_intent_type
  from first_page_views as page_views
  join {{ ref('stg_user_behavior') }} as events
    on page_views.user_id = events.user_id
   and events.behavior_type in ('fav', 'cart')
   and events.event_at > page_views.first_pv_at
  order by
    page_views.user_id,
    events.event_at,
    case events.behavior_type when 'fav' then 1 else 2 end
),

first_purchases as (
  select
    intent_events.user_id,
    min(events.event_at) as first_purchase_at
  from first_intent_events as intent_events
  join {{ ref('stg_user_behavior') }} as events
    on intent_events.user_id = events.user_id
   and events.behavior_type = 'buy'
   and events.event_at > intent_events.first_intent_at
  group by 1
)

select
  users.user_id,
  page_views.first_pv_at,
  intent_events.first_intent_at,
  intent_events.first_intent_type,
  purchases.first_purchase_at
from users
left join first_page_views as page_views using (user_id)
left join first_intent_events as intent_events using (user_id)
left join first_purchases as purchases using (user_id)
