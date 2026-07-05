from app.modules.artifacts.schemas import ArtifactProcessingResult
from app.modules.artifacts.service import VISUAL_ARTIFACT_TYPES
from app.modules.contracts import codes
from app.modules.ocr import service as ocr_module
from app.modules.real_features import service as real_features
from app.modules.visual_qa.schemas import VisualQAAnalysis

VISUAL_QA_NOT_ENABLED_WARNING = (
    "QA visual real ainda não está habilitado; artefatos visuais foram apenas "
    "registrados (sem OCR, sem provider multimodal, sem Playwright)."
)

VISUAL_QA_HUMAN_REVIEW_WARNING = (
    "Evidência visual exige revisão humana; nenhuma análise automática foi realizada."
)

SUGGESTED_MANUAL_CHECKS = [
    "Abrir manualmente o screenshot/imagem e conferir o estado da tela.",
    "Comparar a evidência visual com o comportamento esperado documentado.",
    "Confirmar manualmente se a tela corresponde ao fluxo/rota reportado.",
    "Registrar a conclusão humana como artefato textual para análise QA local.",
]

# Guard multimodal (IMPLEMENT-05E): QA visual real com provider multimodal só
# seria possível com TODAS as condições abaixo — e, mesmo assim, nesta versão o
# envio real não é executado (contrato preparado; execução exige frente futura
# com aprovação). Nenhuma imagem é enviada a provider externo.
MULTIMODAL_DISABLED_WARNING = (
    "Provider multimodal desabilitado (PEDROCORE_MULTIMODAL_PROVIDER_ENABLED=false); "
    "QA visual real não executado."
)
MULTIMODAL_VISUAL_FLAG_WARNING = (
    "QA visual real desabilitado (PEDROCORE_VISUAL_QA_ENABLED=false)."
)
MULTIMODAL_AUTH_WARNING = (
    "QA visual real exige allow_real_provider=true explícito no payload."
)
MULTIMODAL_CONTRACT_ONLY_WARNING = (
    "Todas as flags de QA visual real estão ligadas, mas o envio multimodal real "
    "não é executado nesta versão: contrato preparado; execução exige frente "
    "futura com confirmação humana."
)


def evaluate_real_visual_guard(allow_real_provider: bool) -> tuple[list[str], list[str]]:
    """Retorna (warnings, warning_codes) do guard multimodal. Nunca executa envio."""
    warnings: list[str] = []
    warning_codes: list[str] = []

    if not real_features.multimodal_enabled():
        warnings.append(MULTIMODAL_DISABLED_WARNING)
        warning_codes.append(codes.MULTIMODAL_PROVIDER_DISABLED)
    if not real_features.visual_qa_enabled():
        warnings.append(MULTIMODAL_VISUAL_FLAG_WARNING)
        warning_codes.append(codes.MULTIMODAL_PROVIDER_REQUIRES_FLAG)
    if not allow_real_provider:
        warnings.append(MULTIMODAL_AUTH_WARNING)
        warning_codes.append(codes.MULTIMODAL_PROVIDER_REQUIRES_EXPLICIT_AUTH)

    if not warnings:
        warnings.append(MULTIMODAL_CONTRACT_ONLY_WARNING)
        warning_codes.append(codes.REAL_FEATURE_REQUIRES_HUMAN_CONFIRMATION)

    return warnings, warning_codes


class VisualQAService:
    def analyze(
        self,
        artifacts_result: ArtifactProcessingResult,
        allow_real_provider: bool = False,
    ) -> VisualQAAnalysis | None:
        visual_count = sum(
            1 for artifact_type in artifacts_result.types
            if artifact_type in VISUAL_ARTIFACT_TYPES
        )

        if visual_count == 0:
            return None

        warnings = [VISUAL_QA_NOT_ENABLED_WARNING, VISUAL_QA_HUMAN_REVIEW_WARNING]
        warning_codes = [
            codes.VISUAL_QA_NOT_ENABLED,
            codes.VISUAL_QA_REQUIRES_HUMAN_REVIEW,
        ]

        # Status do OCR local (IMPLEMENT-05D): informativo, nunca executa aqui.
        if not real_features.ocr_enabled():
            warnings.append(ocr_module.OCR_NOT_ENABLED_WARNING)
            warning_codes.append(codes.OCR_NOT_ENABLED)
        elif not ocr_module.dependency_available():
            warnings.append(ocr_module.OCR_DEPENDENCY_UNAVAILABLE_WARNING)
            warning_codes.append(codes.OCR_DEPENDENCY_UNAVAILABLE)

        # Guard multimodal (IMPLEMENT-05E): nunca envia imagem a provider.
        guard_warnings, guard_codes = evaluate_real_visual_guard(allow_real_provider)
        warnings.extend(guard_warnings)
        warning_codes.extend(guard_codes)

        return VisualQAAnalysis(
            status="not_analyzed",
            visual_artifact_count=visual_count,
            supported=False,
            mode="stub",
            can_advance=False,
            requires_human_review=True,
            suggested_manual_checks=list(SUGGESTED_MANUAL_CHECKS),
            warnings=warnings,
            warning_codes=warning_codes,
            ocr_attempted=False,
            provider_attempted=False,
            playwright_attempted=False,
        )


visual_qa_service = VisualQAService()
