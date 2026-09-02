"""Servico do Evaluation Plane V2.

Ele registra avaliacoes e as recupera. Nao promove, nao decide e nao aprova —
essas tres coisas pertencem ao Model Registry, e mante-las fora daqui e o que
impede que quem mede dependa do resultado.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone

from app.modules.evaluation_plane.schemas import (
    EvaluationMetric,
    EvaluationRecord,
    EvaluationStatus,
    EvaluationSubject,
)

DATASET_NOT_READY = "DATASET_NOT_READY"
EVALUATION_COMPLETED = "EVALUATION_COMPLETED"


class EvaluationPlaneError(RuntimeError):
    """Recusa explicita do plano de avaliacao."""


class EvaluationPlaneService:
    """Registro de avaliacoes, isolado por projeto."""

    def __init__(self) -> None:
        self._records: dict[tuple[str, str], EvaluationRecord] = {}

    def record(
        self,
        *,
        subject: EvaluationSubject,
        suite: str,
        suite_version: str,
        environment: str,
        project_id: str,
        producer: str,
        metrics: tuple[EvaluationMetric, ...] = (),
        dataset_id: str | None = None,
        dataset_slice: str | None = None,
        evidence_ids: tuple[str, ...] = (),
        correlation_id: str | None = None,
        now: datetime | None = None,
    ) -> EvaluationRecord:
        """Registra uma avaliacao.

        Sem `dataset_id`, o resultado sai `DATASET_NOT_READY` e SEM metricas —
        mesmo que o chamador tenha enviado metricas. Aceitar numeros sobre um
        dataset que nao existe seria a forma mais silenciosa de fabricar
        evidencia.
        """
        projeto = project_id.strip().lower()
        pronto = bool(dataset_id) and bool(metrics)

        status = EvaluationStatus.COMPLETED if pronto else EvaluationStatus.DATASET_NOT_READY
        registro = EvaluationRecord(
            evaluation_id=self._evaluation_id(subject, suite, projeto, dataset_id),
            subject=subject,
            suite=suite,
            suite_version=suite_version,
            dataset_id=dataset_id,
            dataset_slice=dataset_slice,
            environment=environment,
            project_id=projeto,
            producer=producer,
            status=status,
            metrics=metrics if pronto else (),
            reason_codes=(EVALUATION_COMPLETED,) if pronto else (DATASET_NOT_READY,),
            evidence_ids=evidence_ids,
            correlation_id=correlation_id,
            evaluated_at=now or datetime.now(timezone.utc),
        )
        self._records[(projeto, registro.evaluation_id)] = registro
        return registro

    def get(self, project_id: str, evaluation_id: str) -> EvaluationRecord | None:
        return self._records.get((project_id.strip().lower(), evaluation_id))

    def for_subject(self, project_id: str, subject_id: str) -> list[EvaluationRecord]:
        projeto = project_id.strip().lower()
        return [
            item
            for (dono, _), item in self._records.items()
            if dono == projeto and item.subject.subject_id == subject_id
        ]

    def promotion_evidence(self, project_id: str, subject_id: str) -> list[str]:
        """Ids que servem de evidencia para promocao. So avaliacao concluida."""
        return [
            item.evaluation_id
            for item in self.for_subject(project_id, subject_id)
            if item.usable_as_promotion_evidence
        ]

    def reset(self) -> None:
        self._records.clear()

    @staticmethod
    def _evaluation_id(subject, suite, project_id, dataset_id) -> str:
        payload = "|".join(
            [
                subject.kind.value,
                subject.subject_id,
                subject.subject_version or "",
                suite,
                project_id,
                dataset_id or "",
                datetime.now(timezone.utc).isoformat(),
            ]
        )
        return "eval_" + hashlib.sha256(payload.encode()).hexdigest()[:24]


evaluation_plane_service = EvaluationPlaneService()
