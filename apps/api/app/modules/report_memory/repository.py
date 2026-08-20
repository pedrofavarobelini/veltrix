from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import LiteralString, Protocol, cast, runtime_checkable

import psycopg
from psycopg import Connection, sql
from psycopg.types.json import Jsonb

from app.modules.report_memory.schemas import ReportMemoryEntry

# Repositórios de memória técnica (PEDROCORE-REPORT-MEMORY-01).
#
# Padrão seguro: in-memory (in-process, volátil). Persistência local_json é
# opcional, default OFF, grava somente no diretório configurado pelo operador
# (testes usam tmp_path), nunca em .env e nunca dados com segredos (a
# sanitização acontece no serviço, antes de chegar aqui).

MAX_ENTRIES_PER_PROJECT = 50


class ReportMemoryRepositoryError(RuntimeError):
    """Falha explícita de persistência; nunca autoriza fallback silencioso."""


class ReportMemoryRepositoryConfigurationError(ReportMemoryRepositoryError):
    pass


@runtime_checkable
class ReportMemoryRepository(Protocol):
    def add(self, entry: ReportMemoryEntry) -> bool: ...

    def list(
        self, project_id: str, limit: int | None = None, offset: int = 0
    ) -> list[ReportMemoryEntry]: ...

    def count(self, project_id: str) -> int: ...

    def get_by_report_id(self, project_id: str, report_id: str) -> ReportMemoryEntry | None: ...

    def delete_project(self, project_id: str) -> int: ...

    def delete_expired(self, now: datetime | None = None) -> int: ...

    def clear(self) -> None: ...


def _expired(entry: ReportMemoryEntry, now: datetime) -> bool:
    if entry.retention_until is None:
        return False
    try:
        expires_at = datetime.fromisoformat(entry.retention_until)
    except ValueError:
        return False
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    return expires_at <= now


class InMemoryReportMemoryRepository:
    def __init__(self) -> None:
        self._entries: dict[str, list[ReportMemoryEntry]] = {}

    def add(self, entry: ReportMemoryEntry) -> bool:
        entries = self._entries.setdefault(entry.project_id, [])
        entries.append(entry)
        if len(entries) > MAX_ENTRIES_PER_PROJECT:
            del entries[: len(entries) - MAX_ENTRIES_PER_PROJECT]
        return True

    def list(
        self, project_id: str, limit: int | None = None, offset: int = 0
    ) -> list[ReportMemoryEntry]:
        entries = list(self._entries.get(project_id, []))
        if offset:
            entries = entries[offset:]
        if limit is not None:
            return entries[:limit]
        return entries

    def count(self, project_id: str) -> int:
        return len(self._entries.get(project_id, []))

    def get_by_report_id(self, project_id: str, report_id: str) -> ReportMemoryEntry | None:
        return next(
            (entry for entry in self._entries.get(project_id, []) if entry.report_id == report_id),
            None,
        )

    def clear(self) -> None:
        self._entries.clear()

    def delete_project(self, project_id: str) -> int:
        return len(self._entries.pop(project_id, []))

    def delete_expired(self, now: datetime | None = None) -> int:
        reference = now or datetime.now(timezone.utc)
        deleted = 0
        for project_id, entries in list(self._entries.items()):
            retained = [entry for entry in entries if not _expired(entry, reference)]
            deleted += len(entries) - len(retained)
            if retained:
                self._entries[project_id] = retained
            else:
                self._entries.pop(project_id, None)
        return deleted


class LocalJsonReportMemoryRepository(InMemoryReportMemoryRepository):
    """Persistência local opcional: um arquivo JSON por projeto.

    Grava apenas dentro do diretório configurado (criado se necessário).
    Dados gerados em runtime não devem ser commitados.
    """

    def __init__(self, directory: str | Path) -> None:
        super().__init__()
        self._directory = Path(directory)
        self._directory.mkdir(parents=True, exist_ok=True)
        self._load_all()

    def _file_for(self, project_id: str) -> Path:
        safe_name = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in project_id)
        return self._directory / f"{safe_name}.json"

    def _load_all(self) -> None:
        for file in self._directory.glob("*.json"):
            try:
                raw = json.loads(file.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            for item in raw if isinstance(raw, list) else []:
                try:
                    entry = ReportMemoryEntry(**item)
                except Exception:
                    continue
                super().add(entry)

    def _persist_project(self, project_id: str) -> None:
        entries = self.list(project_id)
        target = self._file_for(project_id)
        if not entries:
            target.unlink(missing_ok=True)
            return
        payload = [item.model_dump(mode="json") for item in entries]
        target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def add(self, entry: ReportMemoryEntry) -> bool:
        added = super().add(entry)
        self._persist_project(entry.project_id)
        return added

    def delete_project(self, project_id: str) -> int:
        deleted = super().delete_project(project_id)
        self._persist_project(project_id)
        return deleted

    def delete_expired(self, now: datetime | None = None) -> int:
        projects = list(self._entries)
        deleted = super().delete_expired(now)
        for project_id in projects:
            self._persist_project(project_id)
        return deleted


class PostgreSQLReportMemoryRepository:
    """Persistência operacional PostgreSQL; nunca cria schema implicitamente."""

    def __init__(self, database_url: str) -> None:
        if not database_url.strip():
            raise ReportMemoryRepositoryConfigurationError(
                "PEDROCORE_REPORT_MEMORY_DATABASE_URL é obrigatória no modo postgresql."
            )
        self._database_url = database_url

    def _connect(self) -> Connection:
        try:
            return psycopg.connect(self._database_url, connect_timeout=5)
        except psycopg.Error as exc:
            raise ReportMemoryRepositoryError("PostgreSQL indisponível.") from exc

    def add(self, entry: ReportMemoryEntry) -> bool:
        if entry.report_id is None:
            raise ReportMemoryRepositoryError(
                "PostgreSQL exige report_id para idempotência operacional."
            )
        statement = """
            INSERT INTO pedrocore_operational_reports (
                memory_id, report_id, project_id, schema_version, producer,
                report_type, run_id, conversation_id, lifecycle, created_at,
                updated_at, retention_until, payload
            ) VALUES (
                %(memory_id)s, %(report_id)s, %(project_id)s, %(schema_version)s,
                %(producer)s, %(report_type)s, %(run_id)s, %(conversation_id)s,
                %(lifecycle)s, %(created_at)s, %(updated_at)s,
                %(retention_until)s, %(payload)s
            )
            ON CONFLICT (project_id, report_id) DO NOTHING
        """
        params = {
            "memory_id": entry.memory_id,
            "report_id": entry.report_id,
            "project_id": entry.project_id,
            "schema_version": entry.schema_version,
            "producer": entry.producer,
            "report_type": entry.report_type,
            "run_id": entry.source_run_id,
            "conversation_id": entry.conversation_id,
            "lifecycle": entry.lifecycle,
            "created_at": entry.created_at,
            "updated_at": entry.updated_at,
            "retention_until": entry.retention_until,
            "payload": Jsonb(entry.model_dump(mode="json")),
        }
        try:
            with self._connect() as connection, connection.cursor() as cursor:
                cursor.execute(statement, params)
                return cursor.rowcount == 1
        except psycopg.Error as exc:
            raise ReportMemoryRepositoryError("Falha ao persistir relatório.") from exc

    def list(
        self, project_id: str, limit: int | None = None, offset: int = 0
    ) -> list[ReportMemoryEntry]:
        statement = """
            SELECT payload FROM pedrocore_operational_reports
            WHERE project_id = %s ORDER BY created_at ASC, memory_id ASC
        """
        params: list[object] = [project_id]
        if limit is not None:
            statement += " LIMIT %s"
            params.append(limit)
        if offset:
            statement += " OFFSET %s"
            params.append(offset)
        try:
            with self._connect() as connection, connection.cursor() as cursor:
                cursor.execute(statement, params)
                return [ReportMemoryEntry.model_validate(row[0]) for row in cursor]
        except psycopg.Error as exc:
            raise ReportMemoryRepositoryError("Falha ao consultar relatórios.") from exc

    def count(self, project_id: str) -> int:
        try:
            with self._connect() as connection, connection.cursor() as cursor:
                cursor.execute(
                    "SELECT COUNT(*) FROM pedrocore_operational_reports WHERE project_id = %s",
                    (project_id,),
                )
                row = cursor.fetchone()
                return int(row[0]) if row is not None else 0
        except psycopg.Error as exc:
            raise ReportMemoryRepositoryError("Falha ao contar relatórios.") from exc

    def get_by_report_id(self, project_id: str, report_id: str) -> ReportMemoryEntry | None:
        try:
            with self._connect() as connection, connection.cursor() as cursor:
                cursor.execute(
                    """SELECT payload FROM pedrocore_operational_reports
                    WHERE project_id = %s AND report_id = %s""",
                    (project_id, report_id),
                )
                row = cursor.fetchone()
                return ReportMemoryEntry.model_validate(row[0]) if row is not None else None
        except psycopg.Error as exc:
            raise ReportMemoryRepositoryError("Falha ao consultar report_id.") from exc

    def delete_project(self, project_id: str) -> int:
        try:
            with self._connect() as connection, connection.cursor() as cursor:
                cursor.execute(
                    "DELETE FROM pedrocore_operational_reports WHERE project_id = %s",
                    (project_id,),
                )
                return cursor.rowcount
        except psycopg.Error as exc:
            raise ReportMemoryRepositoryError("Falha ao excluir dados do projeto.") from exc

    def delete_expired(self, now: datetime | None = None) -> int:
        reference = now or datetime.now(timezone.utc)
        try:
            with self._connect() as connection, connection.cursor() as cursor:
                cursor.execute(
                    """DELETE FROM pedrocore_operational_reports
                    WHERE retention_until IS NOT NULL AND retention_until <= %s""",
                    (reference,),
                )
                return cursor.rowcount
        except psycopg.Error as exc:
            raise ReportMemoryRepositoryError("Falha ao aplicar retenção.") from exc

    def clear(self) -> None:
        try:
            with self._connect() as connection, connection.cursor() as cursor:
                cursor.execute("DELETE FROM pedrocore_operational_reports")
        except psycopg.Error as exc:
            raise ReportMemoryRepositoryError("Falha ao limpar repositório de teste.") from exc


def apply_postgresql_migrations(database_url: str, directory: str | Path) -> list[str]:
    """Aplica migrações SQL aditivas com checksum; repetição é idempotente."""
    migration_dir = Path(directory)
    files = sorted(migration_dir.glob("*.sql"))
    if not files:
        raise ReportMemoryRepositoryConfigurationError(
            "Nenhuma migração SQL encontrada; schema não foi alterado."
        )
    applied: list[str] = []
    try:
        with (
            psycopg.connect(database_url, connect_timeout=5) as connection,
            connection.cursor() as cursor,
        ):
            cursor.execute(
                """CREATE TABLE IF NOT EXISTS pedrocore_schema_migrations (
                    version TEXT PRIMARY KEY,
                    checksum TEXT NOT NULL,
                    applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )"""
            )
            for file in files:
                content = file.read_text(encoding="utf-8")
                checksum = hashlib.sha256(content.encode("utf-8")).hexdigest()
                cursor.execute(
                    "SELECT checksum FROM pedrocore_schema_migrations WHERE version = %s",
                    (file.name,),
                )
                row = cursor.fetchone()
                if row is not None:
                    if row[0] != checksum:
                        raise ReportMemoryRepositoryError(
                            f"Checksum divergente para migração aplicada: {file.name}"
                        )
                    continue
                cursor.execute(sql.SQL(cast(LiteralString, content)))
                cursor.execute(
                    """INSERT INTO pedrocore_schema_migrations (version, checksum)
                    VALUES (%s, %s)""",
                    (file.name, checksum),
                )
                applied.append(file.name)
        return applied
    except (OSError, psycopg.Error) as exc:
        raise ReportMemoryRepositoryError("Falha ao aplicar migrações PostgreSQL.") from exc
