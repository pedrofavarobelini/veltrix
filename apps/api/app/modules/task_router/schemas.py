from pydantic import BaseModel, Field


class TaskStrategy(BaseModel):
    task_type: str
    response_style: str = "free_text"
    requires_structured_response: bool = False
    criticality: str = "low"
    allow_mock: bool = True
    warnings: list[str] = Field(default_factory=list)
