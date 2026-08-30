"""Construção do outbox a partir da configuração real.

Por que este módulo existe
--------------------------

A implementação durável existia, mas ninguém a construía fora dos testes. Em
produção não havia caminho algum que a instanciasse — o que significa que
"outbox durável" descrevia uma classe disponível, não um comportamento em
vigor. Uma peça que só é montada em teste não protege nada.

O interruptor é o MESMO do resto do sistema
--------------------------------------------

`PEDROCORE_REPORT_MEMORY_PERSISTENCE` já decide onde vivem Report Memory,
Interaction Outcomes, Operational Memory, Candidate Store e Evidence Registry.
O outbox entra na mesma chave em vez de inventar a sexta forma de configurar
armazenamento no mesmo processo — cada nova chave é mais um jeito de o
ambiente ficar meio ligado.

| modo | implementação | durável? |
|---|---|---|
| `off` | nenhuma — recusa fail-closed | — |
| `memory` | `OutboxStore` | não (explícito) |
| `local_json` | `DurableOutboxStore` | sim, arquivo |
| `postgresql` | `PostgreSQLOutboxStore` | sim, banco |

`off` recusa em vez de cair em memória. Um outbox que silenciosamente não
persiste é pior do que outbox nenhum: o consumidor acredita ter uma garantia de
entrega que não existe, e descobre no primeiro restart — com dado já perdido.

`memory` continua disponível, mas só por escolha explícita. É a diferença entre
"o operador decidiu que aqui é efêmero" e "ninguém configurou nada".
"""

from __future__ import annotations

import os
from pathlib import Path

from app.modules.report_memory.repository import ReportMemoryRepositoryConfigurationError
from app.modules.report_memory.service import (
    FLAG_DATABASE_URL,
    FLAG_MEMORY_DIR,
    MODE_LOCAL_JSON,
    MODE_MEMORY,
    MODE_POSTGRESQL,
    persistence_mode,
)
from app.modules.resilience.durable_outbox import (
    DurableOutboxStore,
    PostgreSQLOutboxStore,
)
from app.modules.resilience.outbox import OutboxStore

# Subdiretório do outbox dentro do diretório de persistência local. Separado do
# Report Memory de propósito: são estados de natureza diferente, e misturá-los
# faria a limpeza de um arriscar o outro.
OUTBOX_SUBDIRECTORY = "outbox"


def outbox_persistence_mode() -> str:
    """Modo efetivo do outbox. Mesma variável do resto do sistema."""
    return persistence_mode()


def build_outbox_store() -> OutboxStore:
    """Constrói o outbox conforme a configuração. Fail-closed em `off`.

    Devolve sempre uma implementação real — nunca um objeto que finge
    persistir. Quando a configuração não permite decidir, levanta em vez de
    escolher a opção mais permissiva.
    """
    mode = persistence_mode()

    if mode == MODE_MEMORY:
        # Efêmero POR ESCOLHA. Sobrevive ao servidor cair, não ao processo.
        return OutboxStore()

    if mode == MODE_LOCAL_JSON:
        directory = (os.environ.get(FLAG_MEMORY_DIR) or "").strip()
        if not directory:
            raise ReportMemoryRepositoryConfigurationError(
                f"{FLAG_MEMORY_DIR} é obrigatória no modo local_json; "
                "o outbox não escolhe um diretório por conta própria."
            )
        return DurableOutboxStore(Path(directory) / OUTBOX_SUBDIRECTORY)

    if mode == MODE_POSTGRESQL:
        database_url = (os.environ.get(FLAG_DATABASE_URL) or "").strip()
        if not database_url:
            raise ReportMemoryRepositoryConfigurationError(
                f"{FLAG_DATABASE_URL} é obrigatória no modo postgresql."
            )
        return PostgreSQLOutboxStore(database_url)

    raise ReportMemoryRepositoryConfigurationError(
        "Outbox desabilitado (persistência 'off'); nenhum fallback em memória "
        "foi aplicado. Um outbox que não persiste promete uma garantia de "
        "entrega que não tem."
    )


def outbox_is_durable() -> bool:
    """A configuração atual sobrevive ao restart do processo?

    Exposto para que um consumidor possa VERIFICAR a promessa antes de confiar
    nela, em vez de descobrir no primeiro restart.
    """
    return persistence_mode() in {MODE_LOCAL_JSON, MODE_POSTGRESQL}
