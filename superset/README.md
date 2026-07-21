# Superset 仪表盘资产

## PostgreSQL 连接

在 Superset 中新建 PostgreSQL 数据库连接，并使用项目部署时导出的连接配置。连接信息应由环境变量或安全密钥管理系统提供：

- Host：`POSTGRES_HOST`
- Port：`POSTGRES_PORT`（通常为 `5432`）
- Database：`POSTGRES_DB`
- Username：`POSTGRES_USER`
- Password：`POSTGRES_PASSWORD`
- Schema：`POSTGRES_SCHEMA`（默认 `analytics`）

SQLAlchemy 连接串格式：`postgresql+psycopg2://POSTGRES_USER:POSTGRES_PASSWORD@POSTGRES_HOST:POSTGRES_PORT/POSTGRES_DB`。

## dbt mart 到 Superset 数据集

| Superset 数据集 | dbt mart | 用途 |
| --- | --- | --- |
| `fct_daily_metrics` | `fct_daily_metrics` | 经营日指标和 PV/UV 趋势 |
| `fct_retention` | `fct_retention` | 新增、活跃与分群留存 |
| `fct_user_funnel` | `fct_user_funnel` | 四阶段用户漏斗 |
| `fct_user_segment` | `fct_user_segment` | 用户分层、加购未购及品类运营 |

在已连接的 PostgreSQL 数据库中，将以上 mart 表逐一注册为同名数据集；数据库、schema 和表名须与 dbt 导出结果一致。

## 导入 YAML 规格

1. 在 Superset 的 Import/Export 页面选择导入资产。
2. 上传 `taobao_analytics_dashboard.yaml`，再将其中数据集绑定到已注册的 PostgreSQL 数据集。
3. 按 `dashboard-spec.md` 创建或核对三个页面的图表、指标卡和筛选器。
4. 校验日期、类目和用户分层筛选器能够作用于对应图表后发布仪表盘。

此 YAML 是可审阅的资产清单；不同 Superset 版本的完整导出格式可能不同，若导入器提示版本不兼容，请用本实例导出的 YAML 作为外壳并保留同名数据集、图表和页面配置。

## 截图归档

验收截图须由人工在连接真实、已审批数据的 Superset 实例中捕获，并保存至 `superset/assets/`。不要保存原始行数据、查询结果导出或任何可识别用户的信息。
