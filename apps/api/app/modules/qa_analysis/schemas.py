from pydantic import BaseModel, Field


class QATextAnalysisResult(BaseModel):
    analyzed: bool = False
    status: str = "not_analyzed"
    summary: str = ""
    detected_successes: list[str] = Field(default_factory=list)
    detected_failures: list[str] = Field(default_factory=list)
    detected_errors: list[str] = Field(default_factory=list)
    detected_warnings: list[str] = Field(default_factory=list)
    detected_critical: list[str] = Field(default_factory=list)
    findings: list[str] = Field(default_factory=list)
    failures: list[str] = Field(default_factory=list)
    probable_causes: list[str] = Field(default_factory=list)
    suggested_commands: list[str] = Field(default_factory=list)
    suggested_fixes: list[str] = Field(default_factory=list)
    risk_level: str = "medium"
    can_advance: bool = False
    confidence: float = 0.0
    warnings: list[str] = Field(default_factory=list)
    warning_codes: list[str] = Field(default_factory=list)
