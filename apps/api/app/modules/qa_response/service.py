from app.modules.artifacts.schemas import ArtifactProcessingResult
from app.modules.artifacts.service import VISUAL_NOT_SUPPORTED_WARNING
from app.modules.qa_response.schemas import QAResponseSkeleton
from app.modules.task_router.service import (
    CRITICAL_TASK_TYPES,
    FALLBACK_CRITICAL_WARNING,
)

QA_SKELETON_WARNING = "Skeleton de QA gerado sem análise real."

QA_NO_ARTIFACTS_WARNING = (
    "Tarefa QA sem artefatos enviados; análise real não pode ser inferida."
)

QA_SKELETON_SUMMARY = (
    "QA Intelligence real ainda não implementada; "
    "resposta textual do provider deve ser revisada manualmente."
)


class QAResponseService:
    def build_skeleton(
        self,
        task_type: str,
        fallback_used: bool,
        artifacts_result: ArtifactProcessingResult,
    ) -> QAResponseSkeleton | None:
        if task_type not in CRITICAL_TASK_TYPES:
            return None

        warnings = [QA_SKELETON_WARNING]

        if fallback_used:
            warnings.append(FALLBACK_CRITICAL_WARNING)

        if artifacts_result.count == 0:
            warnings.append(QA_NO_ARTIFACTS_WARNING)

        if VISUAL_NOT_SUPPORTED_WARNING in artifacts_result.warnings:
            warnings.append(VISUAL_NOT_SUPPORTED_WARNING)

        return QAResponseSkeleton(
            status="not_analyzed",
            summary=QA_SKELETON_SUMMARY,
            risk_level="unknown",
            can_advance=False,
            confidence=0.0,
            warnings=warnings,
        )


qa_response_service = QAResponseService()
