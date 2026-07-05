from pydantic import BaseModel, Field


class ArtifactInput(BaseModel):
    type: str
    name: str | None = None
    content: str | None = None
    metadata: dict | None = None


class ArtifactProcessingResult(BaseModel):
    count: int = 0
    types: list[str] = Field(default_factory=list)
    names: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    warning_codes: list[str] = Field(default_factory=list)
    text_block: str = ""
    analysis_text: str = ""
    textual_count: int = 0
    rejected_count: int = 0
    path_rejected: bool = False
    truncated: bool = False
