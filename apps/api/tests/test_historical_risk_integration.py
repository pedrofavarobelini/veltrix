"""Risk Engine V2 — Stage R2.1: Historical Risk usa a persistência própria.

O que o R2 provou, e o que ele NÃO provou
------------------------------------------

O Stage R2 criou o repositório de risco e provou que **ele** funciona com
Report Memory desligada. Isso é independência do *store*.

O que ficou sem prova foi a independência do **serviço**: o
`HistoricalRiskService` continuava reconstruindo `risk_policy_version` — um
fato do domínio Risk — lendo metadata de Report Memory. Com Report Memory
desligada, a política simplesmente não era resolvida, e a consulta histórica
devolvia menos do que sabia.

O gate do R2 foi superestimado por medir a camada errada. Esta suíte mede a
certa: o serviço oficial e o endpoint público.

A correlação usada
------------------

Verificada no fluxo pós-execução, não suposta:

    evidence.source_id == report_id == outcome_id
        -> RiskOutcomeRecord.risk_analysis_id
        -> RiskAnalysisRecord.analysis_policy_version
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.modules.operational_memory.schemas import (
    EvidenceReference,
    EvidenceSourceType,
)
from app.modules.risk_engine.historical_service import (
    POLICY_SOURCE_LEGACY_REPORT,
    POLICY_SOURCE_RISK_DOMAIN,
    HistoricalRiskService,
    historical_risk_service,
)
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
    RiskRepositoryError,
    fingerprint_of,
)

NOW = datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc)
PROJECT = "alpha"
OUTCOME_ID = "risk-outcome-hist-001"
ANALYSIS_ID = "risk-analysis-hist-001"
RISK_POLICY = "pre-execution-risk-v1"


@pytest.fixture(autouse=True)
def isolated(monkeypatch):
    monkeypatch.delenv(FLAG_RISK_PERSISTENCE, raising=False)
    monkeypatch.delenv(FLAG_RISK_DATABASE_URL, raising=False)
    risk_persistence_service.set_repository(None)
    yield
    risk_persistence_service.set_repository(None)


class _Memory:
    """Memória operacional mínima: só a evidência que a correlação usa."""

    def __init__(self, source_id: str = OUTCOME_ID) -> None:
        self.evidence = [
            EvidenceReference(
                source_type=EvidenceSourceType.REPORT,
                source_id=source_id,
                source_reliability=0.9,
                evidence_strength=0.8,
                context_match=0.8,
                observed_at=NOW,
            )
        ]


def _seed_risk_domain(repository: InMemoryRiskRepository) -> None:
    """Grava o par previsto/observado que o domínio Risk passa a possuir."""
    repository.add_analysis(
        RiskAnalysisRecord(
            analysis_id=ANALYSIS_ID,
            project_id=PROJECT,
            request_id="request-hist-001",
            analysis_policy_version=RISK_POLICY,
            severity="HIGH",
            confidence=0.8,
            uncertainty=0.2,
            dimensions=(
                PersistedRiskDimension(dimension="scope_risk", score=0.7, severity="HIGH"),
            ),
            reason_codes=("SECRETS_OR_ENV",),
            blast_radius_level="HIGH",
            fingerprint=fingerprint_of({"analysis_id": ANALYSIS_ID}),
            created_at=NOW,
        )
    )
    repository.add_outcome(
        RiskOutcomeRecord(
            outcome_id=OUTCOME_ID,
            project_id=PROJECT,
            risk_analysis_id=ANALYSIS_ID,
            contract_id="contract-hist-001",
            evidence_id="evidence-hist-001",
            outcome_policy_version="post-execution-v1",
            effective_gate="PASS",
            status="passed",
            contract_valid=True,
            fingerprint=fingerprint_of({"outcome_id": OUTCOME_ID}),
            created_at=NOW,
        )
    )


# ---------------------------------------------------------------------------
# Teste A — o serviço histórico usa o Risk Repository
# ---------------------------------------------------------------------------


def test_historical_service_resolves_policy_from_the_risk_domain(monkeypatch):
    """O teste que realmente fecha P1.

    Report Memory desligada, persistência de risco ligada. A política é
    resolvida — e é resolvida PELO domínio Risk, não por acidente.
    """
    monkeypatch.setenv("PEDROCORE_REPORT_MEMORY_PERSISTENCE", "off")
    monkeypatch.setenv(FLAG_RISK_PERSISTENCE, "memory")
    repository = InMemoryRiskRepository()
    _seed_risk_domain(repository)
    risk_persistence_service.set_repository(repository)

    policies, sources = historical_risk_service._resolve_risk_policies(
        PROJECT, _Memory()
    )

    assert policies == [RISK_POLICY]
    assert sources[OUTCOME_ID] == POLICY_SOURCE_RISK_DOMAIN


def test_report_memory_is_not_consulted_when_the_risk_domain_answers(monkeypatch):
    """Não basta responder: tem que responder SEM depender do legado.

    Se Report Memory fosse consultada mesmo com o registro próprio presente, a
    dependência continuaria de pé, apenas escondida atrás de um resultado certo.
    """
    monkeypatch.setenv("PEDROCORE_REPORT_MEMORY_PERSISTENCE", "off")
    monkeypatch.setenv(FLAG_RISK_PERSISTENCE, "memory")
    repository = InMemoryRiskRepository()
    _seed_risk_domain(repository)
    risk_persistence_service.set_repository(repository)

    calls: list[str] = []

    def _forbidden(project_id, source_id):
        calls.append(source_id)
        raise AssertionError("Report Memory não deveria ser consultada")

    monkeypatch.setattr(
        HistoricalRiskService, "_policy_from_report_memory", staticmethod(_forbidden)
    )

    policies, _ = historical_risk_service._resolve_risk_policies(PROJECT, _Memory())
    assert policies == [RISK_POLICY]
    assert calls == []


# ---------------------------------------------------------------------------
# Teste C — compatibilidade V1
# ---------------------------------------------------------------------------


def test_with_risk_persistence_off_the_v1_path_is_untouched(monkeypatch):
    """Persistência desligada = comportamento idêntico ao anterior à Stage."""
    monkeypatch.setenv(FLAG_RISK_PERSISTENCE, "off")
    seen: list[str] = []

    def _legacy(project_id, source_id):
        seen.append(source_id)
        return RISK_POLICY

    monkeypatch.setattr(
        HistoricalRiskService, "_policy_from_report_memory", staticmethod(_legacy)
    )

    policies, sources = historical_risk_service._resolve_risk_policies(
        PROJECT, _Memory()
    )
    assert policies == [RISK_POLICY]
    assert seen == [OUTCOME_ID]
    assert sources[OUTCOME_ID] == POLICY_SOURCE_LEGACY_REPORT


# ---------------------------------------------------------------------------
# Teste D — dado legado
# ---------------------------------------------------------------------------


def test_legacy_records_still_resolve_through_report_memory(monkeypatch):
    """Registro anterior ao R2 não existe no store próprio.

    Apagar o caminho legado da leitura seria perder história real — registros
    gravados antes de a persistência existir continuam sendo fatos.
    """
    monkeypatch.setenv(FLAG_RISK_PERSISTENCE, "memory")
    # Store proprio vazio: simula exatamente o registro anterior a Stage.
    risk_persistence_service.set_repository(InMemoryRiskRepository())
    monkeypatch.setattr(
        HistoricalRiskService,
        "_policy_from_report_memory",
        staticmethod(lambda project_id, source_id: "legacy-risk-policy-v0"),
    )

    policies, sources = historical_risk_service._resolve_risk_policies(
        PROJECT, _Memory()
    )
    assert policies == ["legacy-risk-policy-v0"]
    assert sources[OUTCOME_ID] == POLICY_SOURCE_LEGACY_REPORT


def test_nothing_is_invented_when_neither_source_knows(monkeypatch):
    """Sem registro próprio e sem relatório, a resposta é vazia — não inventada."""
    monkeypatch.setenv(FLAG_RISK_PERSISTENCE, "memory")
    risk_persistence_service.set_repository(InMemoryRiskRepository())
    monkeypatch.setattr(
        HistoricalRiskService,
        "_policy_from_report_memory",
        staticmethod(lambda project_id, source_id: None),
    )

    policies, sources = historical_risk_service._resolve_risk_policies(
        PROJECT, _Memory()
    )
    assert policies == []
    assert sources == {}


# ---------------------------------------------------------------------------
# Teste E — fail-closed
# ---------------------------------------------------------------------------


def test_a_configured_but_unreachable_repository_fails_closed(monkeypatch):
    """Store configurado e indisponível não vira "sem histórico".

    Devolver `sample_size = 0` faria a consulta parecer segura quando ela
    apenas não conseguiu ler — e é sobre esse número que uma decisão de risco
    se apoia.
    """
    monkeypatch.setenv(FLAG_RISK_PERSISTENCE, "postgresql")
    monkeypatch.setenv(
        FLAG_RISK_DATABASE_URL,
        "postgresql://invalid:invalid@127.0.0.1:1/none?connect_timeout=1",
    )
    risk_persistence_service.set_repository(None)

    with pytest.raises(RiskRepositoryError):
        historical_risk_service._resolve_risk_policies(PROJECT, _Memory())


def test_the_failure_never_leaks_database_internals(monkeypatch):
    """A mensagem diz que falhou, não onde nem como."""
    monkeypatch.setenv(FLAG_RISK_PERSISTENCE, "postgresql")
    monkeypatch.setenv(
        FLAG_RISK_DATABASE_URL,
        "postgresql://segredo:senha-secreta@db.interno.local:5432/risk",
    )
    risk_persistence_service.set_repository(None)

    with pytest.raises(RiskRepositoryError) as error:
        historical_risk_service._resolve_risk_policies(PROJECT, _Memory())

    rendered = str(error.value)
    for leak in ("senha-secreta", "db.interno.local", "segredo", "5432", "SELECT"):
        assert leak not in rendered


# ---------------------------------------------------------------------------
# Teste B — o endpoint público
# ---------------------------------------------------------------------------


def test_the_endpoint_returns_a_sanitized_operational_error(monkeypatch):
    """A falha do store chega à API como erro operacional, não como 500.

    Sem isto, internals do psycopg — connection string incluída — apareceriam
    no corpo da resposta.
    """
    from fastapi.testclient import TestClient

    from app.main import app
    from app.modules.contracts import codes

    monkeypatch.setattr(
        historical_risk_service,
        "summarize",
        lambda payload: (_ for _ in ()).throw(
            RiskRepositoryError("postgresql://user:senha@host/db indisponível")
        ),
    )

    with TestClient(app) as client:
        response = client.post(
            "/api/risk/history/query",
            json={
                "producer": "alpha-technical-tool",
                "project_id": PROJECT,
                "task_types": [],
                "pattern_types": [],
                "lifecycles": [],
            },
        )

    # A rota exige autorizacao; o que se prova aqui e que NENHUM caminho
    # devolve internals do banco, seja qual for o status.
    body = response.text
    for leak in ("senha", "psycopg", "Traceback", "postgresql://"):
        assert leak not in body
    if response.status_code == 503:
        assert codes.RISK_HISTORY_PERSISTENCE_UNAVAILABLE in body


def test_the_new_error_code_is_distinct_from_operational_memory():
    """Dois stores diferentes, dois códigos.

    Colapsá-los esconderia qual deles caiu — e a ação de quem opera é
    diferente em cada caso.
    """
    from app.modules.contracts import codes

    assert (
        codes.RISK_HISTORY_PERSISTENCE_UNAVAILABLE
        != codes.OPERATIONAL_MEMORY_PERSISTENCE_UNAVAILABLE
    )
