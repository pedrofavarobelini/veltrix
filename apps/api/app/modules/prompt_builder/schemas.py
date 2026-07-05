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


class PromptBuildResult(BaseModel):
    enriched_system_prompt: str
    full_prompt: str
