# 三页仪表盘规格

字段的机器可读映射见 [`dashboard_manifest.json`](dashboard_manifest.json)。

## 1. 经营与漏斗概览

| 图表 | 数据集 | 字段/指标 |
| --- | --- | --- |
| PV 事件数 | `fct_daily_metrics` | `SUM(pv_events)`；仅 `behavior_type='pv'` |
| UV、购买用户数、购买转化率 | `int_user_daily_behavior` | `COUNT(DISTINCT user_id)`、`has_purchase` |
| 日 PV/UV 趋势 | `fct_daily_metrics` | `event_date`, `pv_events`, `uv` |
| 有序用户漏斗 | `fct_user_funnel` | `stage_order`, `stage_name`, `user_count` |

漏斗固定为 `pv → (fav 或 cart) → buy`。中间阶段允许收藏或加购任一事件，只有发生在首次合格 `pv` 之后的事件才计入；`buy` 还必须发生在合格中间阶段之后。

## 2. 用户增长与留存

| 图表 | 数据集 | 字段/指标 |
| --- | --- | --- |
| 新增用户、日活用户 | `fct_daily_metrics` | `event_date`, `new_users`, `uv` |
| 次日留存率 | `fct_retention` | `day_number=1`, `retained_users`, `cohort_users` |
| 小时活跃分布 | `fct_hourly_metrics` | `event_hour`, `hour_of_day`, `uv` |
| 首日分群留存热力图 | `fct_retention` | `cohort_date`, `day_number`, `retention_rate` |

留存矩阵只延伸至源数据的最大 `event_date`，可观察但无活跃的单元格显示为 0。

## 3. 用户分层与品类运营

| 图表 | 数据集 | 字段/指标 |
| --- | --- | --- |
| 五类用户分层占比 | `fct_user_segment_activity` | `user_segment`, `COUNT(DISTINCT user_id)` |
| 加购未购用户数 | `fct_user_segment_activity` | `user_segment='加购未购型'` |
| 购买用户 Top 类目 | `fct_user_segment_activity` | `category_id`, `has_purchase=1`, 去重用户数 |
| 类目行为明细 | `fct_category_metrics` | `event_date`, `category_id`, `pv_events`, `uv`, `purchase_users` |

本页筛选器为 `event_date`、`category_id` 和 `user_segment`。前三张图共享 `fct_user_segment_activity`，因此三个筛选器均可安全联动；类目明细使用独立日期和类目字段。
