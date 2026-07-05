from pydantic import BaseModel, Field


class ExplorationPlan(BaseModel):
    """Plano exploratório assistido (Bloco 11).

    Modo plano/manual: o agente apenas sugere passos para um humano executar.
    can_execute_actions é sempre False — o PedroCore não abre navegador,
    não clica, não digita, não executa Playwright e não roda comandos.
    """

    task_type: str
    objective: str = ""
    exploration_plan: list[str] = Field(default_factory=list)
    manual_steps: list[str] = Field(default_factory=list)
    risk_areas: list[str] = Field(default_factory=list)
    required_evidence: list[str] = Field(default_factory=list)
    human_confirmations: list[str] = Field(default_factory=list)
    blocked_actions: list[str] = Field(default_factory=list)
    can_execute_actions: bool = False
    can_advance: bool = False
    requires_human_review: bool = True
    warnings: list[str] = Field(default_factory=list)
    warning_codes: list[str] = Field(default_factory=list)
