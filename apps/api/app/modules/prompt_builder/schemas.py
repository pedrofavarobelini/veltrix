from pydantic import BaseModel

from app.modules.project_context.schemas import ProjectContext
from app.modules.task_router.schemas import TaskStrategy


class PromptBuildInput(BaseModel):
    message: str
    mode: str
    system_prompt: str | None = None
    strategy: TaskStrategy
    project: ProjectContext
    origin_system: str
    context: dict | None = None
    metadata: dict | None = None
    artifacts_text_block: str | None = None
    # ECOSYSTEM-INTELLIGENCE-SUITE-01: seções opcionais; None preserva o
    # comportamento anterior do prompt.
    intelligence_instructions: list[str] | None = None
    memory_block: str | None = None


class PromptBuildResult(BaseModel):
    enriched_system_prompt: str
    full_prompt: str
