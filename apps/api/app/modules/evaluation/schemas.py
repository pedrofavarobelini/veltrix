from pydantic import BaseModel, Field

RISK_LEVELS = {"none", "low", "medium", "high", "critical"}


class EvaluationCheck(BaseModel):
    """Resultado de um check individual de segurança/coerência."""

    name: str
    passed: bool
    severity: str = "info"
    message: str


class EvaluationResult(BaseModel):
    """Resultado agregado de uma avaliação determinística.

    A avaliação não usa provider real, não faz benchmark de LLM e não
    aprova nada sozinha: sinais críticos sempre exigem revisão humana.
    """

    passed: bool
    checks: list[EvaluationCheck] = Field(default_factory=list)
    requires_human_review: bool = False
    risk_level: str = "none"
