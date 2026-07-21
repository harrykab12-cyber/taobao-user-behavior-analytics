# 淘宝用户行为分析：有序漏斗、留存与用户分层

> 使用匿名化天池淘宝用户行为数据构建的个人数据分析作品集。仓库不包含原始全量数据；`reports/evidence/` 仅保存一次真实全量运行的聚合证据，不含用户级记录。

## 项目亮点

- pandas 分块清洗、磁盘去重和质量报告，避免一次性载入全量 CSV
- PostgreSQL 分块加载与 dbt-postgres `1.9.0` 指标模型和测试
- `pv → (fav 或 cart) → buy` 按时间戳排序的三阶段用户漏斗
- 截止源数据最大日期、显式包含零值的分群留存矩阵
- Apache Superset `4.1.2` 三页看板、原生导入包和日期/类目/分层筛选

## 数据与指标边界

数据来源为阿里云天池“淘宝用户购物行为数据集”。原始数据不提交到仓库；请按平台规则下载到 `data/raw/UserBehavior.csv`。`data/sample/` 仅是合成测试数据，不能用于推断真实规模、趋势或业务结论。

本仓库已在本地对下载的官方数据完成一次真实全量运行。清洗规则统一使用 `Asia/Shanghai`，保留 `2017-11-25 00:00:00` 至 `2017-12-03 23:59:59` 的观察窗；质量报告记录了 55,576 条超窗记录与 49 条重复记录的剔除情况。可复核的汇总文件位于 [`reports/evidence/tianchi_full_run_20260721`](reports/evidence/tianchi_full_run_20260721)。

- PV：`behavior_type = 'pv'` 的行为事件数，不是全部行为记录数。
- UV：筛选范围内发生任意行为的去重用户数。
- 有序漏斗：用户必须先有 `pv`，再有 `fav` 或 `cart`（二者任一作为意向阶段），最后才有 `buy`；各阶段取满足前序条件后的首次时间戳。
- 留存：用户首个 `event_date` 为分群日，从分群日铺到源数据最大日期；无活跃的可观察日期记录为 0，不外推未来日期。
- 复购用户：分析期内至少在两个不同 `event_date` 发生 `buy` 的用户。

源字段没有价格、GMV 或订单明细，因此本项目不作收入、GMV、客单价或订单层面的结论。简历、报告和看板应沿用以上口径。

## 从空环境复现

需要 Python 3.11、Docker 和 Docker Compose v2。在项目根目录执行：

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[dev]'
cp .env.example .env
set -a; . ./.env; set +a

docker compose up -d postgres superset
python scripts/prepare_data.py \
  data/raw/UserBehavior.csv \
  data/processed/user_behavior_cleaned.csv
python scripts/load_to_postgres.py \
  data/processed/user_behavior_cleaned.csv

mkdir -p ~/.dbt
cp dbt/taobao_analytics/profiles.yml.example ~/.dbt/profiles.yml
dbt deps --project-dir dbt/taobao_analytics
dbt build --project-dir dbt/taobao_analytics

python scripts/build_superset_bundle.py --schema "$DBT_SCHEMA"
docker compose run --rm superset \
  superset import-dashboards \
  -p /app/superset-assets/dist/taobao_analytics_dashboard.zip \
  -u "$SUPERSET_ADMIN_USERNAME"
```

Superset 地址为 `http://localhost:8088`。首次本地登录账号来自 `.env`；默认值只适合本机演示，共享部署前必须更换密码和 `SUPERSET_SECRET_KEY`。如果修改 PostgreSQL 地址或 dbt schema，请同时通过 `SUPERSET_ANALYTICS_DATABASE_URI` 和 `--schema` 生成新的导入包。

`prepare_data.py` 默认每批读取 500,000 行，并用临时 SQLite 唯一约束完成跨批次去重；`load_to_postgres.py` 默认每批读取 100,000 行，并把数据库插入限制在每批 10,000 行。临时文件和全量清洗结果均不纳入 Git。

## 验证与交付状态

```bash
python -m pytest -v
dbt parse --project-dir dbt/taobao_analytics
dbt build --project-dir dbt/taobao_analytics
git diff --check
```

本仓库提供 Superset `4.1.2` 目标格式的导入资产，但只有在本地 PostgreSQL、dbt 和 Superset 实际运行成功后，才能声明导入成功或保存看板截图。当前仓库不以合成样本截图冒充全量分析成果。

Python 全量聚合证据可在不启动 Docker 的环境中复现：

```bash
python scripts/analyze_data.py \
  data/processed/user_behavior_cleaned.csv \
  reports/evidence/tianchi_full_run_YYYYMMDD
```

该脚本输出日/小时指标、有序漏斗、留存、用户分层、购买事件 Top 类目及质量摘要。它与 dbt/Superset 资产使用同一指标口径，但不等同于已完成 Docker、PostgreSQL、dbt 或 Superset 的本机运行。

## 项目导航

- [数据说明](data/README.md)
- [dbt 模型](dbt/taobao_analytics/models)
- [Superset 安装与导入](superset/README.md)
- [三页看板字段规格](superset/dashboard-spec.md)
- [分析报告](reports/taobao_user_behavior_analysis.md)
