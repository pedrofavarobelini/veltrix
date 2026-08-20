"""Gate 2 — repository contract, PostgreSQL, retention e restart/reconnect."""

import json
import os
from collections.abc import Iterator
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.modules.caller_identity.service import FLAG_CALLER_REGISTRY
from app.modules.contracts import codes
from app.modules.report_memory.repository import (
    InMemoryReportMemoryRepository,
    LocalJsonReportMemoryRepository,
    PostgreSQLReportMemoryRepository,
    ReportMemoryRepositoryError,
    apply_postgresql_migrations,
)
from app.modules.report_memory.schemas import ReportMemoryEntry
from app.modules.report_memory.service import (
    FLAG_DATABASE_URL,
    FLAG_PERSISTENCE,
    report_memory_service,
)

client = TestClient(app)
MIGRATIONS = Path(__file__).resolve().parents[1] / "migrations"
AUTH_HEADER = "X-PedroCore-Api-Key"
ALPHA_KEY = "alpha-persistence-credential-synthetic"
BETA_KEY = "beta-persistence-credential-synthetic"


def _entry(
    report_id: str,
    *,
    project_id: str = "alpha",
    retention_until: str | None = None,
) -> ReportMemoryEntry:
    now = datetime.now(timezone.utc).isoformat()
    return ReportMemoryEntry(
        memory_id=f"memory-{project_id}-{report_id}",
        report_id=report_id,
        schema_version="2.0",
        producer=f"{project_id}-technical-tool",
        project_id=project_id,
        report_type="qa_evidence",
        status="passed",
        lifecycle="active",
        created_at=now,
        updated_at=now,
        retention_until=retention_until,
        metadata={"minimal": True},
    )


def _registry() -> str:
    return json.dumps(
        [
            {
                "credential_id": "alpha-technical-tool",
                "api_key": ALPHA_KEY,
                "project_id": "alpha",
                "role": "technical_tool",
                "environment": "development",
                "allowed_origins": ["alpha"],
            },
            {
                "credential_id": "beta-technical-tool",
                "api_key": BETA_KEY,
                "project_id": "beta",
                "role": "technical_tool",
                "environment": "development",
                "allowed_origins": ["beta"],
            },
        ]
    )


def _v2(report_id: str) -> dict:
    return {
        "schema_version": "2.0",
        "report_id": report_id,
        "report_type": "qa_evidence",
        "producer": "alpha-technical-tool",
        "project_id": "alpha",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "payload": {"status": "passed", "summary": "persistência sintética"},
    }


@pytest.fixture
def postgres_url() -> Iterator[str]:
    value = (os.environ.get("PEDROCORE_TEST_POSTGRES_URL") or "").strip()
    if not value:
        pytest.skip("PEDROCORE_TEST_POSTGRES_URL não configurada")
    apply_postgresql_migrations(value, MIGRATIONS)
    repository = PostgreSQLReportMemoryRepository(value)
    repository.clear()
    yield value
    repository.clear()


@pytest.fixture(autouse=True)
def clean_service(monkeypatch):
    monkeypatch.delenv(FLAG_CALLER_REGISTRY, raising=False)
    monkeypatch.delenv(FLAG_DATABASE_URL, raising=False)
    monkeypatch.delenv(FLAG_PERSISTENCE, raising=False)
    report_memory_service.reset()
    yield
    report_memory_service.reset()


def test_memory_and_local_json_keep_repository_contract(tmp_path):
    memory = InMemoryReportMemoryRepository()
    assert memory.add(_entry("one")) is True
    assert memory.count("alpha") == 1
    assert memory.get_by_report_id("alpha", "one") is not None

    local = LocalJsonReportMemoryRepository(tmp_path)
    assert local.add(_entry("local-one")) is True
    reconnected = LocalJsonReportMemoryRepository(tmp_path)
    assert reconnected.count("alpha") == 1
    assert reconnected.get_by_report_id("alpha", "local-one") is not None
    assert reconnected.delete_project("alpha") == 1
    assert list(tmp_path.glob("*.json")) == []


def test_local_retention_deletes_only_expired_entry():
    repository = InMemoryReportMemoryRepository()
    now = datetime.now(timezone.utc)
    repository.add(_entry("expired", retention_until=(now - timedelta(days=1)).isoformat()))
    repository.add(_entry("active", retention_until=(now + timedelta(days=1)).isoformat()))

    assert repository.delete_expired(now) == 1
    assert repository.get_by_report_id("alpha", "expired") is None
    assert repository.get_by_report_id("alpha", "active") is not None


def test_postgresql_migration_and_reconnect_are_idempotent(postgres_url):
    assert apply_postgresql_migrations(postgres_url, MIGRATIONS) == []
    first_process = PostgreSQLReportMemoryRepository(postgres_url)
    assert first_process.add(_entry("restart-proof")) is True

    reconnected = PostgreSQLReportMemoryRepository(postgres_url)
    restored = reconnected.get_by_report_id("alpha", "restart-proof")
    assert restored is not None
    assert restored.metadata == {"minimal": True}


def test_postgresql_isolation_duplicate_pagination_and_no_local_cap(postgres_url):
    repository = PostgreSQLReportMemoryRepository(postgres_url)
    for index in range(55):
        assert repository.add(_entry(f"alpha-{index:02d}")) is True
    assert repository.add(_entry("alpha-00")) is False
    assert repository.add(_entry("alpha-00", project_id="beta")) is True

    assert repository.count("alpha") == 55
    assert repository.count("beta") == 1
    page = repository.list("alpha", limit=10, offset=20)
    assert len(page) == 10
    assert all(item.project_id == "alpha" for item in page)


def test_postgresql_retention_and_project_deletion_are_isolated(postgres_url):
    repository = PostgreSQLReportMemoryRepository(postgres_url)
    now = datetime.now(timezone.utc)
    repository.add(_entry("expired", retention_until=(now - timedelta(minutes=1)).isoformat()))
    repository.add(_entry("active", retention_until=(now + timedelta(days=1)).isoformat()))
    repository.add(_entry("beta-active", project_id="beta"))

    assert repository.delete_expired(now) == 1
    assert repository.count("alpha") == 1
    assert repository.delete_project("alpha") == 1
    assert repository.count("alpha") == 0
    assert repository.count("beta") == 1


def test_postgresql_api_ingest_query_delete_and_reconnect(postgres_url, monkeypatch):
    monkeypatch.setenv(FLAG_PERSISTENCE, "postgresql")
    monkeypatch.setenv(FLAG_DATABASE_URL, postgres_url)
    monkeypatch.setenv(FLAG_CALLER_REGISTRY, _registry())

    ingested = client.post(
        "/api/reports/v2/ingest",
        headers={AUTH_HEADER: ALPHA_KEY},
        json=_v2("api-persisted"),
    )
    report_memory_service.reset()
    page = client.get(
        "/api/project-memory/alpha/reports?limit=10&offset=0",
        headers={AUTH_HEADER: ALPHA_KEY},
    )
    deleted = client.delete(
        "/api/project-memory/alpha",
        headers={AUTH_HEADER: ALPHA_KEY},
    )

    assert ingested.status_code == 200
    assert ingested.json()["stored"] is True
    assert page.status_code == 200
    assert page.json()["total"] == 1
    assert page.json()["items"][0]["report_id"] == "api-persisted"
    assert deleted.status_code == 200
    assert deleted.json()["deleted"] == 1


def test_postgresql_query_and_delete_reject_cross_project_idor(postgres_url, monkeypatch):
    monkeypatch.setenv(FLAG_PERSISTENCE, "postgresql")
    monkeypatch.setenv(FLAG_DATABASE_URL, postgres_url)
    monkeypatch.setenv(FLAG_CALLER_REGISTRY, _registry())
    accepted = client.post(
        "/api/reports/v2/ingest",
        headers={AUTH_HEADER: ALPHA_KEY},
        json=_v2("alpha-private"),
    )

    read = client.get(
        "/api/project-memory/alpha/reports",
        headers={AUTH_HEADER: BETA_KEY},
    )
    delete = client.delete(
        "/api/project-memory/alpha",
        headers={AUTH_HEADER: BETA_KEY},
    )

    assert accepted.status_code == 200
    assert read.status_code == 403
    assert delete.status_code == 403
    assert PostgreSQLReportMemoryRepository(postgres_url).count("alpha") == 1


@pytest.mark.parametrize(
    "database_url",
    ["", "postgresql://invalid:invalid@127.0.0.1:1/none?connect_timeout=1"],
)
def test_postgresql_configuration_or_failure_never_falls_back(monkeypatch, database_url):
    monkeypatch.setenv(FLAG_PERSISTENCE, "postgresql")
    monkeypatch.setenv(FLAG_DATABASE_URL, database_url)
    monkeypatch.setenv(FLAG_CALLER_REGISTRY, _registry())

    response = client.post(
        "/api/reports/v2/ingest",
        headers={AUTH_HEADER: ALPHA_KEY},
        json=_v2("must-not-fallback"),
    )

    assert response.status_code == 503
    assert response.json()["error_code"] == codes.REPORT_PERSISTENCE_UNAVAILABLE
    assert report_memory_service._memory_repo.count("alpha") == 0


def test_applied_migration_checksum_drift_is_rejected(postgres_url, tmp_path):
    original = (MIGRATIONS / "0001_operational_reports.sql").read_text(encoding="utf-8")
    drifted = tmp_path / "0001_operational_reports.sql"
    drifted.write_text(original + "\n-- drift\n", encoding="utf-8")

    with pytest.raises(ReportMemoryRepositoryError, match="Checksum divergente"):
        apply_postgresql_migrations(postgres_url, tmp_path)
