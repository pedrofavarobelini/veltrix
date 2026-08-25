from __future__ import annotations

import asyncio
import copy
import hashlib
import json
from collections import OrderedDict
from concurrent.futures import Future
from dataclasses import dataclass
from threading import RLock
from typing import Any, Awaitable, Callable

from app.modules.chat.schemas import ChatRequest

MAX_IDEMPOTENCY_ENTRIES = 256


@dataclass(frozen=True)
class IdempotencyExecution:
    value: Any | None = None
    replayed: bool = False
    conflict: bool = False


@dataclass(frozen=True)
class _FlightCompletion:
    value: Any | None = None
    error: BaseException | None = None


@dataclass
class _CacheEntry:
    fingerprint: str
    value: Any


class ElyraIdempotencyService:
    """Idempotência volátil e bounded para a única operação textual Elyra.

    O cache não persiste payload, segredo ou credencial. A chave recebida é
    representada somente por SHA-256, e o fingerprint compara o request
    canônico sem expô-lo em audit/log.
    """

    def __init__(self) -> None:
        self._guard = RLock()
        self._cache: OrderedDict[tuple[str, str], _CacheEntry] = OrderedDict()
        self._in_flight: dict[tuple[str, str], tuple[str, Future[_FlightCompletion]]] = {}

    @staticmethod
    def request_fingerprint(payload: ChatRequest) -> str:
        encoded = json.dumps(
            payload.model_dump(mode="json"),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    @staticmethod
    def key_fingerprint(value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    async def execute(
        self,
        *,
        scope: str,
        idempotency_key: str,
        fingerprint: str,
        operation: Callable[[], Awaitable[Any]],
    ) -> IdempotencyExecution:
        cache_key = (scope, self.key_fingerprint(idempotency_key))

        with self._guard:
            cached = self._cache.get(cache_key)
            if cached is not None:
                if cached.fingerprint != fingerprint:
                    return IdempotencyExecution(conflict=True)
                self._cache.move_to_end(cache_key)
                return IdempotencyExecution(
                    value=copy.deepcopy(cached.value),
                    replayed=True,
                )

            active = self._in_flight.get(cache_key)
            if active is not None:
                active_fingerprint, future = active
                if active_fingerprint != fingerprint:
                    return IdempotencyExecution(conflict=True)
                owner = False
            else:
                future = Future()
                self._in_flight[cache_key] = (fingerprint, future)
                owner = True

        if not owner:
            completion = await asyncio.wrap_future(future)
            if completion.error is not None:
                raise completion.error
            return IdempotencyExecution(
                value=copy.deepcopy(completion.value),
                replayed=True,
            )

        try:
            value = await operation()
        except BaseException as exc:
            with self._guard:
                self._in_flight.pop(cache_key, None)
                future.set_result(_FlightCompletion(error=exc))
            raise

        with self._guard:
            self._cache[cache_key] = _CacheEntry(
                fingerprint=fingerprint,
                value=copy.deepcopy(value),
            )
            self._cache.move_to_end(cache_key)
            while len(self._cache) > MAX_IDEMPOTENCY_ENTRIES:
                self._cache.popitem(last=False)
            self._in_flight.pop(cache_key, None)
            future.set_result(_FlightCompletion(value=copy.deepcopy(value)))

        return IdempotencyExecution(value=value)

    def clear(self) -> None:
        with self._guard:
            self._cache.clear()
            self._in_flight.clear()


elyra_idempotency_service = ElyraIdempotencyService()
