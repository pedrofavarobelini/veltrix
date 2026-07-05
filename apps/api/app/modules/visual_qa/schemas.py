from pydantic import BaseModel, Field


class VisualQAAnalysis(BaseModel):
    """Análise visual de QA em modo stub/contrato (Bloco 10).

    Nesta frente não há OCR, não há provider multimodal e não há Playwright.
    Os campos ocr_attempted/provider_attempted/playwright_attempted existem
    justamente para provar que nada disso foi tentado.
    """

    status: str = "not_analyzed"
    visual_artifact_count: int = 0
    supported: bool = False
    mode: str = "stub"
    can_advance: bool = False
    requires_human_review: bool = True
    suggested_manual_checks: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    warning_codes: list[str] = Field(default_factory=list)
    ocr_attempted: bool = False
    provider_attempted: bool = False
    playwright_attempted: bool = False
