from pydantic import BaseModel, Field


class PolicyEnforcementResult(BaseModel):
    """Resultado do enforcement forte de policy (FINALIZE-06A / IMPLEMENT-05B).

    blocked=True significa bloqueio real: a requisição não chega ao provider,
    ao Artifact Reader nem à análise QA.
    """

    blocked: bool = False
    error_code: str | None = None
    blocked_reason: str | None = None
    warnings: list[str] = Field(default_factory=list)
    warning_codes: list[str] = Field(default_factory=list)
