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
    text_block: str = ""
