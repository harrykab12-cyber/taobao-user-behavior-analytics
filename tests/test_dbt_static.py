from pathlib import Path

import yaml


DBT_ROOT = Path("dbt/taobao_analytics")


def _model(name: str, layer: str = "marts") -> str:
    return (DBT_ROOT / "models" / layer / f"{name}.sql").read_text(encoding="utf-8")


def test_retention_uses_observation_bounded_dense_date_spine() -> None:
    sql = _model("fct_retention").lower()

    assert "max(event_date) as max_event_date" in sql
    assert "generate_series" in sql
    assert "coalesce(retained.retained_users, 0)" in sql
    assert "cohort_users" in sql


def test_funnel_uses_ordered_path_with_fav_or_cart_middle_stage() -> None:
    path_sql = _model("int_user_funnel_path", "intermediate").lower()
    funnel_sql = _model("fct_user_funnel").lower()

    assert "first_pv_at" in path_sql
    assert "first_intent_at" in path_sql
    assert "behavior_type in ('fav', 'cart')" in path_sql
    assert "events.event_at > page_views.first_pv_at" in path_sql
    assert "events.event_at > intent_events.first_intent_at" in path_sql
    assert "first_purchase_at" in path_sql
    assert "stage_order" in funnel_sql
    assert "user_count" in funnel_sql


def test_dashboard_marts_expose_hour_category_and_filterable_segment_grains() -> None:
    hourly_sql = _model("fct_hourly_metrics").lower()
    category_sql = _model("fct_category_metrics").lower()
    segment_activity_sql = _model("fct_user_segment_activity").lower()

    assert "event_hour" in hourly_sql
    assert "hour_of_day" in hourly_sql
    assert "category_id" in category_sql
    assert "pv_events" in category_sql
    assert all(
        field in segment_activity_sql
        for field in ("event_date", "category_id", "user_segment", "has_purchase")
    )


def test_raw_source_schema_is_configurable_and_all_columns_are_tested() -> None:
    source_path = DBT_ROOT / "models/staging/sources.yml"
    sources = source_path.read_text(encoding="utf-8")

    assert "env_var('RAW_SCHEMA', 'public')" in sources
    source_config = yaml.safe_load(sources)
    columns = {
        column["name"]: column
        for column in source_config["sources"][0]["tables"][0]["columns"]
    }
    for column in (
        "user_id",
        "item_id",
        "category_id",
        "behavior_type",
        "event_at",
        "event_date",
    ):
        assert f"- name: {column}" in sources
        assert "not_null" in columns[column]["tests"]
