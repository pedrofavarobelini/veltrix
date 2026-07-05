from app.modules.artifacts.schemas import ArtifactProcessingResult
from app.modules.artifacts.service import VISUAL_NOT_SUPPORTED_WARNING
from app.modules.contracts import codes
from app.modules.qa_analysis.schemas import QATextAnalysisResult
from app.modules.qa_response.schemas import QAResponseSkeleton, ReleaseGateResult
from app.modules.task_router.service import (
    CRITICAL_TASK_TYPES,
    FALLBACK_CRITICAL_WARNING,
)

RELEASE_GATE_TASK_TYPE = "release_gate_review"

QA_SKELETON_WARNING = "Skeleton de QA gerado sem análise real."

QA_NO_ARTIFACTS_WARNING = (
    "Tarefa QA sem artefatos enviados; análise real não pode ser inferida."
)

QA_SKELETON_SUMMARY = (
    "QA Intelligence real ainda não implementada; "
    "resposta textual do provider deve ser revisada manualmente."
)

RELEASE_GATE_MOCK_WARNING = (
    "Provider Mock não valida release gate real; "
    "use análise local (provider local_qa) com artefatos textuais."
)

RELEASE_GATE_LOCAL_DECISION_WARNING = (
    "Decisão de release gate baseada em análise textual local determinística; "
    "a resposta conversacional do provider não é evidência."
)

ANALYSIS_SOURCE_LOCAL = "local_text_heuristic"
ANALYSIS_SOURCE_NONE = "none"


class QAResponseService:
    def build_skeleton(
        self,
        task_type: str,
        fallback_used: bool,
        artifacts_result: ArtifactProcessingResult,
        analysis: QATextAnalysisResult | None = None,
        safe_mode_blocked: bool = False,
    ) -> QAResponseSkeleton | None:
        if task_type not in CRITICAL_TASK_TYPES:
            return None

        if analysis is not None and analysis.analyzed:
            warnings = list(analysis.warnings)

            if fallback_used and FALLBACK_CRITICAL_WARNING not in warnings:
                warnings.append(FALLBACK_CRITICAL_WARNING)

            if (
                VISUAL_NOT_SUPPORTED_WARNING in artifacts_result.warnings
                and VISUAL_NOT_SUPPORTED_WARNING not in warnings
            ):
                warnings.append(VISUAL_NOT_SUPPORTED_WARNING)

            can_advance = analysis.can_advance
            if (
                fallback_used
                or safe_mode_blocked
                or artifacts_result.count == 0
                or artifacts_result.path_rejected
                or analysis.risk_level != "low"
                or analysis.failures
            ):
                can_advance = False

            return QAResponseSkeleton(
                status=analysis.status,
                summary=analysis.summary,
                findings=list(analysis.findings),
                failures=list(analysis.failures),
                probable_causes=list(analysis.probable_causes),
                suggested_commands=list(analysis.suggested_commands),
                suggested_fixes=list(analysis.suggested_fixes),
                risk_level=analysis.risk_level,
                can_advance=can_advance,
                confidence=analysis.confidence,
                warnings=warnings,
                analysis_source=ANALYSIS_SOURCE_LOCAL,
            )

        warnings = [QA_SKELETON_WARNING]

        if fallback_used:
            warnings.append(FALLBACK_CRITICAL_WARNING)

        if artifacts_result.count == 0:
            warnings.append(QA_NO_ARTIFACTS_WARNING)

        if VISUAL_NOT_SUPPORTED_WARNING in artifacts_result.warnings:
            warnings.append(VISUAL_NOT_SUPPORTED_WARNING)

        if analysis is not None:
            for text in analysis.warnings:
                if text not in warnings:
                    warnings.append(text)

        return QAResponseSkeleton(
            status="not_analyzed",
            summary=QA_SKELETON_SUMMARY,
            risk_level=analysis.risk_level if analysis is not None else "unknown",
            can_advance=False,
            confidence=0.0,
            warnings=warnings,
            suggested_commands=(
                list(analysis.suggested_commands) if analysis is not None else []
            ),
            analysis_source=ANALYSIS_SOURCE_NONE,
        )

    def evaluate_release_gate(
        self,
        artifacts_result: ArtifactProcessingResult,
        analysis: QATextAnalysisResult | None,
        fallback_used: bool,
        safe_mode_blocked: bool,
        provider_used: str,
    ) -> ReleaseGateResult:
        warnings = [RELEASE_GATE_LOCAL_DECISION_WARNING]
        warning_codes: list[str] = []
        risk_level = analysis.risk_level if analysis is not None else "unknown"
        confidence = analysis.confidence if analysis is not None else 0.0

        blocked_reason: str | None = None

        if artifacts_result.count == 0:
            blocked_reason = "Sem artefatos para release gate."
        elif artifacts_result.path_rejected:
            blocked_reason = "Artefato com caminho de arquivo rejeitado."
        elif analysis is None or not analysis.analyzed:
            blocked_reason = "Evidência textual insuficiente para release gate."
        elif artifacts_result.truncated:
            blocked_reason = "Artefato truncado; evidência incompleta para release gate."
        elif analysis.failures:
            blocked_reason = "Falha ou erro detectado nos artefatos."
        elif analysis.risk_level in {"high", "critical"}:
            blocked_reason = f"Risco {analysis.risk_level} detectado."
        elif fallback_used:
            blocked_reason = "Fallback Mock em fluxo de release gate."
        elif safe_mode_blocked:
            blocked_reason = "Provider real bloqueado pelo safe mode em fluxo de release gate."
        elif provider_used == "mock":
            blocked_reason = RELEASE_GATE_MOCK_WARNING
            if codes.QA_FALLBACK_MOCK not in warning_codes:
                warning_codes.append(codes.QA_FALLBACK_MOCK)
        elif analysis.confidence < 0.6:
            blocked_reason = "Confiança insuficiente para liberar release gate."
        elif not analysis.can_advance:
            blocked_reason = "Análise QA local não aprovou o avanço."

        can_advance = blocked_reason is None

        if not can_advance:
            warning_codes.append(codes.RELEASE_GATE_BLOCKED)
            warnings.append(f"Release gate bloqueado: {blocked_reason}")

        return ReleaseGateResult(
            can_advance=can_advance,
            blocked_reason=blocked_reason,
            risk_level=risk_level,
            confidence=confidence,
            warnings=warnings,
            warning_codes=warning_codes,
        )


qa_response_service = QAResponseService()
