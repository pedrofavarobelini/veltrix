"""Tipos do health state e circuit breaker (Etapa 6)."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict


class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class FailureClassification(str, Enum):
    SUCCESS = "success"
    PROVIDER_RETRYABLE = "provider_retryable"
    PROVIDER_NON_RETRYABLE = "provider_non_retryable"
    # Falha comprovadamente anterior ao dispatch externo. Usada somente por
    # gates conservadores; não é inferida de texto de exception.
    PROVIDER_PRE_DISPATCH = "provider_pre_dispatch"
    COMPLETION_AMBIGUOUS = "completion_ambiguous"
    CALLER_ERROR = "caller_error"
    POLICY_ERROR = "policy_error"
    INTERNAL_ERROR = "internal_error"


class CompletionCertainty(str, Enum):
    NOT_DISPATCHED = "not_dispatched"
    COMPLETED = "completed"
    AMBIGUOUS = "ambiguous"


class CircuitKey(BaseModel):
    """Estado isolado por ambiente + provider + modelo."""

    model_config = ConfigDict(frozen=True)

    environment: str
    provider_id: str
    model_id: str


class CircuitSnapshot(BaseModel):
    model_config = ConfigDict(frozen=True)

    key: CircuitKey
    enabled: bool
    state: CircuitState
    consecutive_failures: int = 0
    opened_at_monotonic: float | None = None
    cooldown_remaining_seconds: float = 0.0
    half_open_probe_in_flight: bool = False


class CircuitPermit(BaseModel):
    model_config = ConfigDict(frozen=True)

    allowed: bool
    half_open_probe: bool = False
    reason: str | None = None
    snapshot: CircuitSnapshot
