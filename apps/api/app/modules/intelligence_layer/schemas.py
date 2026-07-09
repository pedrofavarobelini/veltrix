from pydantic import BaseModel, Field, field_validator

# Perfis de resposta suportados pela Intelligence Layer (fundação).
RESPONSE_PROFILES = {
    "technical_direct",
    "qa_strict",
    "release_gate_strict",
    "financial_cautious",
    "educational",
    "executive_summary",
    "implementation_plan",
    "general_assistant",
}

SENSITIVE_DATA_POLICIES = {"sanitize", "block"}


class IntelligenceContextPolicy(BaseModel):
    """Política de contexto de um plano de inteligência.

    allow_real_provider é SEMPRE False nesta fundação: a Intelligence Layer
    nunca habilita provider real; a autorização continua vindo apenas do
    payload explícito (allow_real_provider) validado pelo safe mode.
    """

    allow_memory_context: bool = False
    allow_project_context: bool = True
    allow_report_context: bool = False
    allow_real_provider: bool = False
    requires_human_review: bool = False
    sensitive_data_policy: str = "sanitize"

    @field_validator("allow_real_provider")
    @classmethod
    def real_provider_never_enabled(cls, value: bool) -> bool:
        if value:
            raise ValueError(
                "Intelligence Layer nunca habilita provider real; "
                "allow_real_provider deve permanecer False."
            )
        return value

    @field_validator("sensitive_data_policy")
    @classmethod
    def sensitive_policy_known(cls, value: str) -> str:
        if value not in SENSITIVE_DATA_POLICIES:
            raise ValueError(
                f"sensitive_data_policy inválida: '{value}'. "
                f"Permitidas: {sorted(SENSITIVE_DATA_POLICIES)}."
            )
        return value


class IntelligencePlan(BaseModel):
    """Plano cognitivo/operacional determinístico produzido antes do provider.

    O plano não chama provider, não persiste memória e não altera prompt de
    produção automaticamente; nesta fundação ele apenas padroniza instruções
    e metadados internos para o pipeline.
    """

    task_type: str
    response_profile: str = "general_assistant"
    context_policy: IntelligenceContextPolicy = Field(
        default_factory=IntelligenceContextPolicy
    )
    safety_flags: list[str] = Field(default_factory=list)
    instructions: list[str] = Field(default_factory=list)
    memory_hints: list[str] = Field(default_factory=list)
    evaluation_hints: list[str] = Field(default_factory=list)

    @field_validator("response_profile")
    @classmethod
    def profile_known(cls, value: str) -> str:
        if value not in RESPONSE_PROFILES:
            raise ValueError(
                f"response_profile inválido: '{value}'. "
                f"Permitidos: {sorted(RESPONSE_PROFILES)}."
            )
        return value
