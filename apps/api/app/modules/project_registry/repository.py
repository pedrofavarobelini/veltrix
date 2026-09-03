"""Persistência do Project Registry.

Por que precisa sobreviver ao restart
--------------------------------------

Um projeto criado pelo usuário É a identidade sob a qual as análises dele
serão guardadas. Se o catálogo morre com o processo, o `project_id` das
análises de ontem passa a apontar para um projeto que o sistema não conhece
mais — e isolamento por projeto vira isolamento por projeto que talvez exista.

Segue o padrão já canônico no Veltrix
--------------------------------------

`Protocol` + InMemory + LocalJson + PostgreSQL, com a fábrica lendo um modo
declarado e falhando fechado: modo inválido não vira `off`, e `postgresql` sem
URL não cai para memória em silêncio.

Isolamento
----------

`project_id` é PRIMARY KEY. A separação entre projetos é do SCHEMA, não de um
filtro aplicado depois da leitura — um `WHERE` esquecido não pode vazar linha
de outro projeto se a chave já não permite duas linhas com o mesmo id.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Protocol, runtime_checkable

import psycopg

from app.core.env_compat import AmbiguityPolicy, resolve
from app.modules.project_registry.schemas import ProjectRecord, ProjectStatus

FLAG_PROJECT_REGISTRY = "VELTRIX_PROJECT_REGISTRY"
FLAG_PROJECT_REGISTRY_DIR = "VELTRIX_PROJECT_REGISTRY_DIR"
FLAG_PROJECT_REGISTRY_DATABASE_URL = "VELTRIX_PROJECT_REGISTRY_DATABASE_URL"

VALID_MODES = ("memory", "local_json", "postgresql")

TABLE = "pedrocore_projects"


class ProjectRepositoryError(RuntimeError):
    """Falha de persistência. Nunca degradada em silêncio."""


class ProjectRepositoryConfigurationError(ProjectRepositoryError):
    """Configuração declarada que não pode ser honrada."""


@runtime_checkable
class ProjectRepository(Protocol):
    def upsert(self, record: ProjectRecord) -> None: ...

    def get(self, project_id: str) -> ProjectRecord | None: ...

    def list_all(self) -> list[ProjectRecord]: ...

    def clear(self) -> None: ...


class InMemoryProjectRepository:
    """Store em processo. Usado em teste e no modo `memory` explícito."""

    def __init__(self) -> None:
        self._records: dict[str, ProjectRecord] = {}

    def upsert(self, record: ProjectRecord) -> None:
        self._records[record.project_id] = record.model_copy(deep=True)

    def get(self, project_id: str) -> ProjectRecord | None:
        found = self._records.get(project_id)
        return found.model_copy(deep=True) if found else None

    def list_all(self) -> list[ProjectRecord]:
        return [
            item.model_copy(deep=True)
            for item in sorted(self._records.values(), key=lambda r: r.display_name.lower())
        ]

    def clear(self) -> None:
        self._records.clear()


class LocalJsonProjectRepository(InMemoryProjectRepository):
    """Catálogo em arquivo JSON, carregado na construção.

    O carregamento no `__init__` é o que torna o restart verificável: uma
    instância nova enxerga o que a anterior registrou.
    """

    def __init__(self, directory: str | Path) -> None:
        super().__init__()
        self._directory = Path(directory)
        self._directory.mkdir(parents=True, exist_ok=True)
        self._file = self._directory / "project_registry.json"
        self._load()

    def _load(self) -> None:
        if not self._file.exists():
            return
        try:
            bruto = json.loads(self._file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise ProjectRepositoryError(
                f"Catálogo de projetos ilegível em {self._file}. "
                "Nenhum catálogo vazio foi assumido no lugar."
            ) from error
        for item in bruto.get("projects", []):
            registro = ProjectRecord.model_validate(item)
            self._records[registro.project_id] = registro

    def _flush(self) -> None:
        payload = {
            "registry_version": "project-registry-v1",
            "projects": [item.model_dump(mode="json") for item in self._records.values()],
        }
        self._file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def upsert(self, record: ProjectRecord) -> None:
        super().upsert(record)
        self._flush()

    def clear(self) -> None:
        super().clear()
        self._flush()


class PostgreSQLProjectRepository:
    """Store PostgreSQL. Idempotente por chave, isolado pelo próprio id."""

    def __init__(self, database_url: str) -> None:
        self._database_url = database_url

    def _connect(self) -> psycopg.Connection:
        try:
            return psycopg.connect(self._database_url, connect_timeout=5)
        except psycopg.Error as error:
            raise ProjectRepositoryError(
                "Catálogo de projetos indisponível; nenhum fallback aplicado."
            ) from error

    def upsert(self, record: ProjectRecord) -> None:
        # `project_id` nunca aparece no SET: identidade não se atualiza. Um
        # UPDATE que pudesse trocar a chave transformaria "editar metadata" em
        # "assumir o lugar de outro projeto".
        with self._connect() as connection:
            connection.execute(
                f"""
                INSERT INTO {TABLE} (
                    project_id, display_name, local_path, repository_url,
                    status, created_at, updated_at, capability_manifest_reference
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (project_id) DO UPDATE SET
                    display_name = EXCLUDED.display_name,
                    local_path = EXCLUDED.local_path,
                    repository_url = EXCLUDED.repository_url,
                    status = EXCLUDED.status,
                    updated_at = EXCLUDED.updated_at,
                    capability_manifest_reference =
                        EXCLUDED.capability_manifest_reference
                """,
                (
                    record.project_id,
                    record.display_name,
                    record.local_path,
                    record.repository_url,
                    record.status.value,
                    record.created_at,
                    record.updated_at,
                    record.capability_manifest_reference,
                ),
            )

    def get(self, project_id: str) -> ProjectRecord | None:
        with self._connect() as connection:
            linha = connection.execute(
                f"""
                SELECT project_id, display_name, local_path, repository_url,
                       status, created_at, updated_at, capability_manifest_reference
                  FROM {TABLE} WHERE project_id = %s
                """,
                (project_id,),
            ).fetchone()
        return _para_registro(linha) if linha else None

    def list_all(self) -> list[ProjectRecord]:
        with self._connect() as connection:
            linhas = connection.execute(
                f"""
                SELECT project_id, display_name, local_path, repository_url,
                       status, created_at, updated_at, capability_manifest_reference
                  FROM {TABLE} ORDER BY LOWER(display_name)
                """
            ).fetchall()
        return [_para_registro(item) for item in linhas]

    def clear(self) -> None:
        with self._connect() as connection:
            connection.execute(f"DELETE FROM {TABLE}")


def _para_registro(linha) -> ProjectRecord:
    return ProjectRecord(
        project_id=linha[0],
        display_name=linha[1],
        local_path=linha[2],
        repository_url=linha[3],
        status=ProjectStatus(linha[4]),
        created_at=linha[5],
        updated_at=linha[6],
        capability_manifest_reference=linha[7],
    )


# --- fabrica ---------------------------------------------------------------


def project_registry_mode() -> str:
    """Modo declarado. Valor invalido falha; ele nao vira `memory` em silencio.

    O padrao e `memory`, e nao `off`: um catalogo ausente deixaria o console
    sem nenhum projeto para escolher, o que nao e um estado util. `memory` da
    um catalogo funcional e honesto sobre nao sobreviver ao restart.
    """
    modo = (resolve(FLAG_PROJECT_REGISTRY, default="memory") or "memory").lower()
    if modo not in VALID_MODES:
        raise ProjectRepositoryConfigurationError(
            f"{FLAG_PROJECT_REGISTRY} inválido: {modo!r}. Use um de: {', '.join(VALID_MODES)}."
        )
    return modo


def build_project_repository() -> ProjectRepository:
    modo = project_registry_mode()
    if modo == "memory":
        return InMemoryProjectRepository()
    if modo == "local_json":
        diretorio = resolve(FLAG_PROJECT_REGISTRY_DIR, default="") or ""
        if not diretorio.strip():
            raise ProjectRepositoryConfigurationError(
                f"{FLAG_PROJECT_REGISTRY}=local_json exige {FLAG_PROJECT_REGISTRY_DIR}."
            )
        return LocalJsonProjectRepository(diretorio.strip())

    url = (
        resolve(FLAG_PROJECT_REGISTRY_DATABASE_URL, policy=AmbiguityPolicy.FAIL)
        or (os.environ.get("VELTRIX_TEST_POSTGRES_URL") or "").strip()
        or (os.environ.get("PEDROCORE_TEST_POSTGRES_URL") or "").strip()
    )
    if not url:
        raise ProjectRepositoryConfigurationError(
            f"{FLAG_PROJECT_REGISTRY}=postgresql exige "
            f"{FLAG_PROJECT_REGISTRY_DATABASE_URL}. Sem URL não há catálogo "
            "durável, e cair para memória em silêncio perderia projetos sem avisar."
        )
    return PostgreSQLProjectRepository(url)


def project_registry_is_durable() -> bool:
    return project_registry_mode() in ("local_json", "postgresql")
