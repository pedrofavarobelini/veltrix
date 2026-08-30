"""Dataset Registry — governanca e materializacao.

A regra que sustenta a Era 7
-----------------------------

Definir um dataset e livre. Materializar exige readiness real.

Nao existe caminho neste modulo que produza um dataset a partir de uma
definicao bem escrita. A unica forma de materializar e existir populacao
autorizada suficiente, verificada pela mesma politica de readiness que ja
governa o Learning Plane — nao por uma segunda regra mais permissiva criada
aqui.

`DATASET_NOT_READY` e o resultado esperado e correto enquanto nao houver dado
real. Abaixar threshold para obter um PASS seria fabricar o resultado que a
governanca existe para impedir.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone

from app.modules.caller_identity.schemas import AuthenticatedCallerContext
from app.modules.dataset_registry.repository import (
    DatasetRegistryRepository,
    InMemoryDatasetRegistryRepository,
)
from app.modules.dataset_registry.schemas import (
    DatasetDefinition,
    DatasetLineageEntry,
    DatasetStatus,
    DatasetVersion,
    MaterializationRefusal,
)
from app.modules.training_data.acquisition import training_candidate_service
from app.modules.training_data.schemas import (
    CandidateLifecycle,
    TrainingCandidateRecord,
)


# Teto de leitura por projeto. Existe para que uma materializacao nunca tente
# carregar uma populacao inteira sem limite em memoria.
MAX_DATASET_CANDIDATES = 10_000


class DatasetRegistryError(RuntimeError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def _fingerprint(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _split_for(fingerprint: str, seed: int, policy) -> str:
    """Split deterministico e estavel por fingerprint.

    Deterministico para que a mesma populacao produza sempre a mesma particao —
    sem isso, duas materializacoes da mesma versao dariam metricas diferentes e
    nenhuma avaliacao seria comparavel.

    Por fingerprint (e nao por indice) para que duas copias do mesmo fato caiam
    SEMPRE do mesmo lado: e o que impede o vazamento treino/validacao.
    """
    digest = hashlib.sha256(f"{seed}:{fingerprint}".encode()).digest()
    position = int.from_bytes(digest[:8], "big") / float(1 << 64)
    if position < policy.train:
        return "train"
    if position < policy.train + policy.validation:
        return "validation"
    return "test"


class DatasetRegistryService:
    """Registro de definicoes e versoes, sobre um repositorio pluggavel.

    O default e em memoria; um repositorio duravel (arquivo) e injetado por
    `set_repository`. A distincao importa: o que se persiste aqui e METADATA DE
    GOVERNANCA — quem declarou qual escopo, sob qual politica, e o que entrou em
    cada versao. Persistir governanca nao fabrica populacao, e
    `DATASET_NOT_READY` continua valendo enquanto nao houver dado real.
    """

    def __init__(self) -> None:
        self._repository: DatasetRegistryRepository = (
            InMemoryDatasetRegistryRepository()
        )

    def set_repository(self, repository: DatasetRegistryRepository | None) -> None:
        """Injeta o repositorio. `None` volta ao store em memoria."""
        self._repository = repository or InMemoryDatasetRegistryRepository()

    def reset(self) -> None:
        self._repository.clear()

    # -- definicao --------------------------------------------------------

    def define(
        self,
        definition: DatasetDefinition,
        caller: AuthenticatedCallerContext,
    ) -> DatasetDefinition:
        """Registra a governanca de um dataset. Nao produz dado algum."""
        if not training_candidate_service.admin_authorized(caller):
            raise DatasetRegistryError("DATASET_ADMIN_REQUIRED")
        if self._repository.get_definition(definition.dataset_id) is not None:
            raise DatasetRegistryError("DATASET_ALREADY_DEFINED")
        stored = definition.model_copy(
            update={"created_by": caller.credential_id, "status": DatasetStatus.DEFINED}
        )
        self._repository.save_definition(stored)
        return stored.model_copy(deep=True)

    def get(self, dataset_id: str) -> DatasetDefinition | None:
        return self._repository.get_definition(dataset_id)

    def list_definitions(self) -> list[DatasetDefinition]:
        return self._repository.list_definitions()

    def versions(self, dataset_id: str) -> list[DatasetVersion]:
        return self._repository.versions(dataset_id)

    # -- materializacao ---------------------------------------------------

    def materialize(
        self,
        dataset_id: str,
        caller: AuthenticatedCallerContext,
    ) -> DatasetVersion | MaterializationRefusal:
        """Materializa se — e somente se — houver readiness real.

        Devolve `MaterializationRefusal` em vez de lancar excecao: recusa e um
        resultado normal desta operacao, e nao um erro do chamador.
        """
        if not training_candidate_service.admin_authorized(caller):
            raise DatasetRegistryError("DATASET_ADMIN_REQUIRED")
        definition = self._repository.get_definition(dataset_id)
        if definition is None:
            raise DatasetRegistryError("DATASET_NOT_DEFINED")

        # Readiness pela MESMA politica que governa o Learning Plane. Um
        # segundo criterio aqui seria uma porta lateral para o mesmo dado.
        blockers: set[str] = set()
        for project_id in definition.project_ids:
            report = training_candidate_service.readiness(project_id=project_id)
            if report.readiness == "DATASET_NOT_READY":
                blockers.update(report.blocker_codes)

        if blockers:
            return MaterializationRefusal(
                dataset_id=dataset_id,
                blocker_codes=sorted(blockers),
                reason=(
                    "Population autorizada insuficiente; nenhum dataset foi "
                    "criado e nenhum treinamento foi iniciado."
                ),
            )

        candidates = self._authorized_candidates(definition)
        if not candidates:
            return MaterializationRefusal(
                dataset_id=dataset_id,
                blocker_codes=["NO_AUTHORIZED_CANDIDATES_IN_SCOPE"],
                reason=(
                    "Readiness satisfeita, porém nenhum candidato autorizado "
                    "corresponde ao escopo declarado do dataset."
                ),
            )

        return self._build_version(definition, candidates, caller)

    def _authorized_candidates(
        self, definition: DatasetDefinition
    ) -> list[TrainingCandidateRecord]:
        """Somente AUTHORIZED, no escopo, no proposito e nas origens declaradas.

        Quatro filtros e nao um: cada um corresponde a uma decisao diferente que
        alguem tomou, e afrouxar qualquer um deles deixaria entrar dado que a
        decisao correspondente nunca cobriu.
        """
        allowed_sources = set(definition.allowed_source_types)
        selected: list[TrainingCandidateRecord] = []
        for project_id in definition.project_ids:
            # A filtragem por lifecycle e purpose vai para o repositorio; a de
            # origem fica aqui porque o escopo declara um CONJUNTO de origens,
            # e a consulta aceita uma so.
            records, _total = training_candidate_service.page(
                project_id,
                lifecycle=CandidateLifecycle.AUTHORIZED,
                source_type=None,
                training_purpose=definition.training_purpose,
                task_type=None,
                limit=MAX_DATASET_CANDIDATES,
                offset=0,
            )
            selected.extend(
                record for record in records if record.source_type in allowed_sources
            )
        selected.sort(key=lambda item: (item.project_id, item.candidate_id))
        return selected

    def _build_version(
        self,
        definition: DatasetDefinition,
        candidates: list[TrainingCandidateRecord],
        caller: AuthenticatedCallerContext,
    ) -> DatasetVersion:
        policy = definition.split_policy
        lineage: list[DatasetLineageEntry] = []
        for record in candidates:
            split = _split_for(record.fingerprint, policy.seed, policy)
            lineage.append(
                DatasetLineageEntry(
                    candidate_id=record.candidate_id,
                    project_id=record.project_id,
                    source_type=record.source_type,
                    fingerprint=record.fingerprint,
                    authorization_policy_version=record.policy_version,
                    split=split,
                )
            )

        counts = {"train": 0, "validation": 0, "test": 0}
        for entry in lineage:
            counts[entry.split] += 1

        existing = self._repository.versions(definition.dataset_id)
        version = DatasetVersion(
            dataset_id=definition.dataset_id,
            version=len(existing) + 1,
            content_fingerprint=_fingerprint(
                [
                    {"candidate_id": item.candidate_id, "split": item.split}
                    for item in lineage
                ]
            ),
            materialized_at=datetime.now(timezone.utc),
            materialized_by=caller.credential_id,
            total_examples=len(lineage),
            train_examples=counts["train"],
            validation_examples=counts["validation"],
            test_examples=counts["test"],
            lineage=tuple(lineage),
        )
        self._repository.append_version(version)
        self._repository.save_definition(
            definition.model_copy(update={"status": DatasetStatus.MATERIALIZED})
        )
        return version


dataset_registry_service = DatasetRegistryService()
