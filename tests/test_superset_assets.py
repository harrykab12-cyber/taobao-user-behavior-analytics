import json
import zipfile
from pathlib import Path

from taobao_analytics.superset_bundle import build_superset_bundle


def test_dashboard_manifest_maps_exact_three_pages_to_existing_fields() -> None:
    manifest = json.loads(
        Path("superset/dashboard_manifest.json").read_text(encoding="utf-8")
    )

    assert manifest["superset_version"] == "4.1.2"
    assert [page["name"] for page in manifest["pages"]] == [
        "经营与漏斗概览",
        "用户增长与留存",
        "用户分层与品类运营",
    ]
    assert "fct_hourly_metrics" in manifest["datasets"]
    assert "fct_category_metrics" in manifest["datasets"]
    assert "fct_user_segment_activity" in manifest["datasets"]
    for page in manifest["pages"]:
        for chart in page["charts"]:
            assert chart["dataset"] in manifest["datasets"]
            available_fields = manifest["datasets"][chart["dataset"]]["fields"]
            assert set(chart.get("fields", [])).issubset(available_fields)

    model_layers = {
        "int_user_daily_behavior": "intermediate",
        **{
            dataset: "marts"
            for dataset in manifest["datasets"]
            if dataset != "int_user_daily_behavior"
        },
    }
    for dataset, contract in manifest["datasets"].items():
        sql = Path(
            f"dbt/taobao_analytics/models/{model_layers[dataset]}/{dataset}.sql"
        ).read_text(encoding="utf-8")
        for field in contract["fields"]:
            assert field in sql, f"{dataset}.{field} is absent from its dbt model"


def test_superset_bundle_builder_injects_database_uri_and_creates_zip(
    tmp_path: Path,
) -> None:
    output = tmp_path / "dashboard.zip"

    build_superset_bundle(
        Path("superset/native_export"),
        output,
        "postgresql+psycopg2://user:password@postgres:5432/analytics",
    )

    assert output.stat().st_mode & 0o777 == 0o644
    with zipfile.ZipFile(output) as archive:
        assert "metadata.yaml" in archive.namelist()
        database_yaml = archive.read("databases/Taobao_Analytics.yaml").decode()
        assert "__DATABASE_URI__" not in database_yaml
        assert (
            "postgresql+psycopg2://user:password@postgres:5432/analytics"
            in database_yaml
        )
        dataset_yaml = archive.read(
            "datasets/Taobao_Analytics/fct_daily_metrics.yaml"
        ).decode()
        assert "__DBT_SCHEMA__" not in dataset_yaml
        assert 'schema: "analytics"' in dataset_yaml


def test_compose_pins_superset_and_defines_init_and_healthcheck() -> None:
    compose = Path("docker-compose.yml").read_text(encoding="utf-8")
    dockerfile = Path("superset/Dockerfile").read_text(encoding="utf-8")

    assert "apache/superset:4.1.2" in dockerfile
    assert "superset-init:" in compose
    assert "superset db upgrade" in Path("superset/bootstrap.sh").read_text(
        encoding="utf-8"
    )
    assert "healthcheck:" in compose


def test_superset_services_build_pinned_image_with_postgres_driver_smoke_check() -> None:
    compose = Path("docker-compose.yml").read_text(encoding="utf-8")
    dockerfile = Path("superset/Dockerfile").read_text(encoding="utf-8")

    assert "FROM apache/superset:4.1.2" in dockerfile
    assert "psycopg2-binary==2.9.10" in dockerfile
    assert "import psycopg2" in dockerfile
    assert compose.count("build: *superset-build") == 2
    assert "dockerfile: superset/Dockerfile" in compose


def test_ordered_funnel_sorts_by_its_monotonic_user_count_metric() -> None:
    chart = Path("superset/native_export/charts/Ordered_funnel.yaml").read_text(
        encoding="utf-8"
    )
    params_line = next(
        line for line in chart.splitlines() if line.startswith("params: ")
    )
    params = json.loads(params_line.removeprefix("params: '").removesuffix("'"))

    assert params["metric"] == "sum__user_count"
    assert params["sort_by_metric"] is True
