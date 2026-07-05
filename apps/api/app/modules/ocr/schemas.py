from pydantic import BaseModel, Field


class OCRResult(BaseModel):
    """Resultado de uma tentativa de OCR local (IMPLEMENT-05D).

    executed=True só ocorre com PEDROCORE_OCR_ENABLED=true E dependência local
    instalada. O texto extraído nunca substitui revisão humana e nunca libera
    release gate sozinho.
    """

    attempted: bool = False
    executed: bool = False
    engine: str = "local"
    text: str | None = None
    requires_human_review: bool = True
    warnings: list[str] = Field(default_factory=list)
    warning_codes: list[str] = Field(default_factory=list)
