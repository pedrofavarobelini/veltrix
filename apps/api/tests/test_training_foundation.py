"""Evaluation & Training Foundation (Era 8).

O GATE 8 pede interfaces, politicas, validacao, transicoes de estado e rollback
testados — **sem executar treinamento real**. Nenhum backend real e chamado
aqui: o unico backend e um duble que declara disponibilidade e nunca computa.

Um LoRA de brinquedo "so para provar que funciona" teria comprado o Gate com
exatamente o que ele existe para impedir: um modelo produzido a partir de
populacao que a governanca recusou.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.modules.caller_identity.schemas import (
    AuthenticatedCallerContext,
    CallerRole,
    IdentityStrength,
)
from app.modules.training_data.acquisition import training_candidate_service
from app.modules.training_foundation.schemas import (
    BaselineComparison,
    EvaluationMetric,
    EvaluationRun,
    EvaluationRunStatus,
    MetricValue,
    ModelRegistryEntry,
    ModelStage,
    PromotionDecision,
    PromotionPolicy,
    RollbackPolicy,
    TrainingBackend,
    TrainingRun,
    TrainingRunStatus,
)
from app.modules.training_foundation.service import (
    TrainingFoundationError,
    training_foundation_service,
)

NOW = datetime(2026, 8, 29, 12, 0, 0, tzinfo=timezone.utc)
ADMIN = "alpha-admin"
PROJECT = "alpha"
FINGERPRINT = "sha256:" + "a" * 64


@pytest.fixture(autouse=True)
def isolated(monkeypatch):
    monkeypatch.setenv("PEDROCORE_TRAINING_DATA_ADMIN_IDS", ADMIN)
    monkeypatch.setenv("PEDROCORE_REPORT_MEMORY_PERSISTENCE", "memory")
    training_foundation_service.reset()
    yield
    training_foundation_service.reset()


def _admin() -> AuthenticatedCallerContext:
    return AuthenticatedCallerContext(
        credential_id=ADMIN,
        caller_role=CallerRole.TECHNICAL_TOOL,
        environment="test",
        identity_strength=IdentityStrength.REGISTERED,
        authenticated=True,
        project_id=PROJECT,
        allowed_origins=(PROJECT,),
    )


class _StubBackend:
    """Duble de backend. Declara disponibilidade e NUNCA computa nada."""

    backend_id = "stub-backend"

    def __init__(self, available: bool = True) -> None:
        self._available = available
        self.started: list[str] = []

    def available(self) -> bool:
        return self._available

    def estimate(self, run: TrainingRun) -> dict:
        return {"estimated_seconds": 0, "estimated_cost": 0.0, "run_id": run.run_id}

    def start(self, run: TrainingRun) -> str:
        self.started.append(run.run_id)
        return f"external-{run.run_id}"


def _evaluation(
    evaluation_id: str,
    *,
    accuracy: float,
    sample_size: int = 500,
    status: EvaluationRunStatus = EvaluationRunStatus.COMPLETED,
    extra: tuple[MetricValue, ...] = (),
    dataset_version: int = 1,
) -> EvaluationRun:
    metrics = (
        MetricValue(
            metric=EvaluationMetric.ACCURACY, value=accuracy, sample_size=sample_size
        ),
        *extra,
    )
    return EvaluationRun(
        evaluation_id=evaluation_id,
        dataset_id="ds-1",
        dataset_version=dataset_version,
        dataset_fingerprint=FINGERPRINT,
        model_ref=f"model-{evaluation_id}",
        status=status,
        metrics=metrics if status is EvaluationRunStatus.COMPLETED else (),
    )


def _register_baseline(accuracy: float = 0.80, **kwargs) -> EvaluationRun:
    baseline = training_foundation_service.evaluations.record(
        _evaluation("eval-baseline", accuracy=accuracy, **kwargs)
    )
    training_foundation_service.evaluations.set_baseline("ds-1", "eval-baseline")
    return baseline


def _model(model_ref: str = "model-candidate", **overrides) -> ModelRegistryEntry:
    base = {
        "model_ref": model_ref,
        "dataset_id": "ds-1",
        "dataset_version": 1,
        "registered_at": NOW,
    }
    base.update(overrides)
    return ModelRegistryEntry(**base)


# ---------------------------------------------------------------------------
# Metricas
# ---------------------------------------------------------------------------


def test_bounded_metrics_reject_impossible_values():
    with pytest.raises(ValueError, match="entre 0.0 e 1.0"):
        MetricValue(metric=EvaluationMetric.ACCURACY, value=1.4, sample_size=10)


def test_regression_count_is_lower_is_better():
    """Sem esta distincao, a comparacao promoveria quem mais regride."""
    lower = MetricValue(
        metric=EvaluationMetric.REGRESSION_COUNT, value=3, sample_size=10
    )
    higher = MetricValue(metric=EvaluationMetric.ACCURACY, value=0.9, sample_size=10)
    assert lower.higher_is_better is False
    assert higher.higher_is_better is True


def test_completed_evaluation_must_report_metrics():
    """Avaliacao concluida sem metrica nao avaliou nada."""
    with pytest.raises(ValueError, match="ao menos uma métrica"):
        EvaluationRun(
            evaluation_id="eval-x",
            dataset_id="ds-1",
            dataset_version=1,
            dataset_fingerprint=FINGERPRINT,
            model_ref="model-x",
            status=EvaluationRunStatus.COMPLETED,
        )


# ---------------------------------------------------------------------------
# Evaluation Registry e baseline
# ---------------------------------------------------------------------------


def test_baseline_must_be_a_completed_evaluation():
    """Baseline pendente compararia contra nada e aprovaria qualquer coisa."""
    training_foundation_service.evaluations.record(
        _evaluation("eval-pending", accuracy=0.9, status=EvaluationRunStatus.PENDING)
    )
    with pytest.raises(TrainingFoundationError) as error:
        training_foundation_service.evaluations.set_baseline("ds-1", "eval-pending")
    assert error.value.code == "BASELINE_MUST_BE_COMPLETED"


def test_evaluation_ids_are_unique():
    training_foundation_service.evaluations.record(_evaluation("eval-1", accuracy=0.8))
    with pytest.raises(TrainingFoundationError) as error:
        training_foundation_service.evaluations.record(
            _evaluation("eval-1", accuracy=0.9)
        )
    assert error.value.code == "EVALUATION_ALREADY_RECORDED"


# ---------------------------------------------------------------------------
# Comparacao com baseline
# ---------------------------------------------------------------------------


def test_promotion_is_rejected_without_a_baseline():
    """Sem baseline, "melhorou" nao tem contra o que."""
    candidate = _evaluation("eval-candidate", accuracy=0.99)
    comparison = training_foundation_service.compare_to_baseline(candidate)
    assert comparison.decision is PromotionDecision.REJECT
    assert "BASELINE_NOT_DEFINED" in comparison.reason_codes
    assert comparison.promoted is False


def test_marginal_improvement_is_rejected_as_noise():
    """"A metrica subiu" nao e motivo: 0,001 e ruido, nao progresso."""
    _register_baseline(0.80)
    candidate = _evaluation("eval-candidate", accuracy=0.801)
    comparison = training_foundation_service.compare_to_baseline(candidate)
    assert comparison.decision is PromotionDecision.REJECT
    assert "IMPROVEMENT_BELOW_THRESHOLD" in comparison.reason_codes


def test_large_improvement_on_a_tiny_sample_is_rejected():
    """Melhora grande em amostra minuscula tambem e ruido."""
    _register_baseline(0.50)
    candidate = _evaluation("eval-candidate", accuracy=0.95, sample_size=5)
    comparison = training_foundation_service.compare_to_baseline(candidate)
    assert comparison.decision is PromotionDecision.REJECT
    assert "SAMPLE_SIZE_TOO_SMALL" in comparison.reason_codes


def test_secondary_metric_regression_blocks_promotion():
    """Ganhar accuracy destruindo recall nao e melhoria."""
    _register_baseline(
        0.80,
        extra=(
            MetricValue(metric=EvaluationMetric.RECALL, value=0.90, sample_size=500),
        ),
    )
    candidate = _evaluation(
        "eval-candidate",
        accuracy=0.90,
        extra=(
            MetricValue(metric=EvaluationMetric.RECALL, value=0.40, sample_size=500),
        ),
    )
    comparison = training_foundation_service.compare_to_baseline(candidate)
    assert comparison.decision is PromotionDecision.REJECT
    assert "SECONDARY_METRIC_REGRESSION" in comparison.reason_codes


def test_baseline_from_a_different_dataset_version_is_rejected():
    """Versoes diferentes sao alvos diferentes; a diferenca seria do dataset."""
    _register_baseline(0.80)
    candidate = _evaluation("eval-candidate", accuracy=0.95, dataset_version=2)
    comparison = training_foundation_service.compare_to_baseline(candidate)
    assert comparison.decision is PromotionDecision.REJECT
    assert "BASELINE_DATASET_VERSION_MISMATCH" in comparison.reason_codes


def test_real_improvement_requires_human_review_by_default():
    _register_baseline(0.80)
    candidate = _evaluation("eval-candidate", accuracy=0.90)
    comparison = training_foundation_service.compare_to_baseline(candidate)
    assert comparison.decision is PromotionDecision.REQUIRES_REVIEW
    assert comparison.improvement == pytest.approx(0.10)
    assert comparison.reason_codes == []


def test_review_can_be_waived_only_by_explicit_policy():
    _register_baseline(0.80)
    candidate = _evaluation("eval-candidate", accuracy=0.90)
    comparison = training_foundation_service.compare_to_baseline(
        candidate, PromotionPolicy(requires_human_review=False)
    )
    assert comparison.decision is PromotionDecision.PROMOTE


# ---------------------------------------------------------------------------
# Training Run — pedir nao e executar
# ---------------------------------------------------------------------------


def _run(run_id="run-1", **overrides) -> TrainingRun:
    base = {
        "run_id": run_id,
        "dataset_id": "ds-1",
        "dataset_version": 1,
        "dataset_fingerprint": FINGERPRINT,
        "backend_id": "stub-backend",
        "base_model_ref": "base-model",
        "requested_by": ADMIN,
        "requested_at": NOW,
    }
    base.update(overrides)
    return TrainingRun(**base)


def test_training_request_is_blocked_without_a_materialized_dataset():
    """O caminho REAL do PedroCore hoje — e o resultado correto."""
    backend = _StubBackend()
    training_foundation_service.register_backend(backend)
    stored = training_foundation_service.request_training(_run(), _admin())
    assert stored.status is TrainingRunStatus.BLOCKED
    assert "DATASET_VERSION_NOT_MATERIALIZED" in stored.blocked_reason_codes
    assert stored.training_executed is False
    assert backend.started == []


def test_blocked_run_is_recorded_not_silently_dropped():
    """Pedido bloqueado registrado e auditavel; pedido que some nao e."""
    training_foundation_service.register_backend(_StubBackend())
    training_foundation_service.request_training(_run(), _admin())
    assert training_foundation_service.get_run("run-1") is not None


def test_unregistered_backend_blocks_the_run():
    stored = training_foundation_service.request_training(_run(), _admin())
    assert "TRAINING_BACKEND_NOT_REGISTERED" in stored.blocked_reason_codes


def test_unavailable_backend_blocks_the_run():
    training_foundation_service.register_backend(_StubBackend(available=False))
    stored = training_foundation_service.request_training(_run(), _admin())
    assert "TRAINING_BACKEND_UNAVAILABLE" in stored.blocked_reason_codes


def test_training_request_requires_admin():
    stranger = _admin().model_copy(update={"credential_id": "quem-sou-eu"})
    with pytest.raises(TrainingFoundationError) as error:
        training_foundation_service.request_training(_run(), stranger)
    assert error.value.code == "TRAINING_ADMIN_REQUIRED"


def test_blocked_run_must_declare_a_reason():
    with pytest.raises(ValueError, match="motivo"):
        _run(status=TrainingRunStatus.BLOCKED)


def test_stub_backend_satisfies_the_protocol():
    """O dominio conhece a interface e nada alem dela."""
    assert isinstance(_StubBackend(), TrainingBackend)


def test_no_provider_name_leaks_into_the_domain():
    """Trocar de backend nao pode virar refatoracao de dominio."""
    import inspect

    from app.modules.training_foundation import schemas, service

    for module in (schemas, service):
        source = inspect.getsource(module).lower()
        for provider in ("huggingface", "hugging face", "openai", "vertex", "sagemaker"):
            assert provider not in source.replace(
                "hugging face, nuvem", ""
            ), f"{provider} em {module.__name__}"


# ---------------------------------------------------------------------------
# Promocao e rollback
# ---------------------------------------------------------------------------


def _promotable() -> BaselineComparison:
    _register_baseline(0.80)
    return training_foundation_service.compare_to_baseline(
        _evaluation("eval-candidate", accuracy=0.90)
    )


def test_promotion_archives_the_previous_production_model():
    training_foundation_service.models.register(
        _model("model-v1", stage=ModelStage.PRODUCTION)
    )
    training_foundation_service.models.register(_model("model-v2"))
    promoted = training_foundation_service.promote(
        "model-v2", _promotable(), _admin(), human_approved=True
    )
    assert promoted.stage is ModelStage.PRODUCTION
    assert promoted.supersedes == "model-v1"
    assert training_foundation_service.models.get("model-v1").stage is ModelStage.ARCHIVED


def test_promotion_refuses_without_human_approval():
    training_foundation_service.models.register(_model("model-v2"))
    with pytest.raises(TrainingFoundationError) as error:
        training_foundation_service.promote("model-v2", _promotable(), _admin())
    assert error.value.code == "HUMAN_REVIEW_REQUIRED"


def test_promotion_refuses_a_rejected_comparison():
    _register_baseline(0.80)
    rejected = training_foundation_service.compare_to_baseline(
        _evaluation("eval-bad", accuracy=0.801)
    )
    training_foundation_service.models.register(_model("model-v2"))
    with pytest.raises(TrainingFoundationError) as error:
        training_foundation_service.promote(
            "model-v2", rejected, _admin(), human_approved=True
        )
    assert error.value.code == "PROMOTION_REJECTED_BY_POLICY"


def test_rollback_restores_the_superseded_model():
    training_foundation_service.models.register(
        _model("model-v1", stage=ModelStage.PRODUCTION)
    )
    training_foundation_service.models.register(_model("model-v2"))
    training_foundation_service.promote(
        "model-v2", _promotable(), _admin(), human_approved=True
    )

    restored = training_foundation_service.rollback(_admin())
    assert restored.model_ref == "model-v1"
    assert restored.stage is ModelStage.PRODUCTION
    # O revertido fica REJECTED e nao some: entender o erro exige guarda-lo.
    assert training_foundation_service.models.get("model-v2").stage is ModelStage.REJECTED


def test_rollback_refuses_without_a_previous_production_model():
    """Rollback sem alvo nao e rollback: e desligar o modelo e torcer."""
    training_foundation_service.models.register(
        _model("model-only", stage=ModelStage.PRODUCTION)
    )
    with pytest.raises(TrainingFoundationError) as error:
        training_foundation_service.rollback(_admin())
    assert error.value.code == "NO_PREVIOUS_PRODUCTION_MODEL"


def test_rollback_policy_requires_a_previous_production_by_type():
    assert RollbackPolicy().require_previous_production is True


def test_rollback_requires_admin():
    stranger = _admin().model_copy(update={"credential_id": "quem-sou-eu"})
    with pytest.raises(TrainingFoundationError) as error:
        training_foundation_service.rollback(stranger)
    assert error.value.code == "TRAINING_ADMIN_REQUIRED"


def test_no_real_training_was_executed_in_this_era():
    """A garantia da Era 8, afirmada como teste."""
    backend = _StubBackend()
    training_foundation_service.register_backend(backend)
    training_foundation_service.request_training(_run(), _admin())
    assert backend.started == []
    assert training_foundation_service.get_run("run-1").training_executed is False
    assert training_candidate_service.readiness(
        project_id=PROJECT
    ).training_started is False
