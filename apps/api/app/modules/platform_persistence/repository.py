"""Durabilidade das registries de plataforma.

O que ganhou persistencia, e por que
------------------------------------

Model Registry, Asset Registry e Evaluation Plane guardam estado que NAO pode
desaparecer num restart: a evidencia que autoriza uma promocao, a versao de
prompt que estava ativa, e o registro que sustenta as duas. Perder isso
significaria promover de novo sem saber que ja se promoveu.

O que continua em memoria, tambem por escolha
---------------------------------------------

Trilha de correlacao, comparacoes de shadow e amostras de SLO. As tres sao
observacao VIVA: a trilha aponta para evidencia que ja e duravel, uma
comparacao de shadow pode ser reobservada, e uma janela de SLO de antes do
restart descreveria um processo que nao existe mais. Persistir tudo cegamente
custaria escrita em todo request para responder pergunta que ninguem faz.

Padrao reaproveitado
--------------------

`Protocol` + `InMemory` + `PostgreSQL`, como no Risk Engine. `Protocol` e nao
classe base porque o servico depende da FORMA, e nao da heranca — um duble de
teste satisfaz o contrato sem herdar nada.

Fail-closed
-----------

Banco indisponivel NAO vira memoria. Se a persistencia esta ligada e o banco
nao responde, a chamada falha: um registry que caisse para memoria em silencio
perderia promocao sem avisar, que e o modo de falha que esta camada existe para
impedir.
"""

from __future__ import annotations

import json
import os
import uuid
from typing import Protocol, runtime_checkable

import psycopg

from app.core.env_compat import AmbiguityPolicy, resolve
from app.modules.asset_registry.schemas import AssetVersion
from app.modules.evaluation_plane.schemas import (
    EvaluationMetric,
    EvaluationRecord,
    EvaluationSubject,
)
from app.modules.model_registry.schemas import ModelEntry, ModelTransition

FLAG_PLATFORM_PERSISTENCE = "VELTRIX_PLATFORM_PERSISTENCE"
FLAG_PLATFORM_DATABASE_URL = "VELTRIX_PLATFORM_DATABASE_URL"

VALID_MODES = ("off", "memory", "postgresql")


class PlatformRepositoryError(RuntimeError):
    """Falha da persistencia de plataforma. Nunca silenciosa."""


class PlatformRepositoryConfigurationError(PlatformRepositoryError):
    """Configuracao invalida. Falha na construcao, nao no primeiro uso."""


@runtime_checkable
class PlatformRepository(Protocol):
    """A forma que os tres servicos esperam de um store."""

    def save_model(self, entry: ModelEntry) -> None: ...

    def load_models(self) -> list[ModelEntry]: ...

    def save_transition(self, transition: ModelTransition) -> None: ...

    def load_transitions(self) -> list[ModelTransition]: ...

    def save_asset_version(self, version: AssetVersion) -> None: ...

    def load_asset_versions(self) -> list[AssetVersion]: ...

    def save_evaluation(self, record: EvaluationRecord) -> None: ...

    def load_evaluations(self) -> list[EvaluationRecord]: ...

    def clear(self) -> None: ...


class InMemoryPlatformRepository:
    """Store em memoria. Default, e o que os testes usam."""

    def __init__(self) -> None:
        self._models: dict[str, ModelEntry] = {}
        self._transitions: list[ModelTransition] = []
        self._assets: dict[tuple[str, int], AssetVersion] = {}
        self._evaluations: dict[tuple[str, str], EvaluationRecord] = {}

    def save_model(self, entry: ModelEntry) -> None:
        self._models[entry.model_key] = entry

    def load_models(self) -> list[ModelEntry]:
        return sorted(self._models.values(), key=lambda item: item.model_key)

    def save_transition(self, transition: ModelTransition) -> None:
        self._transitions.append(transition)

    def load_transitions(self) -> list[ModelTransition]:
        return list(self._transitions)

    def save_asset_version(self, version: AssetVersion) -> None:
        self._assets[(version.asset_id, version.version)] = version

    def load_asset_versions(self) -> list[AssetVersion]:
        return sorted(self._assets.values(), key=lambda i: (i.asset_id, i.version))

    def save_evaluation(self, record: EvaluationRecord) -> None:
        self._evaluations[(record.project_id, record.evaluation_id)] = record

    def load_evaluations(self) -> list[EvaluationRecord]:
        return sorted(self._evaluations.values(), key=lambda i: i.evaluation_id)

    def clear(self) -> None:
        self._models.clear()
        self._transitions.clear()
        self._assets.clear()
        self._evaluations.clear()


def _json(value) -> str:
    return json.dumps(value, default=str)


class PostgreSQLPlatformRepository:
    """Store PostgreSQL. Idempotente por chave, isolado por projeto."""

    def __init__(self, database_url: str) -> None:
        self._database_url = database_url

    def _connect(self) -> psycopg.Connection:
        try:
            return psycopg.connect(self._database_url, connect_timeout=5)
        except psycopg.Error as error:
            raise PlatformRepositoryError(
                "Persistência de plataforma indisponível; nenhum fallback aplicado."
            ) from error

    # --- modelos ----------------------------------------------------------

    def save_model(self, entry: ModelEntry) -> None:
        # `ON CONFLICT DO UPDATE` porque o estado do modelo EVOLUI: o registro
        # e o estado corrente, e a historia mora na tabela de transicoes.
        sql = """
        INSERT INTO pedrocore_model_entries (
            model_key, provider, model_name, model_version, registry_version,
            status, capabilities, evaluation_ids, compatible_asset_ids,
            compatible_policy_version, created_at, promoted_at, rejected_at,
            rolled_back_at, notes
        ) VALUES (
            %(model_key)s, %(provider)s, %(model_name)s, %(model_version)s,
            %(registry_version)s, %(status)s, %(capabilities)s,
            %(evaluation_ids)s, %(compatible_asset_ids)s,
            %(compatible_policy_version)s, %(created_at)s, %(promoted_at)s,
            %(rejected_at)s, %(rolled_back_at)s, %(notes)s
        )
        ON CONFLICT (model_key) DO UPDATE SET
            status = EXCLUDED.status,
            evaluation_ids = EXCLUDED.evaluation_ids,
            compatible_asset_ids = EXCLUDED.compatible_asset_ids,
            compatible_policy_version = EXCLUDED.compatible_policy_version,
            promoted_at = EXCLUDED.promoted_at,
            rejected_at = EXCLUDED.rejected_at,
            rolled_back_at = EXCLUDED.rolled_back_at,
            notes = EXCLUDED.notes
        """
        with self._connect() as connection:
            connection.execute(
                sql,
                {
                    "model_key": entry.model_key,
                    "provider": entry.provider,
                    "model_name": entry.model_name,
                    "model_version": entry.model_version,
                    "registry_version": entry.registry_version,
                    "status": entry.status.value,
                    "capabilities": _json([i.value for i in entry.capabilities]),
                    "evaluation_ids": _json(list(entry.evaluation_ids)),
                    "compatible_asset_ids": _json(list(entry.compatible_asset_ids)),
                    "compatible_policy_version": entry.compatible_policy_version,
                    "created_at": entry.created_at,
                    "promoted_at": entry.promoted_at,
                    "rejected_at": entry.rejected_at,
                    "rolled_back_at": entry.rolled_back_at,
                    "notes": entry.notes,
                },
            )

    def load_models(self) -> list[ModelEntry]:
        sql = """
        SELECT model_key, provider, model_name, model_version, registry_version,
               status, capabilities, evaluation_ids, compatible_asset_ids,
               compatible_policy_version, created_at, promoted_at, rejected_at,
               rolled_back_at, notes
        FROM pedrocore_model_entries ORDER BY model_key
        """
        with self._connect() as connection:
            linhas = connection.execute(sql).fetchall()
        return [
            ModelEntry(
                model_key=r[0],
                provider=r[1],
                model_name=r[2],
                model_version=r[3],
                registry_version=r[4],
                status=r[5],
                capabilities=tuple(r[6] or ()),
                evaluation_ids=tuple(r[7] or ()),
                compatible_asset_ids=tuple(r[8] or ()),
                compatible_policy_version=r[9],
                created_at=r[10],
                promoted_at=r[11],
                rejected_at=r[12],
                rolled_back_at=r[13],
                notes=r[14],
            )
            for r in linhas
        ]

    def save_transition(self, transition: ModelTransition) -> None:
        sql = """
        INSERT INTO pedrocore_model_transitions (
            transition_id, model_key, from_status, to_status, reason,
            evaluation_id, actor, occurred_at
        ) VALUES (
            %(transition_id)s, %(model_key)s, %(from_status)s, %(to_status)s,
            %(reason)s, %(evaluation_id)s, %(actor)s, %(occurred_at)s
        )
        ON CONFLICT (transition_id) DO NOTHING
        """
        with self._connect() as connection:
            connection.execute(
                sql,
                {
                    # Transicao e um FATO: dois avancos iguais em instantes
                    # diferentes sao dois fatos, e por isso o id e novo.
                    "transition_id": f"transition_{uuid.uuid4().hex[:24]}",
                    "model_key": transition.model_key,
                    "from_status": transition.from_status.value,
                    "to_status": transition.to_status.value,
                    "reason": transition.reason,
                    "evaluation_id": transition.evaluation_id,
                    "actor": transition.actor,
                    "occurred_at": transition.occurred_at,
                },
            )

    def load_transitions(self) -> list[ModelTransition]:
        sql = """
        SELECT model_key, from_status, to_status, reason, evaluation_id,
               actor, occurred_at
        FROM pedrocore_model_transitions ORDER BY occurred_at, model_key
        """
        with self._connect() as connection:
            linhas = connection.execute(sql).fetchall()
        return [
            ModelTransition(
                model_key=r[0],
                from_status=r[1],
                to_status=r[2],
                reason=r[3],
                evaluation_id=r[4],
                actor=r[5],
                occurred_at=r[6],
            )
            for r in linhas
        ]

    # --- assets -----------------------------------------------------------

    def save_asset_version(self, version: AssetVersion) -> None:
        sql = """
        INSERT INTO pedrocore_asset_versions (
            asset_id, version, registry_version, kind, status, content,
            content_hash, provenance, author, change_reason, created_at,
            compatible_policy_version, compatible_contract_versions
        ) VALUES (
            %(asset_id)s, %(version)s, %(registry_version)s, %(kind)s,
            %(status)s, %(content)s, %(content_hash)s, %(provenance)s,
            %(author)s, %(change_reason)s, %(created_at)s,
            %(compatible_policy_version)s, %(compatible_contract_versions)s
        )
        ON CONFLICT (asset_id, version) DO UPDATE SET status = EXCLUDED.status
        """
        with self._connect() as connection:
            connection.execute(
                sql,
                {
                    "asset_id": version.asset_id,
                    "version": version.version,
                    "registry_version": version.registry_version,
                    "kind": version.kind.value,
                    "status": version.status.value,
                    "content": version.content,
                    "content_hash": version.content_hash,
                    "provenance": version.provenance,
                    "author": version.author,
                    "change_reason": version.change_reason,
                    "created_at": version.created_at,
                    "compatible_policy_version": version.compatible_policy_version,
                    "compatible_contract_versions": _json(
                        list(version.compatible_contract_versions)
                    ),
                },
            )

    def load_asset_versions(self) -> list[AssetVersion]:
        sql = """
        SELECT asset_id, version, registry_version, kind, status, content,
               content_hash, provenance, author, change_reason, created_at,
               compatible_policy_version, compatible_contract_versions
        FROM pedrocore_asset_versions ORDER BY asset_id, version
        """
        with self._connect() as connection:
            linhas = connection.execute(sql).fetchall()
        return [
            AssetVersion(
                asset_id=r[0],
                version=r[1],
                registry_version=r[2],
                kind=r[3],
                status=r[4],
                content=r[5],
                content_hash=r[6],
                provenance=r[7],
                author=r[8],
                change_reason=r[9],
                created_at=r[10],
                compatible_policy_version=r[11],
                compatible_contract_versions=tuple(r[12] or ()),
            )
            for r in linhas
        ]

    # --- avaliacoes -------------------------------------------------------

    def save_evaluation(self, record: EvaluationRecord) -> None:
        sql = """
        INSERT INTO pedrocore_evaluation_records (
            evaluation_id, project_id, plane_version, subject_kind, subject_id,
            subject_version, suite, suite_version, dataset_id, dataset_slice,
            environment, producer, status, metrics, reason_codes, evidence_ids,
            correlation_id, evaluated_at
        ) VALUES (
            %(evaluation_id)s, %(project_id)s, %(plane_version)s,
            %(subject_kind)s, %(subject_id)s, %(subject_version)s, %(suite)s,
            %(suite_version)s, %(dataset_id)s, %(dataset_slice)s,
            %(environment)s, %(producer)s, %(status)s, %(metrics)s,
            %(reason_codes)s, %(evidence_ids)s, %(correlation_id)s,
            %(evaluated_at)s
        )
        ON CONFLICT (project_id, evaluation_id) DO NOTHING
        """
        with self._connect() as connection:
            connection.execute(
                sql,
                {
                    "evaluation_id": record.evaluation_id,
                    "project_id": record.project_id,
                    "plane_version": record.plane_version,
                    "subject_kind": record.subject.kind.value,
                    "subject_id": record.subject.subject_id,
                    "subject_version": record.subject.subject_version,
                    "suite": record.suite,
                    "suite_version": record.suite_version,
                    "dataset_id": record.dataset_id,
                    "dataset_slice": record.dataset_slice,
                    "environment": record.environment,
                    "producer": record.producer,
                    "status": record.status.value,
                    "metrics": _json(
                        [item.model_dump(mode="json") for item in record.metrics]
                    ),
                    "reason_codes": _json(list(record.reason_codes)),
                    "evidence_ids": _json(list(record.evidence_ids)),
                    "correlation_id": record.correlation_id,
                    "evaluated_at": record.evaluated_at,
                },
            )

    def load_evaluations(self) -> list[EvaluationRecord]:
        sql = """
        SELECT evaluation_id, project_id, plane_version, subject_kind,
               subject_id, subject_version, suite, suite_version, dataset_id,
               dataset_slice, environment, producer, status, metrics,
               reason_codes, evidence_ids, correlation_id, evaluated_at
        FROM pedrocore_evaluation_records ORDER BY evaluation_id
        """
        with self._connect() as connection:
            linhas = connection.execute(sql).fetchall()
        return [
            EvaluationRecord(
                evaluation_id=r[0],
                project_id=r[1],
                plane_version=r[2],
                subject=EvaluationSubject(
                    kind=r[3], subject_id=r[4], subject_version=r[5]
                ),
                suite=r[6],
                suite_version=r[7],
                dataset_id=r[8],
                dataset_slice=r[9],
                environment=r[10],
                producer=r[11],
                status=r[12],
                metrics=tuple(EvaluationMetric(**item) for item in (r[13] or ())),
                reason_codes=tuple(r[14] or ()),
                evidence_ids=tuple(r[15] or ()),
                correlation_id=r[16],
                evaluated_at=r[17],
            )
            for r in linhas
        ]

    def clear(self) -> None:
        with self._connect() as connection:
            for tabela in (
                "pedrocore_model_transitions",
                "pedrocore_model_entries",
                "pedrocore_asset_versions",
                "pedrocore_evaluation_records",
            ):
                connection.execute(f"DELETE FROM {tabela}")


# --- fabrica ---------------------------------------------------------------


def platform_persistence_mode() -> str:
    """Modo declarado. Valor invalido falha; ele nao vira `off` em silencio."""
    modo = (resolve(FLAG_PLATFORM_PERSISTENCE, default="off") or "off").lower()
    if modo not in VALID_MODES:
        raise PlatformRepositoryConfigurationError(
            f"{FLAG_PLATFORM_PERSISTENCE} inválido: {modo!r}. "
            f"Use um de: {', '.join(VALID_MODES)}."
        )
    return modo


def build_platform_repository() -> PlatformRepository | None:
    """Constroi o store do modo declarado. `off` devolve `None`."""
    modo = platform_persistence_mode()
    if modo == "off":
        return None
    if modo == "memory":
        return InMemoryPlatformRepository()

    url = resolve(
        FLAG_PLATFORM_DATABASE_URL, policy=AmbiguityPolicy.FAIL
    ) or (os.environ.get("PEDROCORE_TEST_POSTGRES_URL") or "").strip()
    if not url:
        raise PlatformRepositoryConfigurationError(
            f"{FLAG_PLATFORM_PERSISTENCE}=postgresql exige "
            f"{FLAG_PLATFORM_DATABASE_URL}. Sem URL não há persistência, e "
            "cair para memória em silêncio perderia promoção sem avisar."
        )
    return PostgreSQLPlatformRepository(url)


def platform_persistence_is_durable() -> bool:
    return platform_persistence_mode() == "postgresql"
