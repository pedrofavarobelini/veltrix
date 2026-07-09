from pydantic import BaseModel, Field, field_validator

from app.modules.artifacts.schemas import ArtifactInput


class EvalCase(BaseModel):
    """Caso de avaliação determinístico.

    Roda contra o pipeline real de orquestração usando apenas providers
    seguros (mock/local_qa/local_model bloqueado); allow_real_provider é
    rejeitado por validação — o harness nunca chama provider real nem rede.
    """

    case_id: str
    description: str = ""
    project_id: str = "pedrocore"
    task_type: str = "general_chat"
    input: str
    context: dict | None = None
    provider: str = "mock"
    mode: str = "tecnico"
    allow_real_provider: bool = False
    allow_local_model: bool = False
    context_from_memory: bool = False
    artifacts: list[ArtifactInput] | None = None
    expected_requirements: list[str] = Field(default_factory=list)
    forbidden_patterns: list[str] = Field(default_factory=list)
    expected_warnings: list[str] = Field(default_factory=list)
    expected_safety_flags: list[str] = Field(default_factory=list)
    expect_release_can_advance: bool | None = None
    expect_memory_used: bool | None = None

    @field_validator("allow_real_provider")
    @classmethod
    def real_provider_forbidden(cls, value: bool) -> bool:
        if value:
            raise ValueError(
                "Eval harness nunca usa provider real; allow_real_provider "
                "deve permanecer False."
            )
        return value


class EvalCaseResult(BaseModel):
    case_id: str
    passed: bool
    failures: list[str] = Field(default_factory=list)
    provider_used: str | None = None
    task_type: str | None = None


class EvalRunResult(BaseModel):
    run_id: str
    total: int
    passed: int
    failed: int
    risk_level: str = "none"
    cases: list[EvalCaseResult] = Field(default_factory=list)
    created_at: str | None = None
