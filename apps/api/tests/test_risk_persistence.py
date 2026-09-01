"""Risk Engine V2 — Stage R2: persistência própria do domínio Risk.

O problema (P1 do baseline R0)
-------------------------------

O Risk Engine não tinha onde guardar a própria história: lia de `report_memory`
e `operational_memory`. Na prática, `PEDROCORE_REPORT_MEMORY_PERSISTENCE=off`
decidia em silêncio se o motor de risco tinha ou não histórico — uma variável de
outro domínio governando este.

O teste que fecha P1 é `test_risk_history_survives_report_memory_being_off`:
com Report Memory desligada e persistência de risco ligada, a história do risco
continua existindo e recuperável.

O que mais se prova aqui
------------------------

Isolamento de projeto na chave, idempotência de replay, conflito de conteúdo,
fail-closed em toda configuração inválida, e ausência de texto livre no
registro persistido.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.modules.risk_engine.persistence_schemas import (
    PersistedRiskDimension,
    RiskAnalysisRecord,
    RiskOutcomeRecord,
)
from app.modules.risk_engine.persistence_service import risk_persistence_service
from app.modules.risk_engine.repository import (
    FLAG_RISK_DATABASE_URL,
    FLAG_RISK_PERSISTENCE,
    InMemoryRiskRepository,
    PostgreSQLRiskRepository,
    RiskRecordConflictError,
    RiskRepositoryConfigurationError,
    build_risk_repository,
    fingerprint_of,
    require_risk_repository,
    risk_persistence_mode,
)

NOW = datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc)
ALPHA = "alpha"
BETA = "beta"


@pytest.fixture(autouse=True)
def isolated(monkeypatch):
    monkeypatch.delenv(FLAG_RISK_PERSISTENCE, raising=False)
    monkeypatch.delenv(FLAG_RISK_DATABASE_URL, raising=False)
    risk_persistence_service.set_repository(None)
    yield
    risk_persistence_service.set_repository(None)


@pytest.fixture
def repository() -> InMemoryRiskRepository:
    return InMemoryRiskRepository()


def _analysis(
    analysis_id: str = "risk-analysis-001",
    project_id: str = ALPHA,
    severity: str = "HIGH",
    **overrides,
) -> RiskAnalysisRecord:
    payload = {"analysis_id": analysis_id, "project_id": project_id, "severity": severity}
    values = {
        "analysis_id": analysis_id,
        "project_id": project_id,
        "request_id": "request-001",
        "analysis_policy_version": "pre-execution-risk-v1",
        "severity": severity,
        "confidence": 0.8,
        "uncertainty": 0.2,
        "dimensions": (
            PersistedRiskDimension(dimension="scope_risk", score=0.7, severity="HIGH"),
        ),
        "reason_codes": ("SECRETS_OR_ENV",),
        "blast_radius_level": "HIGH",
        "fingerprint": fingerprint_of(payload),
        "created_at": NOW,
    }
    values.update(overrides)
    return RiskAnalysisRecord(**values)


def _outcome(
    outcome_id: str = "risk-outcome-001",
    project_id: str = ALPHA,
    status: str = "passed",
    **overrides,
) -> RiskOutcomeRecord:
    payload = {"outcome_id": outcome_id, "project_id": project_id, "status": status}
    values = {
        "outcome_id": outcome_id,
        "project_id": project_id,
        "risk_analysis_id": "risk-analysis-001",
        "contract_id": "contract-001",
        "evidence_id": "evidence-001",
        "outcome_policy_version": "post-execution-v1",
        "effective_gate": "PASS",
        "status": status,
        "contract_valid": True,
        "predicted_dimensions": {"scope_risk": 0.7},
        "actual_issue_codes": (),
        "predicted_risk_materialized": False,
        "unpredicted_issue_detected": False,
        "scope_deviation": (),
        "fingerprint": fingerprint_of(payload),
        "created_at": NOW,
    }
    values.update(overrides)
    return RiskOutcomeRecord(**values)


# ---------------------------------------------------------------------------
# P1 — a razão de existir desta Stage
# ---------------------------------------------------------------------------


def test_risk_history_survives_report_memory_being_off(monkeypatch, repository):
    """O teste que fecha P1.

    Report Memory desligada, persistência de risco ligada: a história do
    domínio Risk continua existindo. Antes desta Stage, a variável de outro
    domínio determinava, sozinha e em silêncio, se havia histórico.
    """
    monkeypatch.setenv("PEDROCORE_REPORT_MEMORY_PERSISTENCE", "off")
    monkeypatch.setenv(FLAG_RISK_PERSISTENCE, "memory")
    risk_persistence_service.set_repository(repository)

    repository.add_analysis(_analysis())
    repository.add_outcome(_outcome())

    history = risk_persistence_service.history(ALPHA)
    assert history.sample_size == 1
    assert history.analyses[0].analysis_id == "risk-analysis-001"
    assert history.outcomes[0].outcome_id == "risk-outcome-001"

    # E a memória operacional continua desligada — nada aqui a ligou de volta.
    from app.modules.report_memory.service import persistence_mode

    assert persistence_mode() == "off"


def test_risk_persistence_mode_is_independent_from_report_memory(monkeypatch):
    """A chave do Risk é dele. Mudar a do Report Memory não move a deste."""
    monkeypatch.setenv("PEDROCORE_REPORT_MEMORY_PERSISTENCE", "postgresql")
    assert risk_persistence_mode() == "off"

    monkeypatch.setenv(FLAG_RISK_PERSISTENCE, "memory")
    monkeypatch.setenv("PEDROCORE_REPORT_MEMORY_PERSISTENCE", "off")
    assert risk_persistence_mode() == "memory"


# ---------------------------------------------------------------------------
# InMemory — escrita, leitura, isolamento
# ---------------------------------------------------------------------------


def test_persist_and_retrieve_analysis(repository):
    assert repository.add_analysis(_analysis()) is True
    found = repository.get_analysis(ALPHA, "risk-analysis-001")
    assert found is not None
    assert found.severity == "HIGH"
    assert found.reason_codes == ("SECRETS_OR_ENV",)


def test_persist_and_retrieve_outcome(repository):
    assert repository.add_outcome(_outcome()) is True
    found = repository.get_outcome(ALPHA, "risk-outcome-001")
    assert found is not None
    assert found.status == "passed"
    assert found.risk_analysis_id == "risk-analysis-001"


def test_project_isolation_is_in_the_key_not_in_a_filter(repository):
    """Buscar com o projeto errado não devolve o registro do outro.

    A leitura recebe `project_id` e o usa na consulta. O desenho alternativo —
    buscar por id e comparar depois — já teria carregado o dado do outro
    projeto antes de decidir, e bastaria esquecer o `if` uma vez.
    """
    repository.add_analysis(_analysis(project_id=ALPHA))
    assert repository.get_analysis(ALPHA, "risk-analysis-001") is not None
    assert repository.get_analysis(BETA, "risk-analysis-001") is None


def test_history_never_mixes_projects(repository):
    repository.add_analysis(_analysis(project_id=ALPHA))
    repository.add_analysis(_analysis(analysis_id="risk-analysis-002", project_id=BETA))
    repository.add_outcome(_outcome(project_id=BETA))

    alpha = repository.history(ALPHA)
    assert [item.project_id for item in alpha.analyses] == [ALPHA]
    assert alpha.outcomes == ()

    beta = repository.history(BETA)
    assert [item.project_id for item in beta.analyses] == [BETA]
    assert beta.sample_size == 1


def test_same_id_in_two_projects_is_two_records(repository):
    """Id igual em projetos diferentes não é colisão: são registros distintos."""
    repository.add_analysis(_analysis(project_id=ALPHA))
    assert repository.add_analysis(_analysis(project_id=BETA)) is True
    assert repository.count(ALPHA) == 1
    assert repository.count(BETA) == 1


# ---------------------------------------------------------------------------
# Idempotência e conflito
# ---------------------------------------------------------------------------


def test_identical_replay_is_a_no_op(repository):
    """Reenvio idêntico é ruído esperado, não erro nem cópia."""
    assert repository.add_analysis(_analysis()) is True
    assert repository.add_analysis(_analysis()) is False
    assert repository.count(ALPHA) == 1


def test_same_id_with_different_content_is_a_conflict(repository):
    """Sobrescrever apagaria o registro original sem ninguém saber.

    Mesmo id com conteúdo diferente é sinal de bug ou adulteração — o oposto de
    um replay, e por isso tratado de forma oposta.
    """
    repository.add_analysis(_analysis(severity="HIGH"))
    with pytest.raises(RiskRecordConflictError) as error:
        repository.add_analysis(_analysis(severity="CRITICAL"))
    assert error.value.record_id == "risk-analysis-001"
    # O original sobreviveu intacto.
    assert repository.get_analysis(ALPHA, "risk-analysis-001").severity == "HIGH"


def test_outcome_replay_and_conflict_behave_the_same_way(repository):
    assert repository.add_outcome(_outcome()) is True
    assert repository.add_outcome(_outcome()) is False
    with pytest.raises(RiskRecordConflictError):
        repository.add_outcome(_outcome(status="failed"))


# ---------------------------------------------------------------------------
# Fail-closed — caminho desonesto e configuração inválida
# ---------------------------------------------------------------------------


def test_persistence_is_off_by_default():
    """Default `off` preserva o comportamento anterior à Stage."""
    assert risk_persistence_mode() == "off"
    assert build_risk_repository() is None
    assert risk_persistence_service.enabled() is False


def test_requiring_a_disabled_repository_raises():
    """Desabilitado levanta em vez de devolver store vazio.

    Recorte vazio faria quem pergunta confundir "não há histórico" com "não há
    onde guardar histórico" — e as duas coisas levam a decisões diferentes.
    """
    with pytest.raises(RiskRepositoryConfigurationError):
        require_risk_repository()


def test_invalid_persistence_mode_is_refused(monkeypatch):
    monkeypatch.setenv(FLAG_RISK_PERSISTENCE, "talvez")
    with pytest.raises(RiskRepositoryConfigurationError) as error:
        risk_persistence_mode()
    assert "inválido" in str(error.value)


def test_postgresql_without_a_url_fails_closed(monkeypatch):
    """Modo postgres sem URL não cai para memória."""
    monkeypatch.setenv(FLAG_RISK_PERSISTENCE, "postgresql")
    monkeypatch.delenv(FLAG_RISK_DATABASE_URL, raising=False)
    with pytest.raises(RiskRepositoryConfigurationError):
        build_risk_repository()


def test_postgresql_does_not_reuse_another_domains_url(monkeypatch):
    """A URL do Report Memory não serve para o Risk por conta própria.

    Reaproveitá-la em silêncio recriaria o acoplamento que a Stage desfez, só
    que num lugar mais difícil de ver.
    """
    monkeypatch.setenv(FLAG_RISK_PERSISTENCE, "postgresql")
    monkeypatch.setenv(
        "PEDROCORE_REPORT_MEMORY_DATABASE_URL", "postgresql://u:p@localhost/other"
    )
    monkeypatch.delenv(FLAG_RISK_DATABASE_URL, raising=False)
    with pytest.raises(RiskRepositoryConfigurationError):
        build_risk_repository()


def test_postgresql_mode_builds_the_postgres_repository(monkeypatch):
    monkeypatch.setenv(FLAG_RISK_PERSISTENCE, "postgresql")
    monkeypatch.setenv(FLAG_RISK_DATABASE_URL, "postgresql://u:p@localhost/risk")
    assert isinstance(build_risk_repository(), PostgreSQLRiskRepository)


def test_unreachable_postgres_raises_instead_of_falling_back(monkeypatch):
    """Banco indisponível não vira memória.

    Um histórico que silenciosamente vira efêmero faria um BLOCK baseado em
    histórico mudar de comportamento sem ninguém perceber.
    """
    from app.modules.risk_engine.repository import RiskRepositoryError

    monkeypatch.setenv(FLAG_RISK_PERSISTENCE, "postgresql")
    monkeypatch.setenv(
        FLAG_RISK_DATABASE_URL,
        "postgresql://invalid:invalid@127.0.0.1:1/none?connect_timeout=1",
    )
    repository = build_risk_repository()
    with pytest.raises(RiskRepositoryError):
        repository.get_analysis(ALPHA, "risk-analysis-001")


def test_unknown_record_returns_none_not_an_empty_record(repository):
    assert repository.get_analysis(ALPHA, "nao-existe") is None
    assert repository.get_outcome(ALPHA, "nao-existe") is None


# ---------------------------------------------------------------------------
# Privacidade — o registro não guarda conteúdo do consumidor
# ---------------------------------------------------------------------------


def test_the_persisted_record_has_nowhere_to_put_free_text():
    """A proteção é a ausência de campo, não um sanitizador que roda depois."""
    forbidden = {
        "request_text",
        "prompt",
        "command",
        "diff",
        "payload",
        "message",
        "content",
        "raw",
    }
    assert not (set(RiskAnalysisRecord.model_fields) & forbidden)
    assert not (set(RiskOutcomeRecord.model_fields) & forbidden)


def test_extra_fields_are_refused_on_the_persisted_record():
    """`extra=forbid`: nada entra no registro por descuido de quem projeta."""
    with pytest.raises(ValueError):
        _analysis(request_text="apague o banco de producao")


def test_reason_codes_cannot_smuggle_free_text():
    """Lista de códigos com entrada gigante viraria campo de texto livre."""
    with pytest.raises(ValueError, match="longa demais"):
        _analysis(reason_codes=("x" * 200,))


# ---------------------------------------------------------------------------
# Projeção a partir do domínio
# ---------------------------------------------------------------------------


def test_history_ratio_is_none_without_outcomes(repository):
    """Zero seria uma afirmação; `None` é a verdade — não há o que comparar."""
    repository.add_analysis(_analysis())
    assert repository.history(ALPHA).materialized_ratio() is None


def test_history_ratio_counts_materialized_predictions(repository):
    repository.add_outcome(_outcome(outcome_id="o1", predicted_risk_materialized=True))
    repository.add_outcome(_outcome(outcome_id="o2", predicted_risk_materialized=False))
    assert repository.history(ALPHA).materialized_ratio() == pytest.approx(0.5)


def test_history_respects_the_read_ceiling(repository):
    """Histórico cresce sem limite natural; a consulta não pode crescer junto."""
    for index in range(12):
        repository.add_outcome(
            _outcome(
                outcome_id=f"o{index:03d}",
                created_at=NOW + timedelta(minutes=index),
            )
        )
    assert len(repository.history(ALPHA, limit=5).outcomes) == 5


def test_recording_is_a_no_op_when_persistence_is_disabled():
    """Desligado não escreve e não levanta: é o comportamento anterior."""
    assert risk_persistence_service.enabled() is False
    assert risk_persistence_service.record_analysis(object()) is False
    assert risk_persistence_service.record_outcome(object()) is False


# ---------------------------------------------------------------------------
# PostgreSQL — opt-in, mesmo padrao das demais suites de persistencia
# ---------------------------------------------------------------------------


@pytest.fixture
def postgres_url():
    """URL de teste real. Sem ela, os casos abaixo ficam `skip`.

    Nao ha simulacao de PostgreSQL aqui: um duble provaria que o duble
    funciona. Enquanto nao houver banco de teste, estes casos permanecem
    honestamente nao executados.
    """
    import os
    from pathlib import Path

    from app.modules.report_memory.repository import apply_postgresql_migrations

    value = (os.environ.get("PEDROCORE_TEST_POSTGRES_URL") or "").strip()
    if not value:
        pytest.skip("PEDROCORE_TEST_POSTGRES_URL não configurada")
    apply_postgresql_migrations(value, Path(__file__).resolve().parents[1] / "migrations")
    repository = PostgreSQLRiskRepository(value)
    repository.clear()
    yield value
    repository.clear()


def test_postgresql_migration_creates_the_risk_tables(postgres_url):
    """A migration 0009 e aplicada pelo runner ja existente."""
    repository = PostgreSQLRiskRepository(postgres_url)
    assert repository.count(ALPHA) == 0


def test_postgresql_persists_and_retrieves(postgres_url):
    repository = PostgreSQLRiskRepository(postgres_url)
    assert repository.add_analysis(_analysis()) is True
    assert repository.add_outcome(_outcome()) is True

    found = repository.get_analysis(ALPHA, "risk-analysis-001")
    assert found is not None and found.severity == "HIGH"
    assert repository.get_outcome(ALPHA, "risk-outcome-001").status == "passed"


def test_postgresql_is_idempotent_and_detects_conflict(postgres_url):
    repository = PostgreSQLRiskRepository(postgres_url)
    assert repository.add_analysis(_analysis()) is True
    assert repository.add_analysis(_analysis()) is False
    with pytest.raises(RiskRecordConflictError):
        repository.add_analysis(_analysis(severity="CRITICAL"))


def test_postgresql_isolates_projects(postgres_url):
    """Isolamento e chave primaria composta, garantido pelo banco."""
    repository = PostgreSQLRiskRepository(postgres_url)
    repository.add_analysis(_analysis(project_id=ALPHA))
    repository.add_analysis(_analysis(project_id=BETA))

    assert repository.get_analysis(ALPHA, "risk-analysis-001").project_id == ALPHA
    assert repository.get_analysis(BETA, "risk-analysis-001").project_id == BETA
    assert repository.history(ALPHA).analyses[0].project_id == ALPHA


def test_postgresql_history_survives_a_new_repository_instance(postgres_url):
    """Durabilidade: instancia nova, mesmo banco, historia continua la."""
    PostgreSQLRiskRepository(postgres_url).add_outcome(_outcome())
    revived = PostgreSQLRiskRepository(postgres_url)
    assert revived.history(ALPHA).sample_size == 1


# ---------------------------------------------------------------------------
# Stage R3 e fechamento — o que a migration 0010 acrescentou, contra banco real
# ---------------------------------------------------------------------------


def test_postgresql_migration_0010_adds_the_blast_metric_columns(postgres_url):
    """As quatro colunas do R3 existem, e todas nasceram opcionais.

    Contar coluna a coluna em vez de confiar no runner: um INSERT desalinhado
    com o SELECT so aparece contra banco de verdade, e foi exatamente esse o
    erro que a contagem manual pegou durante o R3.
    """
    import psycopg

    with psycopg.connect(postgres_url) as connection:
        rows = connection.execute(
            """
            SELECT column_name, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'pedrocore_risk_analyses'
              AND column_name LIKE 'blast_%'
            ORDER BY column_name
            """
        ).fetchall()

    columns = {name: nullable for name, nullable in rows}
    assert set(columns) == {
        "blast_boundary_counts",
        "blast_boundary_breadth",
        "blast_item_extent",
        "blast_metric_version",
        "blast_radius_level",
    }
    for name in (
        "blast_boundary_counts",
        "blast_boundary_breadth",
        "blast_item_extent",
        "blast_metric_version",
    ):
        assert columns[name] == "YES", f"{name} deveria ser nullable (migration aditiva)"


def test_postgresql_persists_and_returns_the_blast_metric(postgres_url):
    """A métrica volta do banco igual à que entrou."""
    repository = PostgreSQLRiskRepository(postgres_url)
    record = _analysis(
        analysis_id="risk-analysis-metric",
        blast_metric_version="blast-radius-metric-v1",
        blast_boundary_breadth=3,
        blast_item_extent=7,
        blast_boundary_counts={"files": 4, "modules": 2, "database": 1},
    )
    assert repository.add_analysis(record) is True

    found = PostgreSQLRiskRepository(postgres_url).get_analysis(ALPHA, "risk-analysis-metric")
    assert found is not None
    assert found.blast_metric_version == "blast-radius-metric-v1"
    assert found.blast_boundary_breadth == 3
    assert found.blast_item_extent == 7
    assert found.blast_boundary_counts == {"files": 4, "modules": 2, "database": 1}


def test_postgresql_keeps_pre_r3_records_without_a_metric(postgres_url):
    """Registro anterior ao R3 continua sem métrica — e não vira zero.

    Zero seria indistinguivel de "nada foi atingido", que e uma afirmacao que
    ninguem mediu.
    """
    repository = PostgreSQLRiskRepository(postgres_url)
    assert repository.add_analysis(_analysis(analysis_id="risk-analysis-legacy")) is True

    found = repository.get_analysis(ALPHA, "risk-analysis-legacy")
    assert found.blast_metric_version is None
    assert found.blast_boundary_breadth is None
    assert found.blast_item_extent is None
    assert found.blast_boundary_counts is None


def test_postgresql_history_feeds_the_historical_risk_service(postgres_url, monkeypatch):
    """A ponte do R2.1, agora contra banco real e não contra o store isolado.

    Este e o caso que a auditoria do Stage R2 apontou como nao provado: o que
    importa nao e o repositorio responder, e o SERVICO de historico ler dele.
    """
    monkeypatch.setenv(FLAG_RISK_PERSISTENCE, "postgresql")
    monkeypatch.setenv(FLAG_RISK_DATABASE_URL, postgres_url)
    risk_persistence_service.reset()

    repository = PostgreSQLRiskRepository(postgres_url)
    repository.add_analysis(_analysis(analysis_id="risk-analysis-hist"))
    repository.add_outcome(_outcome(outcome_id="risk-outcome-hist"))

    history = risk_persistence_service.history(ALPHA)
    assert history.sample_size >= 1
    assert any(item.analysis_id == "risk-analysis-hist" for item in history.analyses)
    assert all(item.project_id == ALPHA for item in history.analyses)
    risk_persistence_service.reset()
