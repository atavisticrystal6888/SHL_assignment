"""Render build-time checks for the evaluator-facing deployment."""

from __future__ import annotations

from pathlib import Path
import sys

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient

from app.catalog.repository import CatalogRepository
from app.main import app
from app.settings import settings


def require_path(path: Path, *, kind: str) -> None:
    if kind == "file" and not path.is_file():
        raise SystemExit(f"Missing required file: {path}")
    if kind == "dir" and not path.is_dir():
        raise SystemExit(f"Missing required directory: {path}")


def main() -> int:
    require_path(settings.catalog_path, kind="file")
    require_path(settings.catalog_coverage_path, kind="file")
    require_path(settings.trace_fixtures_dir, kind="dir")

    catalog = CatalogRepository.from_path(settings.catalog_path)
    if not catalog.records:
        raise SystemExit("Catalog is empty")
    if not catalog.eligible_records:
        raise SystemExit("Catalog has no eligible recommendation records")

    client = TestClient(app)
    response = client.get("/health")
    if response.status_code != 200 or response.json() != {"status": "ok"}:
        raise SystemExit(f"Submission health check failed: status={response.status_code}, body={response.text}")

    print(
        "Render preflight passed: "
        f"catalog_records={len(catalog.records)}, "
        f"eligible_records={len(catalog.eligible_records)}, "
        f"trace_dir={settings.trace_fixtures_dir}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())