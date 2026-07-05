from pydantic import BaseModel, Field


class ProjectContext(BaseModel):
    project_id: str
    display_name: str
    read_only: bool = True
    can_execute_commands: bool = False
    can_write_files: bool = False
    allowed_tasks: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    notes: str | None = None
