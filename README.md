# 淘宝用户行为分析：漏斗、留存与用户分层

> 使用真实匿名化的天池淘宝用户行为数据完成的个人数据分析作品集。

## 项目亮点

- pandas 数据清洗与质量报告
- PostgreSQL + dbt 指标模型与测试
- Superset 运营看板
- 漏斗、留存、复购与用户分层分析

## 数据来源与边界

数据来源为阿里云天池“淘宝用户购物行为数据集”。原始数据不提交到仓库，仅限按数据集规则用于学习研究；请从官方页面下载到 `data/raw/UserBehavior.csv`。

仓库内的 `data/sample/` 仅为合成样本，用于验证清洗、加载和建模管道，不能用于推断真实用户规模、趋势或业务结论。由于当前未提供真实全量数据，也未在此环境执行 dbt/PostgreSQL 全量运行，分析报告不会展示虚构的数值结果。数据字段不含价格、GMV 或订单信息，因此项目不作收入、GMV、价格或订单层面的结论。

## 本地复现

准备 Docker、Python 3.11+、PostgreSQL 客户端和 dbt-postgres 后，在项目根目录运行：

```bash
python -m pip install -e '.[dev]'
cp .env.example .env
docker compose up -d postgres
python scripts/prepare_data.py data/raw/UserBehavior.csv data/processed/user_behavior_cleaned.csv
python scripts/load_to_postgres.py data/processed/user_behavior_cleaned.csv
cp dbt/taobao_analytics/profiles.yml.example ~/.dbt/profiles.yml
cd dbt/taobao_analytics && dbt deps && dbt build
```

随后可在 Superset 中按看板规格连接 dbt 生成的 mart 表；配置和图表清单见下方链接。提交前可运行 `python -m pytest -v` 验证 Python 管道与文档约束。

## 目录、指标口径、看板与分析报告

- [数据说明与访问边界](data/README.md)：数据源、字段和原始数据限制。
- [看板规格](superset/dashboard-spec.md)：Superset 图表、筛选器和指标展示方案。
- [分析报告](reports/taobao_user_behavior_analysis.md)：指标定义、可复核结论要求及待全量运行验证的分析框架。
