from __future__ import annotations

import json
import os
import tempfile
import zipfile
from pathlib import Path


def build_superset_bundle(
    template_directory: Path,
    output_zip: Path,
    database_uri: str,
    schema: str = "analytics",
) -> None:
    """Build a deterministic Superset native-import archive from tracked YAML."""
    if not database_uri:
        raise ValueError("database_uri must not be empty")
    if not schema:
        raise ValueError("schema must not be empty")
    if not (template_directory / "metadata.yaml").is_file():
        raise FileNotFoundError(
            f"Superset export metadata not found: {template_directory / 'metadata.yaml'}"
        )

    output_zip.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        suffix=".zip", prefix="superset-import-", dir=output_zip.parent, delete=False
    ) as temporary_file:
        temporary_path = Path(temporary_file.name)

    try:
        with zipfile.ZipFile(
            temporary_path, mode="w", compression=zipfile.ZIP_DEFLATED
        ) as archive:
            source_paths = sorted(
                path for path in template_directory.rglob("*") if path.is_file()
            )
            for source_path in source_paths:
                relative_path = source_path.relative_to(template_directory)
                content = source_path.read_text(encoding="utf-8")
                content = content.replace(
                    '"__DATABASE_URI__"', json.dumps(database_uri, ensure_ascii=False)
                )
                content = content.replace(
                    '"__DBT_SCHEMA__"', json.dumps(schema, ensure_ascii=False)
                )
                if "__DATABASE_URI__" in content or "__DBT_SCHEMA__" in content:
                    raise ValueError(
                        f"Unresolved template placeholder in {relative_path}"
                    )

                archive_entry = zipfile.ZipInfo(
                    relative_path.as_posix(), date_time=(1980, 1, 1, 0, 0, 0)
                )
                archive_entry.external_attr = 0o644 << 16
                archive.writestr(archive_entry, content.encode("utf-8"))
        os.replace(temporary_path, output_zip)
        output_zip.chmod(0o644)
    finally:
        temporary_path.unlink(missing_ok=True)
