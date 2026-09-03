"""Project Registry contra PostgreSQL de verdade.

Por que este arquivo existe separado
-------------------------------------

Um store em memória sempre prova que o código do store funciona. Ele nunca
prova que a MIGRATION existe, que a chave é única no banco, que o `CHECK` do
schema recusa um id com separador de caminho, ou que o `ON CONFLICT` de fato
atualiza em vez de duplicar.

Essas são exatamente as garantias que sustentam isolamento de projeto — e
nenhuma delas vive no Python.

Sem `PEDROCORE_TEST_POSTGRES_URL` (ou `VELTRIX_TEST_POSTGRES_URL`) o arquivo
inteiro fica `skip`. Um PASS sem banco aqui seria um PASS sobre nada.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

import psycopg
import pytest

from app.modules.project_registry.repository import (
    TABLE,
    PostgreSQLProjectRepository,
)
from app.modules.project_registry.schemas import ProjectRecord, ProjectStatus
from app.modules.project_registry.seeds import SEED_PROJECTS
from app.modules.project_registry.service import ProjectRegistryService
from app.modules.report_memory.repository import apply_postgresql_migrations


@pytest.fixture
def postgres_url():
    valor = (
        os.environ.get("VELTRIX_TEST_POSTGRES_URL")
        or os.environ.get("PEDROCORE_TEST_POSTGRES_URL")
        or ""
    ).strip()
    if not valor:
        pytest.skip("PEDROCORE_TEST_POSTGRES_URL não configurada")
    migrations = Path(__file__).resolve().parents[1] / "migrations"
    apply_postgresql_migrations(valor, migrations)
    PostgreSQLProjectRepository(valor).clear()
    yield valor
    PostgreSQLProjectRepository(valor).clear()


@pytest.fixture
def registry(postgres_url) -> ProjectRegistryService:
    return ProjectRegistryService(PostgreSQLProjectRepository(postgres_url))


def _agora() -> datetime:
    return datetime.now(timezone.utc)


# ===========================================================================
# A migration chegou ao banco
# ===========================================================================


def test_the_table_exists_after_the_migrations_run(postgres_url):
    with psycopg.connect(postgres_url) as conexao:
        existe = conexao.execute("SELECT to_regclass(%s) IS NOT NULL", (TABLE,)).fetchone()[0]
    assert existe is True


def test_the_migration_is_additive_and_the_historical_ones_are_untouched():
    """A 0012 é nova. Nenhuma migration anterior foi editada."""
    migrations = Path(__file__).resolve().parents[1] / "migrations"
    arquivos = sorted(item.name for item in migrations.glob("*.sql"))
    assert arquivos[-1] == "0012_project_registry.sql"
    assert "CREATE TABLE IF NOT EXISTS pedrocore_projects" in (
        migrations / "0012_project_registry.sql"
    ).read_text(encoding="utf-8")


# ===========================================================================
# Ciclo completo contra o banco
# ===========================================================================


def test_the_seeds_land_in_the_database(registry):
    ids = {item.project_id for item in registry.list_projects()}
    assert ids == {project_id for project_id, _ in SEED_PROJECTS}


def test_a_project_created_survives_a_new_connection(postgres_url):
    """Restart real: outro repositório, outra conexão, mesmo dado."""
    ProjectRegistryService(PostgreSQLProjectRepository(postgres_url)).create(
        display_name="Durável", local_path="C:/Projetos/duravel"
    )
    segunda = ProjectRegistryService(PostgreSQLProjectRepository(postgres_url))
    registro = segunda.require("duravel")
    assert registro.display_name == "Durável"
    assert registro.local_path == "C:/Projetos/duravel"


def test_an_edit_survives_a_new_connection(postgres_url):
    ProjectRegistryService(PostgreSQLProjectRepository(postgres_url)).update(
        "elyra", display_name="Elyra QA", repository_url="https://github.com/org/elyra"
    )
    segunda = ProjectRegistryService(PostgreSQLProjectRepository(postgres_url))
    registro = segunda.require("elyra")
    assert registro.display_name == "Elyra QA"
    assert registro.repository_url == "https://github.com/org/elyra"
    # E a identidade não se moveu.
    assert registro.project_id == "elyra"


def test_an_archive_survives_a_new_connection(postgres_url):
    ProjectRegistryService(PostgreSQLProjectRepository(postgres_url)).archive("rivvo")
    segunda = ProjectRegistryService(PostgreSQLProjectRepository(postgres_url))
    assert segunda.require("rivvo").status is ProjectStatus.ARCHIVED
    assert "rivvo" not in {item.project_id for item in segunda.list_projects()}


def test_writing_the_same_project_twice_does_not_duplicate_a_row(registry, postgres_url):
    """`ON CONFLICT` atualiza; ele não insere uma segunda identidade."""
    registry.update("structa", display_name="Structa A")
    registry.update("structa", display_name="Structa B")
    with psycopg.connect(postgres_url) as conexao:
        total = conexao.execute(
            f"SELECT COUNT(*) FROM {TABLE} WHERE project_id = %s", ("structa",)
        ).fetchone()[0]
    assert total == 1
    assert registry.require("structa").display_name == "Structa B"


def test_seeding_a_populated_database_changes_nothing(postgres_url):
    primeira = ProjectRegistryService(PostgreSQLProjectRepository(postgres_url))
    primeira.update("orlabyte", display_name="OrlaByte Editado")
    antes = len(primeira.list_projects())

    segunda = ProjectRegistryService(PostgreSQLProjectRepository(postgres_url))
    assert len(segunda.list_projects()) == antes
    assert segunda.require("orlabyte").display_name == "OrlaByte Editado"


# ===========================================================================
# Isolamento e identidade — impostos pelo SCHEMA
# ===========================================================================


def test_the_database_refuses_a_second_row_with_the_same_identity(registry, postgres_url):
    """Isolamento é CHAVE, não filtro aplicado depois da leitura."""
    with psycopg.connect(postgres_url) as conexao:
        with pytest.raises(psycopg.errors.UniqueViolation):
            conexao.execute(
                f"""
                INSERT INTO {TABLE} (project_id, display_name, status,
                                     created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s)
                """,
                ("structa", "Impostor", "ACTIVE", _agora(), _agora()),
            )


def test_the_database_refuses_a_path_traversing_identity(postgres_url):
    """Um dump reconstruído entra pelo banco, e não pelo validador Python."""
    with psycopg.connect(postgres_url) as conexao:
        with pytest.raises(psycopg.errors.CheckViolation):
            conexao.execute(
                f"""
                INSERT INTO {TABLE} (project_id, display_name, status,
                                     created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s)
                """,
                ("../etc/passwd", "Hostil", "ACTIVE", _agora(), _agora()),
            )


def test_the_database_refuses_an_invented_status(postgres_url):
    with psycopg.connect(postgres_url) as conexao:
        with pytest.raises(psycopg.errors.CheckViolation):
            conexao.execute(
                f"""
                INSERT INTO {TABLE} (project_id, display_name, status,
                                     created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s)
                """,
                ("novo-projeto", "Novo", "DELETED", _agora(), _agora()),
            )


def test_updating_one_project_leaves_the_others_byte_identical(registry):
    antes = {
        item.project_id: item.model_dump()
        for item in registry.list_projects()
        if item.project_id != "finguard"
    }
    registry.update("finguard", display_name="FinGuard Alterado")
    depois = {
        item.project_id: item.model_dump()
        for item in registry.list_projects()
        if item.project_id != "finguard"
    }
    assert depois == antes


def test_reading_one_project_never_returns_another(registry):
    for registro in registry.list_projects():
        assert registry.require(registro.project_id).project_id == registro.project_id


def test_archiving_never_deletes_the_row(registry, postgres_url):
    registry.archive("orlabyte")
    with psycopg.connect(postgres_url) as conexao:
        linha = conexao.execute(
            f"SELECT status FROM {TABLE} WHERE project_id = %s", ("orlabyte",)
        ).fetchone()
    assert linha is not None
    assert linha[0] == "ARCHIVED"


# ===========================================================================
# Fim a fim: projeto criado no banco chega ao Risk Engine
# ===========================================================================


def test_a_project_created_in_postgres_reaches_the_risk_request(postgres_url, monkeypatch):
    """O caminho inteiro, com o catálogo durável no meio."""
    from app.modules.project_registry.service import reset_project_registry
    from app.modules.retrieval.schemas import RetrievalResponse
    from app.modules.retrieval.service import retrieval_service
    from app.modules.risk_console.analysis import analyze
    from app.modules.risk_console.auto_context import apply, propose
    from app.modules.risk_console.domain import ConsoleRequestInput

    monkeypatch.setattr(
        retrieval_service,
        "retrieve",
        lambda query, **_: RetrievalResponse(query_id=query.query_id, project_id=query.project_id),
    )

    servico = ProjectRegistryService(PostgreSQLProjectRepository(postgres_url))
    servico.create(display_name="Projeto Durável")
    reset_project_registry(servico)
    try:
        entrada = ConsoleRequestInput(
            project_id="projeto-duravel",
            environment_label="Desenvolvimento",
            executor_label="Claude Code",
            prompt="Atualize a documentação do projeto.",
        )
        resultado = analyze(apply(entrada, propose(entrada)))
        assert resultado.request.project_id == "projeto-duravel"
        # Sem manifesto declarado, nenhuma capacidade é assumida pelo nome.
        assert servico.has_manifest("projeto-duravel") is False
        assert resultado.analysis.target_operation_executed is False
    finally:
        reset_project_registry(None)


def test_a_record_round_trips_through_the_database_unchanged(postgres_url):
    store = PostgreSQLProjectRepository(postgres_url)
    original = ProjectRecord(
        project_id="ida-e-volta",
        display_name="Ida e Volta",
        local_path="C:/Projetos/ida",
        repository_url="https://github.com/org/ida",
        status=ProjectStatus.ACTIVE,
        created_at=_agora(),
        updated_at=_agora(),
        capability_manifest_reference=None,
    )
    store.upsert(original)
    devolvido = store.get("ida-e-volta")
    assert devolvido is not None
    assert devolvido.model_dump(exclude={"created_at", "updated_at"}) == (
        original.model_dump(exclude={"created_at", "updated_at"})
    )
