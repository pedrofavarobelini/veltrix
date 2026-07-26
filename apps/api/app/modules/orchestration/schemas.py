from pydantic import BaseModel, Field

from app.modules.audit.schemas import AuditMetadata
from app.modules.contracts.codes import WarningItem
from app.modules.exploration.schemas import ExplorationPlan
from app.modules.intelligence_layer.schemas import IntelligencePlan
from app.modules.qa_response.schemas import QAResponseSkeleton, ReleaseGateResult
from app.modules.shadow_routing.schemas import ShadowRoutingDecision
from app.modules.visual_qa.schemas import VisualQAAnalysis


class OrchestrationOutcome(BaseModel):
    """Resultado interno completo do pipeline, consumido por /api/chat e /api/orchestrate."""

    answer: str
    provider_requested: str
    provider_used: str
    model: str
    mode: str
    fallback_used: bool = False
    safe_mode_blocked: bool = False
    error: str | None = None
    task_type: str
    origin_system: str
    task_criticality: str
    requires_structured_response: bool
    response_style: str
    project_id: str
    project_read_only: bool
    project_can_execute_commands: bool
    project_can_write_files: bool
    task_allowed_for_project: bool
    artifact_count: int
    artifact_types: list[str] = Field(default_factory=list)
    artifact_warnings: list[str] = Field(default_factory=list)
    qa_skeleton: QAResponseSkeleton | None = None
    release_gate: ReleaseGateResult | None = None
    visual_qa_analysis: VisualQAAnalysis | None = None
    exploration: ExplorationPlan | None = None
    warning_items: list[WarningItem] = Field(default_factory=list)
    audit: AuditMetadata
    status: str = "ok"
    blocked_reason: str | None = None
    error_code: str | None = None
    # PEDROCORE-MODEL-FOUNDATION-01: plano interno da Intelligence Layer.
    # Não é exposto em ChatResponse/OrchestrateResponse nesta frente.
    intelligence_plan: IntelligencePlan | None = None
    # ECOSYSTEM-INTELLIGENCE-SUITE-01: memória técnica consultada nesta request.
    memory_used: bool = False
    # MULTI-PROVIDER-SAFE-EVOLUTION Etapa 4: decisão planejada pela política
    # shadow. É metadado interno (auditoria/observabilidade); NÃO é exposto em
    # ChatResponse/OrchestrateResponse e não influencia a execução real.
    shadow_decision: ShadowRoutingDecision | None = None

    @property
    def task_warnings(self) -> list[str]:
        return [item.message for item in self.warning_items]

    @property
    def warning_codes(self) -> list[str]:
        return [item.code for item in self.warning_items]


class OrchestrateResponse(BaseModel):
    """Contrato de resposta do endpoint POST /api/orchestrate."""

    status: str = "ok"
    answer: str
    task_type: str
    origin_system: str
    provider_requested: str
    provider_used: str
    model: str
    mode: str
    fallback_used: bool = False
    safe_mode_blocked: bool = False
    allow_real_provider: bool = False
    warning_codes: list[str] = Field(default_factory=list)
    warnings: list[WarningItem] = Field(default_factory=list)
    task_warnings: list[str] = Field(default_factory=list)
    error_code: str | None = None
    blocked_reason: str | None = None
    project_id: str = "pedrocore"
    task_allowed_for_project: bool = True
    artifact_count: int = 0
    artifact_types: list[str] = Field(default_factory=list)
    artifact_warnings: list[str] = Field(default_factory=list)
    qa: QAResponseSkeleton | None = None
    release_gate: ReleaseGateResult | None = None
    visual_qa_analysis: VisualQAAnalysis | None = None
    exploration: ExplorationPlan | None = None
    audit: AuditMetadata
    # ECOSYSTEM-INTELLIGENCE-SUITE-01 (aditivo, retrocompatível): indica se a
    # memória técnica foi anexada ao contexto (context_from_memory=true).
    memory_used: bool = False


class AssistantResponsePayload(BaseModel):
    """Payload auxiliar de assistente para sistemas consumidores do ecossistema.

    Não substitui OrchestrateResponse: é uma projeção documentada/conveniente
    do outcome, montada por build_assistant_payload() no OrchestrationService.
    O backend do sistema consumidor pode usá-la como formato de resposta do
    seu próprio assistente (ex.: futura FINGUARD-PEDROCORE-ASSISTANT-01).
    """

    answer: str
    suggestions: list[str] = Field(default_factory=list)
    disclaimer: str | None = None
    safety_flags: list[str] = Field(default_factory=list)
    provider_used: str
    model: str
    audit_id: str | None = None
    memory_used: bool = False
    evaluation: dict | None = None
    warnings: list[WarningItem] = Field(default_factory=list)
