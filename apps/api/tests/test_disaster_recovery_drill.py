"""Ensaio de recuperação REAL, contra PostgreSQL descartável.

Por que este arquivo existe separado
------------------------------------

`test_platform_operations.py` prova a MECÂNICA do DR com estruturas em
memória: ordem, digest, divergência, ausência. Isso é necessário e não é
suficiente.

Se o estado produtivo mora em PostgreSQL, um ensaio que só compara dicionários
prova que o comparador funciona — não que o banco volta. Aqui o ciclo acontece
onde o dado realmente está:

    backup do banco  ->  DROP das tabelas  ->  restaurar  ->  verificar

Sem `PEDROCORE_TEST_POSTGRES_URL` o arquivo inteiro fica `skip`. Nenhum dado
real, nenhum dado de consumidor: tudo sintético, e o banco é descartável.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import psycopg
import pytest

from app.modules.asset_registry.schemas import AssetKind
from app.modules.asset_registry.service import asset_registry_service
from app.modules.disaster_recovery.service import (
    EPHEMERAL_BY_DESIGN,
    RestoreOutcome,
    disaster_recovery_service,
    restore_sequence,
)
from app.modules.evaluation_plane.schemas import (
    EvaluationMetric,
    EvaluationSubject,
    EvaluationSubjectKind,
)
from app.modules.evaluation_plane.service import evaluation_plane_service
from app.modules.model_registry.schemas import ModelStatus
from app.modules.model_registry.service import model_registry_service
from app.modules.disaster_recovery.postgres import (
    forget_migrations,
    rebuild_schema,
    tables_present,
)
from app.modules.platform_persistence.repository import PostgreSQLPlatformRepository

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)

# As tabelas que o ensaio derruba e recupera. Só as da plataforma: derrubar o
# schema inteiro tornaria o teste lento e não provaria mais nada.
DRILL_TABLES = (
    "pedrocore_model_transitions",
    "pedrocore_model_entries",
    "pedrocore_asset_versions",
    "pedrocore_evaluation_records",
)

# A migration que cria essas tabelas. Reconstruir schema exige dizer QUAIS
# migrations precisam valer de novo — o runner pula tudo que ja registrou.
DRILL_MIGRATIONS = ["0011_platform_registries.sql"]


@pytest.fixture
def postgres_url():
    """Banco descartavel, com schema garantido antes e depois.

    A limpeza usa `rebuild_schema`, e nao o runner direto, pelo mesmo motivo
    que a restauracao usa: um teste que derruba tabelas deixa o banco sem elas
    e com o livro-razao intacto. A propria fixture caiu nessa armadilha antes
    de o procedimento existir.
    """
    valor = (os.environ.get("PEDROCORE_TEST_POSTGRES_URL") or "").strip()
    if not valor:
        pytest.skip("PEDROCORE_TEST_POSTGRES_URL não configurada")
    migrations = Path(__file__).resolve().parents[1] / "migrations"

    def preparar() -> None:
        rebuild_schema(valor, migrations, DRILL_MIGRATIONS)
        PostgreSQLPlatformRepository(valor).clear()
        model_registry_service.reset()
        asset_registry_service.reset()
        evaluation_plane_service.reset()

    preparar()
    yield valor
    preparar()


def _seed(url: str) -> None:
    """Estado sintético produzido pelos serviços reais, não por INSERT solto."""
    store = PostgreSQLPlatformRepository(url)
    model_registry_service.set_repository(store)
    asset_registry_service.set_repository(store)
    evaluation_plane_service.set_repository(store)

    evaluation_plane_service.record(
        subject=EvaluationSubject(
            kind=EvaluationSubjectKind.MODEL, subject_id="anthropic:claude-sonnet:5"
        ),
        suite="qa-regressao",
        suite_version="1.0",
        environment="test",
        project_id="alpha",
        producer="ci-sintetico",
        dataset_id="ds-sintetico",
        metrics=(
            EvaluationMetric(name="acuracia", value=0.93, unit="ratio", sample_size=80),
        ),
        now=NOW,
    )

    entrada = model_registry_service.register(
        provider="anthropic", model_name="claude-sonnet", model_version="5", now=NOW
    )
    for alvo, ev in (
        (ModelStatus.CANDIDATE, None),
        (ModelStatus.EVALUATING, None),
        (ModelStatus.APPROVED, "eval-drill"),
        (ModelStatus.PROMOTED, "eval-drill"),
    ):
        model_registry_service.transition(
            entrada.model_key, alvo, reason="ensaio", actor="ci", evaluation_id=ev, now=NOW
        )

    asset_registry_service.publish(
        asset_id="assistant.system",
        kind=AssetKind.SYSTEM_PROMPT,
        content="Você é um assistente técnico.",
        provenance="veltrix/core",
        author="ci-sintetico",
        change_reason="versão inicial",
        now=NOW,
    )
    asset_registry_service.activate("assistant.system", 1)


def _serializar(campo):
    """Valor gravavel de volta no banco.

    JSONB volta do driver como lista/dicionario Python. `str()` neles produz
    repr com aspas simples, que nao e JSON valido — e o INSERT de volta falha
    apontando para o dado quando o problema e a serializacao.
    """
    if isinstance(campo, (list, dict)):
        return json.dumps(campo, default=str)
    return None if campo is None else str(campo)


def _dump(url: str) -> dict[str, list]:
    """Fotografa as tabelas como listas de linhas serializaveis."""
    fotografia: dict[str, list] = {}
    with psycopg.connect(url) as conexao:
        for tabela in DRILL_TABLES:
            linhas = conexao.execute(
                f"SELECT * FROM {tabela} ORDER BY 1, 2"  # noqa: S608 - nome fixo
            ).fetchall()
            fotografia[tabela] = [
                [_serializar(campo) for campo in linha] for linha in linhas
            ]
    return fotografia


def _destroy(url: str) -> None:
    """DROP de verdade. Sem isto, o ensaio passaria com um backup vazio."""
    with psycopg.connect(url) as conexao:
        for tabela in DRILL_TABLES:
            conexao.execute(f"DROP TABLE IF EXISTS {tabela} CASCADE")  # noqa: S608


def _restore(url: str, fotografia: dict[str, list]) -> dict[str, list]:
    """Reconstrói o schema e reinsere o conteúdo salvo.

    `rebuild_schema` e nao o runner direto: depois de um DROP, o runner sozinho
    nao recria nada, porque le no livro-razao que a migration ja foi aplicada.
    """
    migrations = Path(__file__).resolve().parents[1] / "migrations"
    rebuild_schema(url, migrations, DRILL_MIGRATIONS)

    presentes = tables_present(url, list(DRILL_TABLES))
    assert set(presentes) == set(DRILL_TABLES), (
        "schema não foi reconstruído; reinserir dado agora falharia linha a "
        "linha e apontaria para o dado quando o problema é o schema"
    )

    with psycopg.connect(url) as conexao:
        for tabela in restore_order_for(fotografia):
            linhas = fotografia[tabela]
            if not linhas:
                continue
            colunas = conexao.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = %s ORDER BY ordinal_position",
                (tabela,),
            ).fetchall()
            nomes = ", ".join(item[0] for item in colunas)
            marcadores = ", ".join(["%s"] * len(colunas))
            for linha in linhas:
                conexao.execute(
                    f"INSERT INTO {tabela} ({nomes}) VALUES ({marcadores})",  # noqa: S608
                    linha,
                )
    return _dump(url)


def restore_order_for(fotografia: dict[str, list]) -> list[str]:
    """Ordem declarada, restrita ao que existe na fotografia.

    Reinserir transição antes da entrada de modelo violaria a dependência que
    o plano declara — e é justamente isso que o plano existe para evitar.
    """
    declarada = [
        item.store_id for item in restore_sequence() if item.store_id in fotografia
    ]
    restantes = [nome for nome in fotografia if nome not in declarada]
    return declarada + restantes


# ===========================================================================


def test_the_real_drill_backs_up_destroys_restores_and_verifies(postgres_url):
    """O ciclo completo, onde o dado realmente mora."""
    _seed(postgres_url)
    fotografia = _dump(postgres_url)
    assert fotografia["pedrocore_model_entries"], "estado sintético não foi criado"

    manifesto = disaster_recovery_service.backup(
        fotografia, backup_id="drill-real-001", now=NOW
    )

    _destroy(postgres_url)
    with psycopg.connect(postgres_url) as conexao:
        existentes = conexao.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_name = ANY(%s)",
            (list(DRILL_TABLES),),
        ).fetchall()
    assert existentes == [], "a destruição não aconteceu; o ensaio não provaria nada"

    restaurado = _restore(postgres_url, fotografia)
    verificacao = disaster_recovery_service.verify_restore(
        manifesto, restaurado, now=NOW
    )

    assert verificacao.outcome is RestoreOutcome.VERIFIED
    assert verificacao.proven is True
    assert verificacao.mismatched_stores == []


def test_the_restored_database_still_serves_the_services(postgres_url):
    """Restaurar é meio; o fim é o sistema voltar a funcionar."""
    _seed(postgres_url)
    fotografia = _dump(postgres_url)
    _destroy(postgres_url)
    _restore(postgres_url, fotografia)

    model_registry_service.reset()
    evaluation_plane_service.reset()
    asset_registry_service.reset()
    store = PostgreSQLPlatformRepository(postgres_url)
    model_registry_service.set_repository(store)
    evaluation_plane_service.set_repository(store)
    asset_registry_service.set_repository(store)

    promovidos = model_registry_service.promoted()
    assert len(promovidos) == 1
    assert promovidos[0].model_key == "anthropic:claude-sonnet:5"
    assert asset_registry_service.active_for("assistant.system").version == 1
    assert evaluation_plane_service.for_subject("alpha", "anthropic:claude-sonnet:5")


def test_a_corrupted_restore_is_caught_against_the_real_database(postgres_url):
    """A prova precisa poder reprovar — e reprova sobre o banco, não sobre dict."""
    _seed(postgres_url)
    fotografia = _dump(postgres_url)
    manifesto = disaster_recovery_service.backup(
        fotografia, backup_id="drill-real-002", now=NOW
    )

    _destroy(postgres_url)
    corrompida = {
        nome: (linhas[:-1] if nome == "pedrocore_model_transitions" else linhas)
        for nome, linhas in fotografia.items()
    }
    restaurado = _restore(postgres_url, corrompida)

    verificacao = disaster_recovery_service.verify_restore(
        manifesto, restaurado, now=NOW
    )
    assert verificacao.outcome is RestoreOutcome.INTEGRITY_FAILED
    assert "pedrocore_model_transitions" in verificacao.mismatched_stores


def test_a_store_that_never_comes_back_is_reported_missing(postgres_url):
    _seed(postgres_url)
    fotografia = _dump(postgres_url)
    manifesto = disaster_recovery_service.backup(
        fotografia, backup_id="drill-real-003", now=NOW
    )
    parcial = {k: v for k, v in fotografia.items() if k != "pedrocore_asset_versions"}

    verificacao = disaster_recovery_service.verify_restore(manifesto, parcial, now=NOW)
    assert verificacao.outcome is RestoreOutcome.INCOMPLETE
    assert "pedrocore_asset_versions" in verificacao.missing_stores


def test_the_drill_uses_only_synthetic_data(postgres_url):
    """Nenhum dado real, nenhum dado de consumidor — verificável."""
    _seed(postgres_url)
    fotografia = _dump(postgres_url)
    texto = str(fotografia)
    for marcador in ("@gmail", "@outlook", "postgresql://", "sk-", "Bearer "):
        assert marcador not in texto


def test_the_plan_declares_what_is_deliberately_not_restored():
    """Não restaurar observação viva é decisão, não esquecimento."""
    assert set(EPHEMERAL_BY_DESIGN) == {
        "correlation_trail",
        "shadow_comparisons",
        "slo_samples",
        "policy_evaluations",
    }
    for motivo in EPHEMERAL_BY_DESIGN.values():
        assert len(motivo) > 40, "um motivo curto demais não explica a decisão"


def test_the_declared_order_covers_the_platform_tables():
    ordem = [item.store_id for item in restore_sequence()]
    assert ordem.index("pedrocore_evaluation_records") < ordem.index(
        "pedrocore_model_entries"
    ), "modelo promovido antes da evidência seria estado que o banco recusa"
    assert ordem.index("pedrocore_model_entries") < ordem.index(
        "pedrocore_model_transitions"
    )


def test_the_runner_alone_does_not_recreate_dropped_tables(postgres_url):
    """A falha silenciosa que o ensaio real encontrou.

    Com as tabelas derrubadas e o livro-razao intacto, o runner le que a
    migration ja foi aplicada e nao faz nada. O operador ve "0 aplicadas",
    conclui que esta tudo certo, e o banco continua sem as tabelas.
    """
    from app.modules.report_memory.repository import apply_postgresql_migrations

    _seed(postgres_url)
    _destroy(postgres_url)

    aplicadas = apply_postgresql_migrations(
        postgres_url, Path(__file__).resolve().parents[1] / "migrations"
    )
    assert DRILL_MIGRATIONS[0] not in aplicadas, "o runner reaplicou sozinho"
    assert tables_present(postgres_url, list(DRILL_TABLES)) == []


def test_rebuild_schema_is_what_actually_brings_the_tables_back(postgres_url):
    _seed(postgres_url)
    _destroy(postgres_url)

    aplicadas = rebuild_schema(
        postgres_url,
        Path(__file__).resolve().parents[1] / "migrations",
        DRILL_MIGRATIONS,
    )
    assert DRILL_MIGRATIONS[0] in aplicadas
    assert set(tables_present(postgres_url, list(DRILL_TABLES))) == set(DRILL_TABLES)


def test_forgetting_reports_what_was_actually_forgotten(postgres_url):
    """Pedir para esquecer o que não estava registrado é sinal de discordância."""
    _seed(postgres_url)
    assert forget_migrations(postgres_url, DRILL_MIGRATIONS) == DRILL_MIGRATIONS
    assert forget_migrations(postgres_url, ["9999_inexistente.sql"]) == []
