from pydantic import BaseModel, Field


class QAResponseSkeleton(BaseModel):
    status: str = "not_analyzed"
    summary: str
    findings: list[str] = Field(default_factory=list)
    failures: list[str] = Field(default_factory=list)
    probable_causes: list[str] = Field(default_factory=list)
    suggested_commands: list[str] = Field(default_factory=list)
    suggested_fixes: list[str] = Field(default_factory=list)
    risk_level: str = "unknown"
    can_advance: bool | None = False
    confidence: float = 0.0
    warnings: list[str] = Field(default_factory=list)
