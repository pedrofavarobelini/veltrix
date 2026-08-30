"""Reconciliacao: o consumidor pergunta o que realmente chegou.

Por que retry nao basta
-----------------------

O retry resolve o caso em que a resposta nao chegou mas a entrega talvez sim.
O que ele nao resolve e a duvida DEPOIS: o consumidor caiu no meio do envio,
voltou, e nao sabe quais dos seus eventos o servidor tem. Sem uma forma de
perguntar, ele so tem duas saidas ruins — reenviar tudo (caro) ou nao reenviar
nada (perde dado).

A reconciliacao e a terceira saida: o consumidor manda as chaves de
idempotencia que acha que enviou e o PedroCore responde quais ja possui. O que
faltar, ele reenvia; o que existir, ele marca como entregue.

Isto e uma consulta de LEITURA. Ela nao registra, nao promove e nao altera
nada — perguntar "voce tem isto?" nunca pode ser a forma de fazer o servidor
passar a ter.
"""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

ShortText = Annotated[str, Field(min_length=1, max_length=128)]

# Um lote grande transformaria a reconciliacao em varredura do registro.
MAX_RECONCILIATION_KEYS = 200


class ReconciliationRequest(BaseModel):
    """Chaves que o consumidor acredita ter enviado."""

    model_config = ConfigDict(extra="forbid")

    idempotency_keys: list[ShortText] = Field(
        ..., min_length=1, max_length=MAX_RECONCILIATION_KEYS
    )


class ReconciliationEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    idempotency_key: ShortText
    known: bool
    evidence_record_id: str | None = None
    fingerprint: str | None = None


class ReconciliationReport(BaseModel):
    """O que o servidor tem e o que falta.

    `missing_keys` e a lista de acao do consumidor: exatamente o que ele deve
    reenviar, nem mais nem menos.
    """

    model_config = ConfigDict(extra="forbid")

    status: str = "ok"
    project_id: ShortText
    requested: int
    known: int
    missing: int
    entries: list[ReconciliationEntry] = Field(default_factory=list)
    missing_keys: list[str] = Field(default_factory=list)


class ReconciliationService:
    """Compara as chaves do consumidor com o Evidence Registry."""

    def reconcile(
        self, project_id: str, request: ReconciliationRequest
    ) -> ReconciliationReport:
        # Import tardio: a reconciliacao e utilitaria e nao deve fazer o modulo
        # de resiliencia depender da ingestao no carregamento.
        from app.modules.evidence_platform.service import evidence_ingestion_service

        repository = evidence_ingestion_service._required_repository()  # noqa: SLF001
        normalized = (project_id or "").strip().lower()

        entries: list[ReconciliationEntry] = []
        missing: list[str] = []
        # Chaves repetidas no pedido sao respondidas uma vez: o consumidor
        # perguntou duas vezes a mesma coisa, e nao sobre duas coisas.
        for key in dict.fromkeys(request.idempotency_keys):
            found = repository.find_by_idempotency_key(normalized, key)
            if found is None:
                missing.append(key)
                entries.append(ReconciliationEntry(idempotency_key=key, known=False))
                continue
            entries.append(
                ReconciliationEntry(
                    idempotency_key=key,
                    known=True,
                    evidence_record_id=found.evidence_record_id,
                    fingerprint=found.fingerprint,
                )
            )

        return ReconciliationReport(
            project_id=normalized,
            requested=len(entries),
            known=len(entries) - len(missing),
            missing=len(missing),
            entries=entries,
            missing_keys=missing,
        )


reconciliation_service = ReconciliationService()
