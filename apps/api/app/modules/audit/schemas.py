from typing import Any

from pydantic import BaseModel, Field


class AuditMetadata(BaseModel):
    audit_id: str
    timestamp: str
    origin_system: str
    task_type: str
    provider_requested: str
    fallback_used: bool | None = None
    criticality: str
    provider_used: str | None = None
    safe_mode_blocked: bool = False
    status: str = "ok"
    latency_ms: float | None = None
    risk_level: str | None = None
    can_advance: bool | None = None
    # MULTI-PROVIDER-SAFE-EVOLUTION Etapa 2 (aditivo, retrocompatível): a
    # auditoria distingue identidade autenticada, origem declarada, provider
    # solicitado e provider efetivamente executado. Nada aqui é segredo: o
    # credential_identifier é um ID configurado ou fingerprint truncado.
    credential_id: str | None = None
    authenticated: bool = False
    # Autenticado != identificado de forma inequívoca: identity_strength diz
    # se a credencial prova o projeto (`registered`) ou não (`ambiguous`).
    identity_strength: str | None = None
    project_id_authenticated: str | None = None
    caller_role: str | None = None
    environment: str | None = None
    origin_system_declared: str | None = None
    origin_validation: str | None = None
    provider_selection_mode: str | None = None
    provider_selected: str | None = None
    # Etapa 3: modelo solicitado != modelo selecionado pelo PedroCore.
    model_requested: str | None = None
    model_selected: str | None = None
    model_source: str | None = None
    # Etapa 4: decisão planejada pela política shadow (observação apenas).
    shadow_enabled: bool = False
    shadow_selected_provider: str | None = None
    shadow_selected_model: str | None = None
    shadow_would_differ: bool | None = None
    shadow_policy_version: str | None = None
    # Etapa 5: a mesma política determinística opera em legacy/shadow/enforced.
    routing_mode: str = "legacy"
    routing_policy_version: str | None = None
    routing_configuration_valid: bool = True
    routing_configuration_reason: str | None = None
    routing_selected_provider: str | None = None
    routing_selected_model: str | None = None
    routing_selection_reason: str | None = None
    routing_candidates_considered: list[dict[str, Any]] = Field(default_factory=list)
    routing_candidates_eliminated: list[dict[str, Any]] = Field(default_factory=list)
    real_provider_attempt_count: int = 0
    # Etapa 6: tentativas identificadas e estado do circuito antes/depois.
    provider_attempts: list[dict[str, Any]] = Field(default_factory=list)
    # Etapa 7: fallback real é independente, default-off e no máximo secundário.
    real_fallback_enabled: bool = False
    real_fallback_attempted: bool = False
    real_fallback_reason: str | None = None
    real_fallback_candidates_considered: list[dict[str, Any]] = Field(
        default_factory=list
    )
    real_fallback_candidates_eliminated: list[dict[str, Any]] = Field(
        default_factory=list
    )
    real_provider_attempt_record_count: int = 0
    authorization_result: str | None = None
    authorization_reason_code: str | None = None
    # PROVIDER-OUTPUT-BUDGET-CANCELLATION-01 (aditivo, retrocompatível):
    # orçamento de saída decidido pelo PedroCore, tempos aplicados e metadados
    # de término. Nada aqui é sensível: são números e rótulos, nunca prompt,
    # resposta, contexto financeiro ou credencial.
    output_budget_effective: int | None = None
    output_budget_source: str | None = None
    output_budget_clamped: bool | None = None
    output_budget_global_cap: int | None = None
    output_budget_model_cap: int | None = None
    output_budget_task_cap: int | None = None
    orchestration_timeout_ms: int | None = None
    transport_timeout_ms: int | None = None
    # Fatos de transporte LOCAL. Não são prova de término remoto: mesmo com
    # ambos True, `completion_certainty` permanece `ambiguous`.
    transport_cancel_requested: bool = False
    transport_cancelled_locally: bool = False
    provider_finish_reason: str | None = None
    provider_input_tokens: int | None = None
    provider_output_tokens: int | None = None
    provider_total_tokens: int | None = None
    provider_output_truncated: bool = False
