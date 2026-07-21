# Superset 4.1.2 看板资产

项目通过 `docker-compose.yml` 固定使用 `apache/superset:4.1.2`。`superset-init` 服务执行元数据库升级、幂等创建本地管理员并运行 `superset init`；`superset` 服务在端口 `8088` 提供界面和健康检查。

## 数据集和三页结构

[`dashboard_manifest.json`](dashboard_manifest.json) 是可机器校验的页面—图表—数据集—字段契约，[`dashboard-spec.md`](dashboard-spec.md) 是便于审阅的中文版本。核心新增数据集为：

| 数据集 | 粒度 | 用途 |
| --- | --- | --- |
| `fct_daily_metrics` | 日期 | `pv` 事件、新增、日趋势 |
| `int_user_daily_behavior` | 用户×日期 | 跨日筛选时准确去重 UV、购买用户和转化率 |
| `fct_user_funnel` | 有序阶段 | `pv → (fav 或 cart) → buy` 漏斗 |
| `fct_retention` | 分群日×相对日 | 稠密留存矩阵和次日留存 |
| `fct_hourly_metrics` | 小时 | 小时活跃分布 |
| `fct_category_metrics` | 日期×类目 | 类目日指标 |
| `fct_user_segment_activity` | 用户×日期×类目 | 日期、类目和用户分层联动筛选 |

## 启动和导入

先按根目录 README 完成 `.env`、PostgreSQL 加载和 `dbt build`。随后运行：

```bash
docker compose up -d postgres superset
python scripts/build_superset_bundle.py --schema "$DBT_SCHEMA"
docker compose run --rm superset \
  superset import-dashboards \
  -p /app/superset-assets/dist/taobao_analytics_dashboard.zip \
  -u "$SUPERSET_ADMIN_USERNAME"
```

`native_export/` 保存 Superset 原生导出目录；构建器把实际数据库 URI 和 dbt schema 注入模板，再生成被 Git 忽略的 `dist/taobao_analytics_dashboard.zip`。默认 URI 指向 Compose 网络内的 `postgres` 服务。自定义连接时，设置 `SUPERSET_ANALYTICS_DATABASE_URI` 或传入 `--database-uri`。

上述命令是版本固定的复现路径，不代表本仓库已在缺少 Docker、PostgreSQL 或原始数据的环境中完成导入。导入后应在 Superset 中逐项确认 15 个图表、三个标签页、数据集连接和第三页的日期/类目/用户分层筛选范围。

## 截图边界

只有在真实全量数据完成加载、`dbt build` 通过且图表口径核对完成后，才可人工截图并保存到 `superset/assets/`。截图不得包含明细行或可识别用户信息；仓库当前不声称存在已验证的全量截图。
