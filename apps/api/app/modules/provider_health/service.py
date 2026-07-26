"""Circuit breaker local, determinístico e sem health check externo.

O estado é somente em memória e coordenado por processo. Múltiplos workers ou
instâncias não compartilham circuito; essa limitação é deliberadamente
explícita e não deve ser apresentada como coordenação distribuída.
"""

from __future__ import annotations

import os
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass

from app.modules.provider_health.schemas import (
    CircuitKey,
    CircuitPermit,
    CircuitSnapshot,
    CircuitState,
    FailureClassification,
)

FLAG_CIRCUIT_ENABLED = "PEDROCORE_CIRCUIT_BREAKER_ENABLED"
FLAG_FAILURE_THRESHOLD = "PEDROCORE_CIRCUIT_FAILURE_THRESHOLD"
FLAG_COOLDOWN_SECONDS = "PEDROCORE_CIRCUIT_COOLDOWN_SECONDS"

DEFAULT_FAILURE_THRESHOLD = 3
DEFAULT_COOLDOWN_SECONDS = 30.0

CIRCUIT_OPEN_REASON = "Circuito aberto; candidato eliminado sem chamar adapter."
HALF_OPEN_BUSY_REASON = (
    "Circuito half-open já possui uma tentativa de prova em andamento."
)


class ProviderCircuitOpenError(Exception):
    """Tentativa recusada antes do adapter pelo estado do circuito."""


@dataclass
class _CircuitRecord:
    state: CircuitState = CircuitState.CLOSED
    consecutive_failures: int = 0
    opened_at_monotonic: float | None = None
    half_open_probe_in_flight: bool = False


def _flag_true(name: str) -> bool:
    return (os.environ.get(name) or "").strip().lower() == "true"


def _bounded_int(name: str, default: int, minimum: int, maximum: int) -> int:
    raw = (os.environ.get(name) or "").strip()
    try:
        value = int(raw) if raw else default
    except ValueError:
        return default
    return min(maximum, max(minimum, value))


def _bounded_float(
    name: str,
    default: float,
    minimum: float,
    maximum: float,
) -> float:
    raw = (os.environ.get(name) or "").strip()
    try:
        value = float(raw) if raw else default
    except ValueError:
        return default
    return min(maximum, max(minimum, value))


class ProviderHealthService:
    """State machine closed/open/half-open protegida por lock de processo."""

    def __init__(self, clock: Callable[[], float] = time.monotonic) -> None:
        self._clock = clock
        self._records: dict[CircuitKey, _CircuitRecord] = {}
        self._lock = threading.RLock()

    def enabled(self) -> bool:
        return _flag_true(FLAG_CIRCUIT_ENABLED)

    def failure_threshold(self) -> int:
        return _bounded_int(
            FLAG_FAILURE_THRESHOLD,
            DEFAULT_FAILURE_THRESHOLD,
            minimum=1,
            maximum=100,
        )

    def cooldown_seconds(self) -> float:
        return _bounded_float(
            FLAG_COOLDOWN_SECONDS,
            DEFAULT_COOLDOWN_SECONDS,
            minimum=0.01,
            maximum=86_400.0,
        )

    @staticmethod
    def key(environment: str, provider_id: str, model_id: str) -> CircuitKey:
        return CircuitKey(
            environment=(environment or "unknown").strip().lower(),
            provider_id=(provider_id or "").strip().lower(),
            model_id=(model_id or "").strip(),
        )

    def reset(self) -> None:
        """Limpeza interna usada por testes; não existe endpoint administrativo."""
        with self._lock:
            self._records.clear()

    def peek(self, key: CircuitKey) -> CircuitSnapshot:
        """Consulta sem transição e sem reservar probe half-open."""
        with self._lock:
            record = self._records.get(key, _CircuitRecord())
            return self._snapshot(key, record, mutate_for_cooldown=False)

    def acquire(self, key: CircuitKey) -> CircuitPermit:
        """Reserva atomicamente uma tentativa, inclusive o único probe."""
        if not self.enabled():
            return CircuitPermit(
                allowed=True,
                snapshot=self._snapshot(key, _CircuitRecord(), enabled=False),
            )

        with self._lock:
            record = self._records.setdefault(key, _CircuitRecord())
            self._promote_after_cooldown(record)

            if record.state is CircuitState.OPEN:
                return CircuitPermit(
                    allowed=False,
                    reason=CIRCUIT_OPEN_REASON,
                    snapshot=self._snapshot(key, record),
                )

            if record.state is CircuitState.HALF_OPEN:
                if record.half_open_probe_in_flight:
                    return CircuitPermit(
                        allowed=False,
                        reason=HALF_OPEN_BUSY_REASON,
                        snapshot=self._snapshot(key, record),
                    )
                record.half_open_probe_in_flight = True
                return CircuitPermit(
                    allowed=True,
                    half_open_probe=True,
                    snapshot=self._snapshot(key, record),
                )

            return CircuitPermit(
                allowed=True,
                snapshot=self._snapshot(key, record),
            )

    def record(
        self,
        key: CircuitKey,
        classification: FailureClassification,
        *,
        half_open_probe: bool = False,
    ) -> CircuitSnapshot:
        """Aplica somente evidência atribuível ao provider.

        Caller/policy/configuração/modelo inválido não contaminam health.
        Timeout ambíguo abre imediatamente para impedir nova chamada enquanto
        a conclusão externa não é conhecida.
        """
        if not self.enabled():
            return self._snapshot(key, _CircuitRecord(), enabled=False)

        with self._lock:
            record = self._records.setdefault(key, _CircuitRecord())

            if classification is FailureClassification.SUCCESS:
                self._close(record)
                return self._snapshot(key, record)

            if half_open_probe:
                # Qualquer probe sem sucesso volta a abrir. Mesmo erro interno
                # não constitui evidência suficiente para fechar o circuito.
                self._open(record)
                return self._snapshot(key, record)

            if classification is FailureClassification.COMPLETION_AMBIGUOUS:
                record.consecutive_failures += 1
                self._open(record)
            elif classification is FailureClassification.PROVIDER_RETRYABLE:
                record.consecutive_failures += 1
                if record.consecutive_failures >= self.failure_threshold():
                    self._open(record)
            # provider_non_retryable/pre_dispatch, caller, policy e internal
            # são registrados na tentativa, mas não degradam o circuito.

            return self._snapshot(key, record)

    def _promote_after_cooldown(self, record: _CircuitRecord) -> None:
        if record.state is not CircuitState.OPEN:
            return
        if record.opened_at_monotonic is None:
            return
        if self._clock() - record.opened_at_monotonic >= self.cooldown_seconds():
            record.state = CircuitState.HALF_OPEN
            record.half_open_probe_in_flight = False

    def _snapshot(
        self,
        key: CircuitKey,
        record: _CircuitRecord,
        *,
        enabled: bool | None = None,
        mutate_for_cooldown: bool = False,
    ) -> CircuitSnapshot:
        if mutate_for_cooldown:
            self._promote_after_cooldown(record)
        effective_enabled = self.enabled() if enabled is None else enabled
        state = record.state
        remaining = 0.0
        if state is CircuitState.OPEN and record.opened_at_monotonic is not None:
            remaining = max(
                0.0,
                self.cooldown_seconds()
                - (self._clock() - record.opened_at_monotonic),
            )
            if remaining == 0.0:
                # Peek mostra disponibilidade half-open sem reservar o probe.
                state = CircuitState.HALF_OPEN
        return CircuitSnapshot(
            key=key,
            enabled=effective_enabled,
            state=state,
            consecutive_failures=record.consecutive_failures,
            opened_at_monotonic=record.opened_at_monotonic,
            cooldown_remaining_seconds=round(remaining, 6),
            half_open_probe_in_flight=record.half_open_probe_in_flight,
        )

    def _open(self, record: _CircuitRecord) -> None:
        record.state = CircuitState.OPEN
        record.opened_at_monotonic = self._clock()
        record.half_open_probe_in_flight = False

    @staticmethod
    def _close(record: _CircuitRecord) -> None:
        record.state = CircuitState.CLOSED
        record.consecutive_failures = 0
        record.opened_at_monotonic = None
        record.half_open_probe_in_flight = False


provider_health_service = ProviderHealthService()
