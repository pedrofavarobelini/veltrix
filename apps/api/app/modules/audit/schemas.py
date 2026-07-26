from pydantic import BaseModel


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
    authorization_result: str | None = None
    authorization_reason_code: str | None = None
