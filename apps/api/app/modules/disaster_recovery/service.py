"""E12 — Disaster Recovery com verificacao de restauracao.

Backup nao e o produto
----------------------

Um backup que nunca foi restaurado e uma hipotese. O que esta camada entrega
nao e a copia: e a PROVA de que a copia volta — feita sobre estado descartavel,
com verificacao de integridade e com o resultado registrado.

O ciclo
-------

    backup -> destruir estado descartavel -> restaurar -> verificar

A destruicao faz parte da prova. Restaurar sobre um estado que ainda esta la
nao prova nada: o teste passaria mesmo com um backup vazio.

Ordem de restauracao importa
----------------------------

Os stores tem dependencia entre si. Restaurar fora de ordem produz um sistema
que parece de pe e referencia coisas que ainda nao existem — que e o pior modo
de falha possivel numa recuperacao, porque nao aparece de imediato.

Fail-closed
-----------

Qualquer divergencia entre o que foi salvo e o que voltou marca a restauracao
como FALHA. Nao ha restauracao parcial silenciosa: um store a menos e um
sistema incompleto que se comporta como completo.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

DISASTER_RECOVERY_VERSION = "disaster-recovery-v1"


class StoreCriticality(str, Enum):
    """O que se perde se este store nao voltar."""

    CRITICAL = "critical"
    IMPORTANT = "important"
    REBUILDABLE = "rebuildable"


class RestoreOutcome(str, Enum):
    VERIFIED = "VERIFIED"
    INTEGRITY_FAILED = "INTEGRITY_FAILED"
    INCOMPLETE = "INCOMPLETE"
    FAILED = "FAILED"


class StoreDescriptor(BaseModel):
    """Um store critico, com a posicao dele na ordem de restauracao."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    store_id: str = Field(..., min_length=1, max_length=64)
    description: str = Field(..., min_length=1, max_length=256)
    criticality: StoreCriticality
    # Menor restaura primeiro. Declarado, e nao inferido: dependencia entre
    # stores nao se descobre pelo nome.
    restore_order: int = Field(..., ge=0, le=100)
    depends_on: tuple[str, ...] = Field(default_factory=tuple)


# Mapa dos stores criticos do PedroCore. Ordem pensada: identidade e politica
# antes de tudo, porque o resto e interpretado a luz delas; outbox por ultimo,
# porque reentregar antes de o destino existir duplicaria efeito.
CRITICAL_STORES: tuple[StoreDescriptor, ...] = (
    StoreDescriptor(
        store_id="caller_identity",
        description="Credenciais registradas e vínculo de projeto.",
        criticality=StoreCriticality.CRITICAL,
        restore_order=0,
    ),
    StoreDescriptor(
        store_id="policy_assets",
        description="Assets governados: prompts e configurações versionadas.",
        criticality=StoreCriticality.CRITICAL,
        restore_order=1,
        depends_on=("caller_identity",),
    ),
    StoreDescriptor(
        store_id="postgresql",
        description="Persistência operacional, memória e histórico de risco.",
        criticality=StoreCriticality.CRITICAL,
        restore_order=2,
        depends_on=("caller_identity",),
    ),
    StoreDescriptor(
        store_id="risk_history",
        description="Análises e outcomes do Risk Engine.",
        criticality=StoreCriticality.CRITICAL,
        restore_order=3,
        depends_on=("postgresql",),
    ),
    StoreDescriptor(
        store_id="model_registry",
        description="Modelos registrados, estado e evidência de promoção.",
        criticality=StoreCriticality.IMPORTANT,
        restore_order=4,
        depends_on=("policy_assets",),
    ),
    StoreDescriptor(
        store_id="dataset_registry",
        description="Metadados de dataset e prontidão declarada.",
        criticality=StoreCriticality.IMPORTANT,
        restore_order=5,
        depends_on=("postgresql",),
    ),
    StoreDescriptor(
        store_id="evidence_records",
        description="Evidência verificável produzida por consumidores.",
        criticality=StoreCriticality.CRITICAL,
        restore_order=6,
        depends_on=("postgresql",),
    ),
    StoreDescriptor(
        store_id="audit_metadata",
        description="Metadados de auditoria e correlação.",
        criticality=StoreCriticality.IMPORTANT,
        restore_order=7,
        depends_on=("postgresql",),
    ),
    StoreDescriptor(
        store_id="outbox",
        description="Entregas pendentes. Restaurado por último de propósito.",
        criticality=StoreCriticality.CRITICAL,
        restore_order=8,
        depends_on=("postgresql", "evidence_records"),
    ),
)


class BackupManifest(BaseModel):
    """O que foi salvo, e a impressao digital de cada parte."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    backup_id: str
    dr_version: Literal["disaster-recovery-v1"] = DISASTER_RECOVERY_VERSION
    created_at: datetime
    store_digests: dict[str, str] = Field(default_factory=dict)
    store_counts: dict[str, int] = Field(default_factory=dict)
    # Declarado no manifesto: um backup de producao nunca deveria ser usado
    # como insumo de teste, e o campo torna isso conferivel.
    contains_production_data: bool = False


class RestoreVerification(BaseModel):
    """O resultado da PROVA. Sem isto, o backup e so uma hipotese."""

    model_config = ConfigDict(extra="forbid")

    backup_id: str
    dr_version: Literal["disaster-recovery-v1"] = DISASTER_RECOVERY_VERSION
    outcome: RestoreOutcome
    restored_order: list[str] = Field(default_factory=list)
    verified_stores: list[str] = Field(default_factory=list)
    mismatched_stores: list[str] = Field(default_factory=list)
    missing_stores: list[str] = Field(default_factory=list)
    reason_codes: list[str] = Field(default_factory=list)
    verified_at: datetime

    @property
    def proven(self) -> bool:
        return self.outcome is RestoreOutcome.VERIFIED


def digest_of(payload: Any) -> str:
    """Impressao digital canonica de um conteudo de store."""
    canonico = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return "sha256:" + hashlib.sha256(canonico.encode()).hexdigest()


def restore_sequence() -> list[StoreDescriptor]:
    """Ordem de restauracao, com a dependencia conferida.

    A conferencia existe porque a ordem e escrita a mao: um store cuja
    dependencia viesse DEPOIS dele passaria despercebido ate o dia do
    desastre, que e o pior dia para descobrir.
    """
    ordenados = sorted(CRITICAL_STORES, key=lambda item: item.restore_order)
    posicao = {item.store_id: item.restore_order for item in ordenados}
    for item in ordenados:
        for dependencia in item.depends_on:
            if posicao.get(dependencia, 999) >= item.restore_order:
                raise ValueError(
                    f"'{item.store_id}' depende de '{dependencia}', que restaura "
                    "depois dele; a ordem declarada está inconsistente."
                )
    return ordenados


class DisasterRecoveryService:
    """Executa o ciclo backup -> destruir -> restaurar -> verificar."""

    def backup(
        self,
        snapshots: dict[str, Any],
        *,
        backup_id: str,
        contains_production_data: bool = False,
        now: datetime | None = None,
    ) -> BackupManifest:
        """Fotografa os stores e registra a impressao digital de cada um."""
        return BackupManifest(
            backup_id=backup_id,
            created_at=now or datetime.now(timezone.utc),
            store_digests={
                nome: digest_of(conteudo) for nome, conteudo in snapshots.items()
            },
            store_counts={
                nome: len(conteudo) if hasattr(conteudo, "__len__") else 1
                for nome, conteudo in snapshots.items()
            },
            contains_production_data=contains_production_data,
        )

    def verify_restore(
        self,
        manifest: BackupManifest,
        restored: dict[str, Any],
        *,
        now: datetime | None = None,
    ) -> RestoreVerification:
        """Compara o que voltou com o que foi salvo, store a store.

        Divergencia em QUALQUER store reprova a restauracao inteira. Uma
        restauracao parcial que se declarasse bem-sucedida seria um sistema
        incompleto se comportando como completo.
        """
        instante = now or datetime.now(timezone.utc)
        conferidos: list[str] = []
        divergentes: list[str] = []
        ausentes: list[str] = []

        for nome, digest in manifest.store_digests.items():
            if nome not in restored:
                ausentes.append(nome)
            elif digest_of(restored[nome]) != digest:
                divergentes.append(nome)
            else:
                conferidos.append(nome)

        ordem = [
            item.store_id
            for item in restore_sequence()
            if item.store_id in manifest.store_digests
        ]

        if divergentes:
            resultado = RestoreOutcome.INTEGRITY_FAILED
            motivos = ["RESTORED_CONTENT_DIVERGED"]
        elif ausentes:
            resultado = RestoreOutcome.INCOMPLETE
            motivos = ["RESTORED_STORE_MISSING"]
        else:
            resultado = RestoreOutcome.VERIFIED
            motivos = ["RESTORE_VERIFIED"]

        return RestoreVerification(
            backup_id=manifest.backup_id,
            outcome=resultado,
            restored_order=ordem,
            verified_stores=sorted(conferidos),
            mismatched_stores=sorted(divergentes),
            missing_stores=sorted(ausentes),
            reason_codes=motivos,
            verified_at=instante,
        )

    def run_drill(
        self,
        snapshots: dict[str, Any],
        *,
        destroy: Callable[[], None],
        restore: Callable[[BackupManifest], dict[str, Any]],
        backup_id: str,
        now: datetime | None = None,
    ) -> RestoreVerification:
        """O ensaio completo. A destruicao faz parte da prova.

        Sem destruir, o teste passaria mesmo com um backup vazio — porque o
        estado original ainda estaria la para ser conferido.
        """
        manifesto = self.backup(snapshots, backup_id=backup_id, now=now)
        destroy()
        try:
            restaurado = restore(manifesto)
        except Exception as error:  # noqa: BLE001 - sanitizado
            return RestoreVerification(
                backup_id=backup_id,
                outcome=RestoreOutcome.FAILED,
                reason_codes=[f"RESTORE_RAISED_{type(error).__name__.upper()}"],
                missing_stores=sorted(manifesto.store_digests),
                verified_at=now or datetime.now(timezone.utc),
            )
        return self.verify_restore(manifesto, restaurado, now=now)


disaster_recovery_service = DisasterRecoveryService()
