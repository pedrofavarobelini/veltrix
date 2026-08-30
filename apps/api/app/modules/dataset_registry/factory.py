"""Construção do repositório do Dataset Registry a partir da configuração.

Mesma chave, mesma regra
------------------------

`PEDROCORE_REPORT_MEMORY_PERSISTENCE` decide onde vive o registry, como decide
para todo o resto. O serviço não constrói mais um store em memória por conta
própria: um default implícito faria produção guardar decisões de governança em
um dicionário que morre com o processo, sem ninguém ter escolhido isso.

| modo | implementação | durável? |
|---|---|---|
| `off` | nenhuma — recusa fail-closed | — |
| `memory` | `InMemoryDatasetRegistryRepository` | não (explícito) |
| `local_json` | `LocalJsonDatasetRegistryRepository` | sim, arquivo |
| `postgresql` | ainda não implementado — recusa explícita | — |

Por que `postgresql` recusa em vez de cair para arquivo
--------------------------------------------------------

A migration `0008` cria as tabelas, mas o repositório PostgreSQL do registry
ainda não foi escrito. Cair para arquivo quando alguém pediu banco seria o pior
dos dois mundos: o operador acredita que a governança está no PostgreSQL que
ele faz backup, e ela está em um arquivo local que ninguém copia.

Recusar deixa a lacuna visível. Um erro na inicialização custa minutos; uma
governança perdida em uma máquina que morreu custa a auditoria inteira.
"""

from __future__ import annotations

import os
from pathlib import Path

from app.modules.dataset_registry.repository import (
    DatasetRegistryRepository,
    InMemoryDatasetRegistryRepository,
    LocalJsonDatasetRegistryRepository,
)
from app.modules.report_memory.repository import ReportMemoryRepositoryConfigurationError
from app.modules.report_memory.service import (
    FLAG_MEMORY_DIR,
    MODE_LOCAL_JSON,
    MODE_MEMORY,
    MODE_POSTGRESQL,
    persistence_mode,
)

# Subdiretório próprio: metadata de governança e memória operacional têm ciclos
# de vida diferentes, e limpar uma não pode arriscar a outra.
REGISTRY_SUBDIRECTORY = "dataset-registry"


def build_dataset_registry_repository() -> DatasetRegistryRepository:
    """Constrói o repositório conforme a configuração. Fail-closed em `off`."""
    mode = persistence_mode()

    if mode == MODE_MEMORY:
        # Efêmero POR ESCOLHA — a decisão de governança some com o processo.
        return InMemoryDatasetRegistryRepository()

    if mode == MODE_LOCAL_JSON:
        directory = (os.environ.get(FLAG_MEMORY_DIR) or "").strip()
        if not directory:
            raise ReportMemoryRepositoryConfigurationError(
                f"{FLAG_MEMORY_DIR} é obrigatória no modo local_json; o Dataset "
                "Registry não escolhe um diretório por conta própria."
            )
        return LocalJsonDatasetRegistryRepository(
            Path(directory) / REGISTRY_SUBDIRECTORY
        )

    if mode == MODE_POSTGRESQL:
        raise ReportMemoryRepositoryConfigurationError(
            "Dataset Registry ainda não possui repositório PostgreSQL. As "
            "tabelas existem na migration 0008, mas o repositório não foi "
            "implementado; cair para arquivo faria a governança parecer estar "
            "no banco que se faz backup quando não está."
        )

    raise ReportMemoryRepositoryConfigurationError(
        "Dataset Registry desabilitado (persistência 'off'); nenhum fallback "
        "em memória foi aplicado."
    )


def dataset_registry_is_durable() -> bool:
    """A configuração atual sobrevive ao restart do processo?"""
    return persistence_mode() == MODE_LOCAL_JSON
