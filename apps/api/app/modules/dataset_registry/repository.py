"""Persistência do Dataset Registry.

O que se persiste aqui — e o que NÃO se persiste
-------------------------------------------------

Persiste-se **metadata de governança**: definições de dataset, versões
materializadas, linhagem e fingerprints. Isso é o registro de *decisões* —
quem declarou qual escopo, sob qual política, e o que de fato entrou em cada
versão.

Não se persiste população de treino. Nenhum Training Candidate é criado, e
`DATASET_NOT_READY` continua sendo o resultado correto enquanto não houver
população real autorizada. Persistir governança não fabrica dado; são coisas
de natureza diferente, e confundi-las seria exatamente o erro que a Era 7
existe para impedir.

Por que precisa sobreviver ao restart
--------------------------------------

Uma definição de dataset é um ato de governança: alguém decidiu escopo,
propósito e política de split, e essa decisão precisa ser auditável depois.
Se o registro morre com o processo, a decisão vira boato — e a linhagem de uma
versão materializada, que é o que torna um modelo auditável, desaparece junto.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Protocol, runtime_checkable

from app.modules.dataset_registry.schemas import DatasetDefinition, DatasetVersion


@runtime_checkable
class DatasetRegistryRepository(Protocol):
    def save_definition(self, definition: DatasetDefinition) -> None: ...

    def get_definition(self, dataset_id: str) -> DatasetDefinition | None: ...

    def list_definitions(self) -> list[DatasetDefinition]: ...

    def append_version(self, version: DatasetVersion) -> None: ...

    def versions(self, dataset_id: str) -> list[DatasetVersion]: ...

    def clear(self) -> None: ...


class InMemoryDatasetRegistryRepository:
    """Store em processo. Usado em teste e no modo `memory` explícito."""

    def __init__(self) -> None:
        self._definitions: dict[str, DatasetDefinition] = {}
        self._versions: dict[str, list[DatasetVersion]] = {}

    def save_definition(self, definition: DatasetDefinition) -> None:
        self._definitions[definition.dataset_id] = definition.model_copy(deep=True)

    def get_definition(self, dataset_id: str) -> DatasetDefinition | None:
        found = self._definitions.get(dataset_id)
        return found.model_copy(deep=True) if found else None

    def list_definitions(self) -> list[DatasetDefinition]:
        return [item.model_copy(deep=True) for item in self._definitions.values()]

    def append_version(self, version: DatasetVersion) -> None:
        self._versions.setdefault(version.dataset_id, []).append(
            version.model_copy(deep=True)
        )

    def versions(self, dataset_id: str) -> list[DatasetVersion]:
        return [item.model_copy(deep=True) for item in self._versions.get(dataset_id, [])]

    def clear(self) -> None:
        self._definitions.clear()
        self._versions.clear()


class LocalJsonDatasetRegistryRepository(InMemoryDatasetRegistryRepository):
    """Registro em arquivo JSON, carregado na construção.

    Segue o padrão já estabelecido em `report_memory`: subclasse do store em
    memória, leitura no `__init__`, gravação a cada escrita. É esse
    carregamento na construção que torna o restart verificável — uma instância
    nova enxerga o que a anterior decidiu.
    """

    def __init__(self, directory: str | Path) -> None:
        super().__init__()
        self._directory = Path(directory)
        self._directory.mkdir(parents=True, exist_ok=True)
        self._file = self._directory / "dataset_registry.json"
        self._load()

    def _load(self) -> None:
        if not self._file.exists():
            return
        try:
            raw = json.loads(self._file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return
        if not isinstance(raw, dict):
            return
        for item in raw.get("definitions", []):
            try:
                super().save_definition(DatasetDefinition(**item))
            except Exception:
                # Uma definição ilegível não pode impedir as outras de carregar.
                continue
        for item in raw.get("versions", []):
            try:
                super().append_version(DatasetVersion(**item))
            except Exception:
                continue

    def _persist(self) -> None:
        payload = {
            "definitions": [
                item.model_dump(mode="json") for item in self.list_definitions()
            ],
            "versions": [
                version.model_dump(mode="json")
                for definition in self.list_definitions()
                for version in self.versions(definition.dataset_id)
            ],
        }
        temporary = self._file.with_suffix(".json.tmp")
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        # Atômico no mesmo sistema de arquivos: nunca um arquivo pela metade.
        os.replace(temporary, self._file)

    def save_definition(self, definition: DatasetDefinition) -> None:
        super().save_definition(definition)
        self._persist()

    def append_version(self, version: DatasetVersion) -> None:
        super().append_version(version)
        self._persist()

    def clear(self) -> None:
        super().clear()
        self._persist()
