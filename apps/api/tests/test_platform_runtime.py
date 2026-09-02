"""E4, E6 e E7 — Evaluation Plane V2, Shadow Mode e Routing explicavel.

Reunidos porque formam um circuito: o routing escolhe, o shadow observa o
candidato que nao foi escolhido, e a avaliacao registra a evidencia que o
Model Registry vai exigir para promover.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.modules.evaluation_plane.schemas import (
    EvaluationMetric,
    EvaluationRecord,
    EvaluationStatus,
    EvaluationSubject,
    EvaluationSubjectKind,
)
from app.modules.evaluation_plane.service import evaluation_plane_service
from app.modules.routing_intelligence.service import (
    EliminationReason,
    RoutingCandidate,
    RoutingDecision,
    RoutingSignals,
    RoutingStrategy,
    routing_intelligence_service,
)
from app.modules.shadow_execution.service import (
    ShadowCandidate,
    ShadowOutcome,
    ShadowExecutionService,
)

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)
PROJECT = "pedrocore"


@pytest.fixture(autouse=True)
def limpa():
    evaluation_plane_service.reset()
    yield
    evaluation_plane_service.reset()


# ===========================================================================
# E4 — Evaluation Plane V2
# ===========================================================================


def _subject(**kw) -> EvaluationSubject:
    return EvaluationSubject(
        kind=kw.pop("kind", EvaluationSubjectKind.MODEL),
        subject_id=kw.pop("subject_id", "anthropic:claude-sonnet:5"),
        subject_version=kw.pop("subject_version", "5"),
    )


def _metric(name="acuracia", value=0.91, sample_size=120) -> EvaluationMetric:
    return EvaluationMetric(
        name=name, value=value, unit="ratio", sample_size=sample_size
    )


def _record(**kw):
    return evaluation_plane_service.record(
        subject=kw.pop("subject", _subject()),
        suite=kw.pop("suite", "qa-regressao"),
        suite_version=kw.pop("suite_version", "1.0"),
        environment=kw.pop("environment", "test"),
        project_id=PROJECT,
        producer="pedrocore-ci",
        now=NOW,
        **kw,
    )


def test_without_a_dataset_the_evaluation_reports_dataset_not_ready():
    """DATASET_NOT_READY continua sendo a resposta correta."""
    registro = _record()
    assert registro.status is EvaluationStatus.DATASET_NOT_READY
    assert registro.metrics == ()
    assert "DATASET_NOT_READY" in registro.reason_codes


def test_metrics_sent_without_a_dataset_are_discarded_not_stored():
    """Aceitar número sobre dataset inexistente é fabricar evidência."""
    registro = _record(metrics=(_metric(),))
    assert registro.status is EvaluationStatus.DATASET_NOT_READY
    assert registro.metrics == ()


def test_a_completed_evaluation_needs_a_dataset_and_metrics():
    registro = _record(dataset_id="ds-001", metrics=(_metric(),))
    assert registro.status is EvaluationStatus.COMPLETED
    assert registro.usable_as_promotion_evidence is True


def test_the_schema_refuses_metrics_alongside_dataset_not_ready():
    """A guarda vive no schema: um dump reconstruído também passa por ela."""
    with pytest.raises(Exception) as erro:
        EvaluationRecord(
            evaluation_id="eval_" + "a" * 12,
            subject=_subject(),
            suite="s",
            suite_version="1",
            environment="test",
            project_id=PROJECT,
            producer="ci",
            status=EvaluationStatus.DATASET_NOT_READY,
            metrics=(_metric(),),
            evaluated_at=NOW,
        )
    assert "não se mede o que não existe" in str(erro.value)


def test_a_completed_evaluation_without_metrics_is_refused():
    with pytest.raises(Exception):
        EvaluationRecord(
            evaluation_id="eval_" + "a" * 12,
            subject=_subject(),
            suite="s",
            suite_version="1",
            environment="test",
            project_id=PROJECT,
            producer="ci",
            status=EvaluationStatus.COMPLETED,
            evaluated_at=NOW,
        )


def test_the_evaluation_plane_never_promotes_anything():
    """Quem mede não pode ser quem aprova."""
    registro = _record(dataset_id="ds-001", metrics=(_metric(),))
    assert registro.promotes_subject is False
    assert not hasattr(evaluation_plane_service, "promote")


def test_only_completed_evaluations_count_as_promotion_evidence():
    _record()
    _record(dataset_id="ds-001", metrics=(_metric(),))
    evidencias = evaluation_plane_service.promotion_evidence(
        PROJECT, "anthropic:claude-sonnet:5"
    )
    assert len(evidencias) == 1


def test_a_metric_carries_its_sample_size():
    """Média sobre três casos e sobre trezentos não valem o mesmo."""
    registro = _record(dataset_id="ds-001", metrics=(_metric(sample_size=3),))
    assert registro.metrics[0].sample_size == 3


def test_evaluations_are_isolated_by_project():
    _record(dataset_id="ds-001", metrics=(_metric(),))
    assert evaluation_plane_service.for_subject("structa", "anthropic:claude-sonnet:5") == []


def test_every_subject_kind_can_be_evaluated():
    for kind in EvaluationSubjectKind:
        registro = _record(subject=_subject(kind=kind, subject_id=f"s-{kind.value}"))
        assert registro.subject.kind is kind


# ===========================================================================
# E6 — Shadow Mode
# ===========================================================================


def _fingerprint(value) -> str:
    return f"fp:{value}"


def _observe(service, candidate, *, primary_output="oficial", primary_input="entrada"):
    return service.observe(
        candidate=candidate,
        primary_input=primary_input,
        primary_output=primary_output,
        project_id=PROJECT,
        environment="development",
        correlation_id="corr-shadow-000001",
        fingerprint=_fingerprint,
        now=NOW,
    )


def test_a_matching_shadow_is_recorded_as_matched():
    service = ShadowExecutionService()
    candidato = ShadowCandidate("cand-1", run=lambda entrada, ctx: "oficial")
    resultado = _observe(service, candidato)
    assert resultado.outcome is ShadowOutcome.MATCHED


def test_a_diverging_shadow_is_recorded_not_returned_to_the_user():
    service = ShadowExecutionService()
    candidato = ShadowCandidate("cand-1", run=lambda entrada, ctx: "diferente")
    resultado = _observe(service, candidato)
    assert resultado.outcome is ShadowOutcome.DIVERGED
    assert resultado.affected_user_response is False


def test_the_shadow_receives_a_context_that_forbids_side_effects():
    """A proibição viaja como dado, não como convenção."""
    service = ShadowExecutionService()
    visto = {}

    def candidato_run(entrada, ctx):
        visto["side_effects"] = ctx.side_effects_allowed
        visto["persistence"] = ctx.persistence_allowed
        visto["responds"] = ctx.responds_to_user
        return "x"

    _observe(service, ShadowCandidate("cand-1", run=candidato_run))
    assert visto == {"side_effects": False, "persistence": False, "responds": False}


def test_a_candidate_that_declares_side_effects_is_refused_before_running():
    """A recusa é barata; o efeito não."""
    service = ShadowExecutionService()
    rodou = []
    candidato = ShadowCandidate(
        "cand-perigoso",
        run=lambda entrada, ctx: rodou.append(1),
        declares_side_effects=True,
    )
    resultado = _observe(service, candidato)
    assert resultado.outcome is ShadowOutcome.REFUSED
    assert rodou == [], "candidato com efeito externo não pode ter rodado"


def test_the_shadow_runs_on_the_primary_input_not_on_its_output():
    """Encadear faria o shadow herdar o efeito do primário."""
    service = ShadowExecutionService()
    recebido = {}

    def candidato_run(entrada, ctx):
        recebido["entrada"] = entrada
        return entrada

    _observe(
        service,
        ShadowCandidate("cand-1", run=candidato_run),
        primary_input="a entrada original",
        primary_output="a saída do primário",
    )
    assert recebido["entrada"] == "a entrada original"


def test_a_failing_shadow_never_breaks_the_primary_path():
    service = ShadowExecutionService()

    def explode(entrada, ctx):
        raise RuntimeError("segredo-que-nao-pode-vazar")

    resultado = _observe(service, ShadowCandidate("cand-1", run=explode))
    assert resultado.outcome is ShadowOutcome.FAILED
    assert "segredo-que-nao-pode-vazar" not in str(resultado.reason_codes)
    assert "RUNTIMEERROR" in resultado.reason_codes[0]


def test_a_shadow_over_budget_is_marked_and_does_not_affect_the_primary():
    import time as _time

    service = ShadowExecutionService()

    def lento(entrada, ctx):
        _time.sleep(0.05)
        return "oficial"

    candidato = ShadowCandidate("cand-lento", run=lento, budget_seconds=0.001)
    resultado = _observe(service, candidato)
    assert resultado.outcome is ShadowOutcome.BUDGET_EXCEEDED


def test_the_shadow_can_be_switched_off():
    service = ShadowExecutionService()
    service.disable()
    rodou = []
    resultado = _observe(
        service, ShadowCandidate("cand-1", run=lambda e, c: rodou.append(1))
    )
    assert resultado.outcome is ShadowOutcome.SKIPPED
    assert rodou == []


def test_no_comparison_ever_claims_a_side_effect():
    service = ShadowExecutionService()
    _observe(service, ShadowCandidate("cand-1", run=lambda e, c: "oficial"))
    for item in service.comparisons():
        assert item.produced_side_effects is False
        assert item.affected_user_response is False


def test_divergence_rate_is_none_without_completed_observations():
    """None é diferente de zero: zero significaria 'nunca divergiu'."""
    service = ShadowExecutionService()
    assert service.divergence_rate("cand-inexistente") is None


def test_divergence_rate_counts_only_completed_observations():
    service = ShadowExecutionService()
    _observe(service, ShadowCandidate("c", run=lambda e, ctx: "oficial"))
    _observe(service, ShadowCandidate("c", run=lambda e, ctx: "outro"))
    assert service.divergence_rate("c") == 0.5


def test_comparisons_are_scoped_by_project():
    service = ShadowExecutionService()
    _observe(service, ShadowCandidate("c", run=lambda e, ctx: "oficial"))
    assert service.comparisons(PROJECT)
    assert service.comparisons("structa") == []


# ===========================================================================
# E7 — Routing por qualidade, custo e latencia
# ===========================================================================


def _candidate(cid="c1", quality=0.9, cost=0.2, latency=0.2, sample=100, **flags):
    return RoutingCandidate(
        candidate_id=cid,
        provider=flags.pop("provider", "anthropic"),
        model=flags.pop("model", "claude-sonnet-5"),
        signals=RoutingSignals(
            quality=quality, cost=cost, latency=latency, sample_size=sample
        ),
        **flags,
    )


def test_every_strategy_declares_weights_that_sum_to_one():
    """Pesos que não somassem 1 tornariam as notas incomparáveis."""
    for estrategia in RoutingStrategy:
        decisao = routing_intelligence_service.decide([_candidate()], estrategia)
        assert round(sum(decisao.weights.values()), 6) == 1.0


def test_cost_and_latency_are_inverted_because_lower_is_better():
    caro = _candidate("caro", quality=0.9, cost=0.9, latency=0.1)
    barato = _candidate("barato", quality=0.9, cost=0.1, latency=0.1)
    decisao = routing_intelligence_service.decide(
        [caro, barato], RoutingStrategy.COST_AWARE
    )
    assert decisao.selected_candidate_id == "barato"


def test_quality_first_and_cost_aware_can_disagree():
    """Se toda estratégia escolhesse igual, a estratégia seria decoração."""
    bom_e_caro = _candidate("bom-caro", quality=0.95, cost=0.9, latency=0.3)
    ok_e_barato = _candidate("ok-barato", quality=0.6, cost=0.05, latency=0.3)
    qualidade = routing_intelligence_service.decide(
        [bom_e_caro, ok_e_barato], RoutingStrategy.QUALITY_FIRST
    )
    custo = routing_intelligence_service.decide(
        [bom_e_caro, ok_e_barato], RoutingStrategy.COST_AWARE
    )
    assert qualidade.selected_candidate_id == "bom-caro"
    assert custo.selected_candidate_id == "ok-barato"


@pytest.mark.parametrize(
    "flag,motivo",
    [
        ("policy_allowed", EliminationReason.POLICY_DENIED),
        ("capability_satisfied", EliminationReason.CAPABILITY_MISSING),
        ("homologated", EliminationReason.NOT_HOMOLOGATED),
        ("circuit_closed", EliminationReason.CIRCUIT_OPEN),
        ("available", EliminationReason.UNAVAILABLE),
    ],
)
def test_a_closed_door_eliminates_before_any_ranking(flag, motivo):
    """Nota alta não compra permissão."""
    excelente = _candidate("otimo", quality=1.0, cost=0.0, latency=0.0, **{flag: False})
    mediocre = _candidate("mediano", quality=0.4, cost=0.5, latency=0.5)
    decisao = routing_intelligence_service.decide([excelente, mediocre])

    assert decisao.selected_candidate_id == "mediano"
    assert any(
        item.candidate_id == "otimo" and item.reason is motivo
        for item in decisao.eliminated
    )
    assert all(item.candidate_id != "otimo" for item in decisao.ranked)


def test_routing_never_selects_outside_the_ranking():
    """Seleção fora da eliminação seria bypass de política."""
    with pytest.raises(Exception) as erro:
        RoutingDecision(
            strategy=RoutingStrategy.BALANCED,
            selected_candidate_id="fantasma",
            selected_provider="p",
            selected_model="m",
        )
    assert "bypass" in str(erro.value)


def test_no_surviving_candidate_yields_no_selection():
    decisao = routing_intelligence_service.decide(
        [_candidate("bloqueado", policy_allowed=False)]
    )
    assert decisao.selected_candidate_id is None
    assert decisao.reason_codes == ["NO_CANDIDATE_SURVIVED"]


def test_the_decision_shows_the_contribution_of_each_signal():
    decisao = routing_intelligence_service.decide([_candidate()])
    escolhido = decisao.ranked[0]
    assert set(escolhido.contributions) == {"quality", "cost", "latency"}
    assert round(sum(escolhido.contributions.values()), 6) == escolhido.score


def test_a_candidate_without_measurement_is_flagged_when_selected():
    """Escolher sem medição é legítimo; escondê-lo não seria."""
    decisao = routing_intelligence_service.decide([_candidate(sample=0)])
    assert "SELECTED_WITHOUT_MEASUREMENT" in decisao.reason_codes
    assert decisao.ranked[0].measured is False


def test_routing_declares_it_did_not_bypass_policy():
    decisao = routing_intelligence_service.decide([_candidate()])
    assert decisao.bypassed_policy is False


def test_the_ranking_is_stable_for_tied_scores():
    """Empate resolvido por id: decisão de roteamento não pode ser sorteio."""
    a = _candidate("aaa", quality=0.5, cost=0.5, latency=0.5)
    b = _candidate("bbb", quality=0.5, cost=0.5, latency=0.5)
    primeira = routing_intelligence_service.decide([a, b])
    segunda = routing_intelligence_service.decide([b, a])
    assert primeira.selected_candidate_id == segunda.selected_candidate_id
