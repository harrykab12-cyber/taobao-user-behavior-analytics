from pathlib import Path


def test_readme_links_to_reproducible_steps_and_data_license_notice() -> None:
    text = Path("README.md").read_text(encoding="utf-8")
    assert "docker compose up -d postgres" in text
    assert "dbt build" in text
    assert "原始数据不提交" in text
    assert "天池" in text
    assert "dbt-postgres `1.9.0`" in text
    assert "apache/superset:4.1.2" in Path("docker-compose.yml").read_text(
        encoding="utf-8"
    )
    assert "pv → (fav 或 cart) → buy" in text
