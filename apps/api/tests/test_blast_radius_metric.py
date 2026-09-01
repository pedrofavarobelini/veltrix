"""Risk Engine V2 — Stage R3: métrica de alcance do blast radius (P3).

O problema
----------

`BlastRadius` descrevia alcance qualitativamente. Sem número comparável, duas
análises não podiam ser ordenadas, e o histórico não conseguia aprender "isto
atingiu mais do que aquilo".

O que estes testes fixam
------------------------

As propriedades que tornam a métrica utilizável: determinismo, invariância a
ordem e a duplicata, monotonicidade, e — a mais importante — **independência
da severidade**. Alcance e perigo são perguntas diferentes, e um número que
misturasse as duas não responderia nenhuma.
"""

from __future__ import annotations

import pytest

from app.modules.risk_engine.blast_radius_metric import (
    BLAST_RADIUS_METRIC_VERSION,
    BOUNDARY_FIELDS,
    BlastRadiusMetric,
    compute_blast_radius_metric,
)
from app.modules.risk_engine.pre_execution_schemas import BlastRadius
from app.modules.risk_engine.schemas import RiskSeverity


def _radius(**overrides) -> BlastRadius:
    values = {
        "files": ["file:a.py", "file:b.py"],
        "modules": ["module:billing"],
        "database": [],
        "users": [],
        "permissions": ["write:billing"],
        "environments": ["development"],
        "external_integrations": [],
        "security_boundaries": [],
        "magnitude": RiskSeverity.MEDIUM,
    }
    values.update(overrides)
    return BlastRadius(**values)


# ---------------------------------------------------------------------------
# Cálculo e explicabilidade
# ---------------------------------------------------------------------------


def test_metric_counts_boundaries_and_items():
    metric = compute_blast_radius_metric(_radius())
    # files(2) + modules(1) + permissions(1) + environments(1)
    assert metric.boundary_breadth == 4
    assert metric.item_extent == 5
    assert metric.boundary_counts == {
        "files": 2,
        "modules": 1,
        "permissions": 1,
        "environments": 1,
    }
    assert metric.metric_version == BLAST_RADIUS_METRIC_VERSION


def test_the_number_is_explainable_item_by_item():
    """Sem a conta aberta, a métrica seria uma opinião com aparência de dado."""
    metric = compute_blast_radius_metric(_radius())
    assert sum(metric.boundary_counts.values()) == metric.item_extent
    assert len(metric.boundary_counts) == metric.boundary_breadth


def test_an_empty_radius_has_zero_extent():
    metric = compute_blast_radius_metric(
        _radius(files=[], modules=[], permissions=[], environments=[])
    )
    assert metric.boundary_breadth == 0
    assert metric.item_extent == 0
    assert metric.boundary_counts == {}


# ---------------------------------------------------------------------------
# Propriedades
# ---------------------------------------------------------------------------


def test_metric_is_deterministic():
    first = compute_blast_radius_metric(_radius())
    second = compute_blast_radius_metric(_radius())
    assert first == second


def test_metric_is_order_invariant():
    """A ordem em que os alvos aparecem não é informação."""
    ordered = compute_blast_radius_metric(_radius(files=["file:a.py", "file:b.py"]))
    reversed_ = compute_blast_radius_metric(_radius(files=["file:b.py", "file:a.py"]))
    assert ordered == reversed_


def test_metric_is_duplicate_invariant():
    """O mesmo alvo listado duas vezes é um alvo."""
    once = compute_blast_radius_metric(_radius(files=["file:a.py"]))
    twice = compute_blast_radius_metric(_radius(files=["file:a.py", "file:a.py"]))
    assert once == twice


def test_metric_is_monotonic_in_items():
    """Acrescentar alvo nunca diminui o alcance."""
    smaller = compute_blast_radius_metric(_radius(files=["file:a.py"]))
    larger = compute_blast_radius_metric(_radius(files=["file:a.py", "file:b.py"]))
    assert larger.item_extent > smaller.item_extent
    assert larger.boundary_breadth == smaller.boundary_breadth


def test_metric_is_monotonic_in_boundaries():
    """Tocar uma fronteira nova aumenta a amplitude."""
    before = compute_blast_radius_metric(_radius(database=[]))
    after = compute_blast_radius_metric(_radius(database=["db:billing"]))
    assert after.boundary_breadth == before.boundary_breadth + 1
    assert after.item_extent == before.item_extent + 1


def test_breadth_never_exceeds_the_number_of_boundaries():
    everything = {field: [f"{field}:item"] for field in BOUNDARY_FIELDS}
    metric = compute_blast_radius_metric(_radius(**everything))
    assert metric.boundary_breadth == len(BOUNDARY_FIELDS)


# ---------------------------------------------------------------------------
# Separação: alcance ≠ severidade
# ---------------------------------------------------------------------------


def test_metric_is_independent_from_severity():
    """Alterar 40 arquivos de teste tem alcance maior e perigo menor.

    Um número que misturasse as duas coisas não responderia nenhuma das duas
    perguntas.
    """
    low = compute_blast_radius_metric(_radius(magnitude=RiskSeverity.INFO))
    high = compute_blast_radius_metric(_radius(magnitude=RiskSeverity.CRITICAL))
    assert low == high


def test_magnitude_is_preserved_alongside_the_metric():
    """A métrica é aditiva: `magnitude` continua existindo e valendo."""
    radius = _radius(magnitude=RiskSeverity.HIGH)
    assert radius.magnitude is RiskSeverity.HIGH
    assert compute_blast_radius_metric(radius).item_extent == 5


def test_the_metric_carries_no_risk_score_field():
    """Não é um score global de risco, e não tem onde virar um."""
    forbidden = {"risk_score", "score", "severity", "gate", "magnitude"}
    assert not (set(BlastRadiusMetric.model_fields) & forbidden)


# ---------------------------------------------------------------------------
# Consistência interna
# ---------------------------------------------------------------------------


def test_totals_that_do_not_match_the_counts_are_refused():
    """Um agregado que não decorre do detalhe é impossível de conferir."""
    with pytest.raises(ValueError, match="item_extent"):
        BlastRadiusMetric(
            boundary_breadth=1, item_extent=99, boundary_counts={"files": 2}
        )


def test_breadth_that_does_not_match_the_counts_is_refused():
    with pytest.raises(ValueError, match="boundary_breadth"):
        BlastRadiusMetric(
            boundary_breadth=5, item_extent=2, boundary_counts={"files": 2}
        )


def test_unknown_boundaries_are_refused():
    with pytest.raises(ValueError, match="desconhecidas"):
        BlastRadiusMetric(
            boundary_breadth=1, item_extent=1, boundary_counts={"telepatia": 1}
        )


# ---------------------------------------------------------------------------
# Integração com a análise e com a persistência
# ---------------------------------------------------------------------------


def test_the_analysis_carries_the_metric(monkeypatch):
    """O motor passa a produzir a métrica junto com o raio."""
    from app.modules.retrieval.schemas import RetrievalResponse
    from app.modules.retrieval.service import retrieval_service
    from app.modules.risk_engine.pre_execution_service import pre_execution_risk_service
    from app.modules.risk_engine.schemas import RiskRequest

    monkeypatch.setattr(
        retrieval_service,
        "retrieve",
        lambda query, **_: RetrievalResponse(
            query_id=query.query_id, project_id=query.project_id
        ),
    )
    analysis = pre_execution_risk_service.analyze(
        RiskRequest.model_validate(
            {
                "request_id": "metric-001",
                "producer": "alpha-technical-tool",
                "project_id": "alpha",
                "request_text": "Edit the billing module within scope.",
                "environment": "development",
                "agent_id": "codex-local",
                "permissions": ["write:billing"],
                "context": {"allowed_scope": ["module:billing"]},
                "requested_operation": {
                    "kind": "WRITE",
                    "targets": ["module:billing", "file:billing/service.py"],
                    "expected_changes": ["bounded edit"],
                },
            }
        )
    )
    metric = analysis.blast_radius.metric
    assert metric is not None
    assert metric.metric_version == BLAST_RADIUS_METRIC_VERSION
    assert metric.item_extent >= 2
    # Severidade continua sendo campo proprio, nao derivada da metrica.
    assert analysis.blast_radius.magnitude is not None


def test_legacy_records_keep_a_null_metric_without_conflict():
    """Registro anterior ao R3 não tem métrica — e isso não vira conflito.

    A métrica ficou de fora do fingerprint de propósito: ela é derivada de
    dados já presentes na análise, então não acrescenta identidade. Incluí-la
    faria a mesma análise, reprojetada após o R3, colidir com o registro
    gravado antes dele.
    """
    from datetime import datetime, timezone

    from app.modules.risk_engine.persistence_schemas import RiskAnalysisRecord
    from app.modules.risk_engine.repository import (
        InMemoryRiskRepository,
        fingerprint_of,
    )

    moment = datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc)
    shared_fingerprint = fingerprint_of({"analysis_id": "a1"})

    legacy = RiskAnalysisRecord(
        analysis_id="a1",
        project_id="alpha",
        request_id="r1",
        analysis_policy_version="pre-execution-risk-v1",
        severity="HIGH",
        confidence=0.8,
        uncertainty=0.2,
        fingerprint=shared_fingerprint,
        created_at=moment,
    )
    assert legacy.blast_metric_version is None

    upgraded = legacy.model_copy(
        update={
            "blast_metric_version": BLAST_RADIUS_METRIC_VERSION,
            "blast_boundary_breadth": 2,
            "blast_item_extent": 3,
            "blast_boundary_counts": {"files": 2, "modules": 1},
        }
    )

    repository = InMemoryRiskRepository()
    assert repository.add_analysis(legacy) is True
    # Mesmo fingerprint: reprojetar apos o R3 e replay, nao conflito.
    assert repository.add_analysis(upgraded) is False


def test_a_partially_filled_metric_is_refused():
    """Amplitude sem extensão descreveria fronteiras tocadas e vazias."""
    from datetime import datetime, timezone

    from app.modules.risk_engine.persistence_schemas import RiskAnalysisRecord
    from app.modules.risk_engine.repository import fingerprint_of

    with pytest.raises(ValueError, match="incompleta"):
        RiskAnalysisRecord(
            analysis_id="a1",
            project_id="alpha",
            request_id="r1",
            analysis_policy_version="pre-execution-risk-v1",
            severity="HIGH",
            confidence=0.8,
            uncertainty=0.2,
            blast_boundary_breadth=2,
            fingerprint=fingerprint_of({"analysis_id": "a1"}),
            created_at=datetime(2026, 9, 1, tzinfo=timezone.utc),
        )
