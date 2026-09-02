"""Outbox local com retry, backoff e dead-letter.

O problema que isto resolve
---------------------------

Se um consumidor chama o Veltrix de dentro do seu fluxo principal, o Veltrix
vira Single Point of Failure dele: Veltrix fora do ar, funcionalidade do
consumidor fora do ar. Isso e inaceitavel, e nenhuma quantidade de uptime
resolve — o acoplamento e de desenho, nao de disponibilidade.

O outbox quebra esse acoplamento. O consumidor GRAVA localmente o que quer
enviar (operacao rapida, local, sob a transacao dele) e um processo separado
entrega depois. Se o Veltrix estiver fora, a entrega espera; o fluxo do
consumidor ja terminou.

Por que aqui e nao um broker
-----------------------------

Um broker resolveria o mesmo problema e traria fila, deploy, autenticacao entre
servicos, observabilidade distribuida e mais um componente para ficar fora do
ar. Persistencia local resolve o caso real — entrega eventual de eventos
pequenos e idempotentes — sem nenhum desses custos. Era a resposta certa antes
de ser a mais barata.

Esta implementacao e uma REFERENCIA, sem dependencia de rede: o transporte e
injetado. O Veltrix a usa para os proprios envios e a documenta para que
consumidores nao precisem inventar a deles — cada um inventando a sua e como se
tem cinco bugs de duplicacao diferentes.

Garantia oferecida
------------------

Entrega **at-least-once** com deduplicacao no servidor. Nao existe exactly-once
em sistema distribuido; o par honesto e "reenvie a vontade" mais uma chave de
idempotencia que faz o reenvio ser reconhecido em vez de duplicado. E o que a
Era 4 implementou do outro lado.
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

ShortText = Annotated[str, Field(min_length=1, max_length=128)]

DEFAULT_MAX_ATTEMPTS = 5
DEFAULT_BASE_DELAY_SECONDS = 2.0
DEFAULT_MAX_DELAY_SECONDS = 300.0


class DeliveryState(str, Enum):
    """Onde uma entrega esta.

    `DEAD_LETTER` nao e "perdido": e "parou de tentar e precisa de gente". A
    diferenca importa — um item que some nao gera alarme, e um item em
    dead-letter e uma pergunta esperando resposta.
    """

    PENDING = "pending"
    IN_FLIGHT = "in_flight"
    DELIVERED = "delivered"
    DEAD_LETTER = "dead_letter"


class DeliveryOutcome(str, Enum):
    """O que o transporte relatou.

    A distincao entre `RETRYABLE` e `PERMANENT` e a decisao mais importante do
    modulo. Reenviar indefinidamente um payload que o servidor recusa por
    contrato invalido nao conserta nada e transforma um erro do consumidor em
    carga permanente no servidor.
    """

    DELIVERED = "delivered"
    DUPLICATE = "duplicate"
    RETRYABLE = "retryable"
    PERMANENT = "permanent"


class OutboxEntry(BaseModel):
    """Um envio pendente, com todo o estado necessario para retomar."""

    model_config = ConfigDict(extra="forbid")

    entry_id: ShortText
    project_id: ShortText
    # A chave que faz o reenvio ser RECONHECIDO em vez de duplicado. Escolhida
    # uma vez, na gravacao, e nunca regerada: regerar por tentativa produziria
    # uma duplicata a cada retry, que e o oposto do objetivo.
    idempotency_key: ShortText
    payload: dict
    state: DeliveryState = DeliveryState.PENDING
    attempts: int = Field(default=0, ge=0)
    max_attempts: int = Field(default=DEFAULT_MAX_ATTEMPTS, ge=1, le=50)
    created_at: datetime
    next_attempt_at: datetime
    last_error_code: str | None = Field(default=None, max_length=128)
    delivered_at: datetime | None = None

    @property
    def terminal(self) -> bool:
        return self.state in {DeliveryState.DELIVERED, DeliveryState.DEAD_LETTER}


def backoff_delay(
    attempts: int,
    *,
    base_seconds: float = DEFAULT_BASE_DELAY_SECONDS,
    max_seconds: float = DEFAULT_MAX_DELAY_SECONDS,
) -> float:
    """Backoff exponencial com teto.

    O teto existe porque sem ele a oitava tentativa cairia em horas: um servidor
    que voltou depois de dez minutos ficaria esperando um cliente que so tentaria
    de novo no dia seguinte.
    """
    if attempts <= 0:
        return 0.0
    return min(base_seconds * (2 ** (attempts - 1)), max_seconds)


class OutboxStore:
    """Store em memoria, seguro para uso concorrente.

    O lock protege a transicao PENDING -> IN_FLIGHT: sem ele, dois workers
    pegariam a mesma entrada e o servidor veria duas entregas simultaneas com a
    mesma chave — funcionaria, porque o servidor deduplica, mas gastaria o
    dobro e escondería o bug.
    """

    def __init__(self) -> None:
        self._entries: dict[str, OutboxEntry] = {}
        self._lock = threading.Lock()

    def enqueue(
        self,
        *,
        entry_id: str,
        project_id: str,
        idempotency_key: str,
        payload: dict,
        now: datetime | None = None,
        max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    ) -> OutboxEntry:
        moment = now or datetime.now(timezone.utc)
        with self._lock:
            existing = self._entries.get(entry_id)
            if existing is not None:
                # Gravar duas vezes o mesmo evento e replay do consumidor, nao
                # um segundo evento. Devolver o existente evita criar duas
                # entregas para o mesmo fato.
                return existing.model_copy(deep=True)
            entry = OutboxEntry(
                entry_id=entry_id,
                project_id=project_id,
                idempotency_key=idempotency_key,
                payload=payload,
                created_at=moment,
                next_attempt_at=moment,
                max_attempts=max_attempts,
            )
            self._entries[entry_id] = entry
            return entry.model_copy(deep=True)

    def get(self, entry_id: str) -> OutboxEntry | None:
        with self._lock:
            found = self._entries.get(entry_id)
            return found.model_copy(deep=True) if found else None

    def due(self, *, now: datetime | None = None) -> list[OutboxEntry]:
        """Entradas prontas para tentativa, mais antigas primeiro."""
        moment = now or datetime.now(timezone.utc)
        with self._lock:
            selected = [
                entry.model_copy(deep=True)
                for entry in self._entries.values()
                if entry.state is DeliveryState.PENDING and entry.next_attempt_at <= moment
            ]
        selected.sort(key=lambda item: (item.next_attempt_at, item.entry_id))
        return selected

    def pending_count(self) -> int:
        with self._lock:
            return sum(
                1 for entry in self._entries.values() if entry.state is DeliveryState.PENDING
            )

    def dead_letters(self) -> list[OutboxEntry]:
        with self._lock:
            return [
                entry.model_copy(deep=True)
                for entry in self._entries.values()
                if entry.state is DeliveryState.DEAD_LETTER
            ]

    def all_entries(self) -> list[OutboxEntry]:
        with self._lock:
            return [entry.model_copy(deep=True) for entry in self._entries.values()]

    def _replace(self, entry: OutboxEntry) -> None:
        with self._lock:
            self._entries[entry.entry_id] = entry.model_copy(deep=True)

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()


# O transporte recebe a entrada e devolve `(resultado, codigo de erro)`.
Transport = Callable[[OutboxEntry], tuple[DeliveryOutcome, str | None]]


class OutboxDispatcher:
    """Entrega as entradas devidas, aplicando backoff e dead-letter."""

    def __init__(self, store: OutboxStore) -> None:
        self._store = store

    def dispatch_once(
        self,
        transport: Transport,
        *,
        now: datetime | None = None,
    ) -> list[OutboxEntry]:
        """Uma passada. Devolve o estado final de cada entrada tentada.

        Uma passada, e nao um laco infinito: quem decide a cadencia e o
        agendador do consumidor. Um laco aqui esconderia o custo real da
        entrega dentro de uma chamada que parece barata.
        """
        moment = now or datetime.now(timezone.utc)
        results: list[OutboxEntry] = []

        for entry in self._store.due(now=moment):
            attempted = entry.model_copy(
                update={"state": DeliveryState.IN_FLIGHT, "attempts": entry.attempts + 1}
            )
            self._store._replace(attempted)  # noqa: SLF001 — mesmo modulo

            try:
                outcome, error_code = transport(attempted)
            except Exception as error:  # noqa: BLE001 — transporte e codigo de terceiro
                # Excecao do transporte e falha de entrega, nao do processo:
                # deixar propagar derrubaria o worker e travaria a fila inteira
                # por causa de uma unica entrada.
                outcome, error_code = DeliveryOutcome.RETRYABLE, type(error).__name__

            results.append(self._apply(attempted, outcome, error_code, moment))

        return results

    def _apply(
        self,
        entry: OutboxEntry,
        outcome: DeliveryOutcome,
        error_code: str | None,
        moment: datetime,
    ) -> OutboxEntry:
        if outcome in {DeliveryOutcome.DELIVERED, DeliveryOutcome.DUPLICATE}:
            # Duplicata e SUCESSO: o servidor confirmou que ja tem o fato.
            # Tratar como falha faria o consumidor reenviar para sempre algo
            # que ja chegou.
            updated = entry.model_copy(
                update={
                    "state": DeliveryState.DELIVERED,
                    "delivered_at": moment,
                    "last_error_code": None,
                }
            )
        elif outcome is DeliveryOutcome.PERMANENT:
            # Recusa definitiva: reenviar nao conserta contrato invalido.
            updated = entry.model_copy(
                update={
                    "state": DeliveryState.DEAD_LETTER,
                    "last_error_code": error_code,
                }
            )
        elif entry.attempts >= entry.max_attempts:
            updated = entry.model_copy(
                update={
                    "state": DeliveryState.DEAD_LETTER,
                    "last_error_code": error_code or "MAX_ATTEMPTS_EXCEEDED",
                }
            )
        else:
            updated = entry.model_copy(
                update={
                    "state": DeliveryState.PENDING,
                    "last_error_code": error_code,
                    "next_attempt_at": moment
                    + timedelta(seconds=backoff_delay(entry.attempts)),
                }
            )
        self._store._replace(updated)  # noqa: SLF001 — mesmo modulo
        return updated

    def requeue_dead_letter(
        self, entry_id: str, *, now: datetime | None = None
    ) -> OutboxEntry | None:
        """Devolve uma entrada de dead-letter a fila, apos revisao humana.

        Zera as tentativas de proposito: a entrada volta porque alguem OLHOU e
        corrigiu a causa. Manter o contador puniria a correcao com um
        dead-letter imediato.
        """
        entry = self._store.get(entry_id)
        if entry is None or entry.state is not DeliveryState.DEAD_LETTER:
            return None
        moment = now or datetime.now(timezone.utc)
        updated = entry.model_copy(
            update={
                "state": DeliveryState.PENDING,
                "attempts": 0,
                "next_attempt_at": moment,
                "last_error_code": None,
            }
        )
        self._store._replace(updated)  # noqa: SLF001 — mesmo modulo
        return updated
