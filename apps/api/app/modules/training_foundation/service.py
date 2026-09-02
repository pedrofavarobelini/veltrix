"""Orquestracao de avaliacao, treino e promocao (Era 8).

O Veltrix decide; ele nao computa. Este modulo aplica politica e mantem
estado — iniciar um treino de verdade e trabalho de um `TrainingBackend`, e
nenhum backend real e chamado nesta Era.

A regra que atravessa tudo
--------------------------

Nada avanca sem readiness. Pedir treino sobre um dataset nao materializado
resulta em `BLOCKED` com motivo, nunca em um treino "de teste". Promover sem
baseline resulta em recusa, nunca em promocao otimista.
"""

from __future__ import annotations

from datetime import datetime, timezone

from app.modules.caller_identity.schemas import AuthenticatedCallerContext
from app.modules.dataset_registry.service import dataset_registry_service
from app.modules.training_data.acquisition import training_candidate_service
from app.modules.training_foundation.schemas import (
    BaselineComparison,
    EvaluationRun,
    EvaluationRunStatus,
    ModelRegistryEntry,
    ModelStage,
    PromotionDecision,
    PromotionPolicy,
    RollbackPolicy,
    TrainingRun,
    TrainingRunStatus,
)


class TrainingFoundationError(RuntimeError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class EvaluationRegistry:
    """Guarda avaliacoes e o baseline vigente por dataset."""

    def __init__(self) -> None:
        self._runs: dict[str, EvaluationRun] = {}
        self._baselines: dict[str, str] = {}

    def reset(self) -> None:
        self._runs.clear()
        self._baselines.clear()

    def record(self, run: EvaluationRun) -> EvaluationRun:
        if run.evaluation_id in self._runs:
            raise TrainingFoundationError("EVALUATION_ALREADY_RECORDED")
        self._runs[run.evaluation_id] = run.model_copy(deep=True)
        return run.model_copy(deep=True)

    def get(self, evaluation_id: str) -> EvaluationRun | None:
        found = self._runs.get(evaluation_id)
        return found.model_copy(deep=True) if found else None

    def set_baseline(self, dataset_id: str, evaluation_id: str) -> None:
        """Fixa o baseline de um dataset.

        Exige avaliacao CONCLUIDA: um baseline pendente compararia contra nada
        e faria qualquer candidato parecer melhor.
        """
        run = self._runs.get(evaluation_id)
        if run is None:
            raise TrainingFoundationError("EVALUATION_NOT_FOUND")
        if run.status is not EvaluationRunStatus.COMPLETED:
            raise TrainingFoundationError("BASELINE_MUST_BE_COMPLETED")
        self._baselines[dataset_id] = evaluation_id

    def baseline(self, dataset_id: str) -> EvaluationRun | None:
        evaluation_id = self._baselines.get(dataset_id)
        return self.get(evaluation_id) if evaluation_id else None


class ModelRegistry:
    """Registro de modelos e do que esta em producao."""

    def __init__(self) -> None:
        self._entries: dict[str, ModelRegistryEntry] = {}

    def reset(self) -> None:
        self._entries.clear()

    def register(self, entry: ModelRegistryEntry) -> ModelRegistryEntry:
        if entry.model_ref in self._entries:
            raise TrainingFoundationError("MODEL_ALREADY_REGISTERED")
        self._entries[entry.model_ref] = entry.model_copy(deep=True)
        return entry.model_copy(deep=True)

    def get(self, model_ref: str) -> ModelRegistryEntry | None:
        found = self._entries.get(model_ref)
        return found.model_copy(deep=True) if found else None

    def production(self) -> ModelRegistryEntry | None:
        return next(
            (
                item.model_copy(deep=True)
                for item in self._entries.values()
                if item.stage is ModelStage.PRODUCTION
            ),
            None,
        )

    def archived(self) -> list[ModelRegistryEntry]:
        return [
            item.model_copy(deep=True)
            for item in self._entries.values()
            if item.stage is ModelStage.ARCHIVED
        ]

    def _set_stage(self, model_ref: str, stage: ModelStage) -> ModelRegistryEntry:
        entry = self._entries[model_ref].model_copy(update={"stage": stage})
        self._entries[model_ref] = entry
        return entry.model_copy(deep=True)


class TrainingFoundationService:
    """Politica de treino, comparacao e promocao."""

    def __init__(self) -> None:
        self.evaluations = EvaluationRegistry()
        self.models = ModelRegistry()
        self._backends: dict[str, object] = {}
        self._runs: dict[str, TrainingRun] = {}

    def reset(self) -> None:
        self.evaluations.reset()
        self.models.reset()
        self._backends.clear()
        self._runs.clear()

    # -- backends ---------------------------------------------------------

    def register_backend(self, backend: object) -> None:
        """Registra um executor. O dominio so conhece a interface."""
        self._backends[getattr(backend, "backend_id")] = backend

    def backend(self, backend_id: str) -> object | None:
        return self._backends.get(backend_id)

    # -- treino -----------------------------------------------------------

    def request_training(
        self,
        run: TrainingRun,
        caller: AuthenticatedCallerContext,
    ) -> TrainingRun:
        """Registra um pedido de treino. NUNCA executa treino.

        Se a governanca nao permitir, o run e gravado como `BLOCKED` com o
        motivo — e nao rejeitado em silencio. Um pedido bloqueado registrado e
        auditavel; um pedido que some nao e.
        """
        if not training_candidate_service.admin_authorized(caller):
            raise TrainingFoundationError("TRAINING_ADMIN_REQUIRED")
        if run.run_id in self._runs:
            raise TrainingFoundationError("TRAINING_RUN_ALREADY_EXISTS")

        blockers = self._training_blockers(run)
        stored = run.model_copy(
            update={
                "requested_by": caller.credential_id,
                "status": (
                    TrainingRunStatus.BLOCKED if blockers else TrainingRunStatus.REQUESTED
                ),
                "blocked_reason_codes": sorted(blockers),
                "training_executed": False,
            }
        )
        self._runs[stored.run_id] = stored
        return stored.model_copy(deep=True)

    def _training_blockers(self, run: TrainingRun) -> set[str]:
        blockers: set[str] = set()
        versions = dataset_registry_service.versions(run.dataset_id)
        match = next(
            (item for item in versions if item.version == run.dataset_version), None
        )
        if match is None:
            # Sem versao materializada nao existe o que treinar. Este e o
            # caminho real do Veltrix hoje.
            blockers.add("DATASET_VERSION_NOT_MATERIALIZED")
        elif match.content_fingerprint != run.dataset_fingerprint:
            # Fingerprint divergente significa que o dataset mudou desde o
            # pedido. Treinar assim produziria um modelo cuja proveniencia
            # declarada seria falsa.
            blockers.add("DATASET_FINGERPRINT_MISMATCH")
        if run.backend_id not in self._backends:
            blockers.add("TRAINING_BACKEND_NOT_REGISTERED")
        elif not getattr(self._backends[run.backend_id], "available")():
            blockers.add("TRAINING_BACKEND_UNAVAILABLE")
        return blockers

    def get_run(self, run_id: str) -> TrainingRun | None:
        found = self._runs.get(run_id)
        return found.model_copy(deep=True) if found else None

    # -- comparacao e promocao -------------------------------------------

    def compare_to_baseline(
        self,
        candidate: EvaluationRun,
        policy: PromotionPolicy | None = None,
    ) -> BaselineComparison:
        """Compara um candidato ao baseline vigente do dataset."""
        active = policy or PromotionPolicy()
        reasons: set[str] = set()
        baseline = self.evaluations.baseline(candidate.dataset_id)

        if candidate.status is not EvaluationRunStatus.COMPLETED:
            reasons.add("CANDIDATE_EVALUATION_NOT_COMPLETED")
        if baseline is None:
            # Sem baseline nao ha comparacao. Promover assim seria dizer
            # "melhorou" sem ter contra o que.
            reasons.add("BASELINE_NOT_DEFINED")
        if baseline is not None and baseline.dataset_version != candidate.dataset_version:
            # Versoes diferentes sao alvos diferentes; a diferenca medida seria
            # do dataset, nao do modelo.
            reasons.add("BASELINE_DATASET_VERSION_MISMATCH")

        candidate_metric = candidate.metric(active.primary_metric)
        baseline_metric = baseline.metric(active.primary_metric) if baseline else None
        if candidate_metric is None or baseline_metric is None:
            reasons.add("PRIMARY_METRIC_MISSING")
            return BaselineComparison(
                decision=PromotionDecision.REJECT,
                primary_metric=active.primary_metric,
                baseline_value=baseline_metric.value if baseline_metric else 0.0,
                candidate_value=candidate_metric.value if candidate_metric else 0.0,
                improvement=0.0,
                reason_codes=sorted(reasons),
            )

        if candidate_metric.sample_size < active.minimum_sample_size:
            # Melhora grande em amostra minuscula tambem e ruido.
            reasons.add("SAMPLE_SIZE_TOO_SMALL")

        direction = 1.0 if candidate_metric.higher_is_better else -1.0
        improvement = (candidate_metric.value - baseline_metric.value) * direction
        if improvement < active.minimum_improvement:
            reasons.add("IMPROVEMENT_BELOW_THRESHOLD")

        for regression in self._regressions(candidate, baseline, active):
            reasons.add(regression)

        if reasons:
            decision = PromotionDecision.REJECT
        elif active.requires_human_review:
            decision = PromotionDecision.REQUIRES_REVIEW
        else:
            decision = PromotionDecision.PROMOTE

        return BaselineComparison(
            decision=decision,
            primary_metric=active.primary_metric,
            baseline_value=baseline_metric.value,
            candidate_value=candidate_metric.value,
            improvement=improvement,
            reason_codes=sorted(reasons),
        )

    @staticmethod
    def _regressions(
        candidate: EvaluationRun,
        baseline: EvaluationRun | None,
        policy: PromotionPolicy,
    ) -> set[str]:
        """Metrica secundaria que piorou demais barra a promocao.

        Sem este teto, um modelo poderia ganhar accuracy destruindo recall — e
        a metrica principal esconderia o estrago.
        """
        if baseline is None:
            return set()
        found: set[str] = set()
        for candidate_metric in candidate.metrics:
            if candidate_metric.metric is policy.primary_metric:
                continue
            baseline_metric = baseline.metric(candidate_metric.metric)
            if baseline_metric is None:
                continue
            direction = 1.0 if candidate_metric.higher_is_better else -1.0
            delta = (candidate_metric.value - baseline_metric.value) * direction
            if delta < -policy.maximum_regression:
                found.add("SECONDARY_METRIC_REGRESSION")
        return found

    def promote(
        self,
        model_ref: str,
        comparison: BaselineComparison,
        caller: AuthenticatedCallerContext,
        *,
        human_approved: bool = False,
    ) -> ModelRegistryEntry:
        """Promove um candidato a producao, arquivando o anterior."""
        if not training_candidate_service.admin_authorized(caller):
            raise TrainingFoundationError("TRAINING_ADMIN_REQUIRED")
        entry = self.models.get(model_ref)
        if entry is None:
            raise TrainingFoundationError("MODEL_NOT_REGISTERED")
        if entry.stage is not ModelStage.CANDIDATE:
            raise TrainingFoundationError("MODEL_NOT_PROMOTABLE")
        if comparison.decision is PromotionDecision.REJECT:
            raise TrainingFoundationError("PROMOTION_REJECTED_BY_POLICY")
        if comparison.decision is PromotionDecision.REQUIRES_REVIEW and not human_approved:
            raise TrainingFoundationError("HUMAN_REVIEW_REQUIRED")

        previous = self.models.production()
        if previous is not None:
            self.models._set_stage(previous.model_ref, ModelStage.ARCHIVED)  # noqa: SLF001
        promoted = entry.model_copy(
            update={
                "stage": ModelStage.PRODUCTION,
                "supersedes": previous.model_ref if previous else None,
            }
        )
        self.models._entries[model_ref] = promoted  # noqa: SLF001
        return promoted.model_copy(deep=True)

    def rollback(
        self,
        caller: AuthenticatedCallerContext,
        policy: RollbackPolicy | None = None,
    ) -> ModelRegistryEntry:
        """Volta para o modelo que o atual substituiu.

        Recusa quando nao ha alvo conhecido: um rollback sem destino nao e
        rollback, e desligar o modelo e torcer.
        """
        if not training_candidate_service.admin_authorized(caller):
            raise TrainingFoundationError("TRAINING_ADMIN_REQUIRED")
        active = policy or RollbackPolicy()
        current = self.models.production()
        if current is None:
            raise TrainingFoundationError("NO_PRODUCTION_MODEL")
        if active.require_previous_production and not current.supersedes:
            raise TrainingFoundationError("NO_PREVIOUS_PRODUCTION_MODEL")

        previous = self.models.get(current.supersedes or "")
        if previous is None:
            raise TrainingFoundationError("PREVIOUS_MODEL_NOT_FOUND")

        # O modelo revertido fica REJECTED e nao some: guardar o que deu errado
        # e o que permite entender por que deu errado.
        self.models._set_stage(  # noqa: SLF001
            current.model_ref,
            ModelStage.REJECTED if active.keep_rejected_for_audit else ModelStage.ARCHIVED,
        )
        restored = previous.model_copy(update={"stage": ModelStage.PRODUCTION})
        self.models._entries[previous.model_ref] = restored  # noqa: SLF001
        return restored.model_copy(deep=True)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


training_foundation_service = TrainingFoundationService()
