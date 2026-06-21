from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    mode: str = "tecnico"
    provider: str = "mock"
    model: str | None = None
    system_prompt: str | None = None


class ChatResponse(BaseModel):
    answer: str
    provider: str
    model: str
    mode: str
    requested_provider: str
    fallback_used: bool = False
    error: str | None = None


class ProviderInfo(BaseModel):
    name: str
    label: str
    default_model: str
    configured: bool
    real_provider: bool
