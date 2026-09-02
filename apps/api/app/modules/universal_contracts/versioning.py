"""Versionamento dos Universal Contracts V1.

Por que este modulo existe
--------------------------

Um contrato sem regra de versao quebra consumidores em silencio. O produtor
adiciona um campo, o servidor comeca a recusar, e a falha aparece em producao
do lado de quem integrou — nao do lado de quem mudou.

Aqui a regra e explicita e executavel: cada contrato declara sua versao, o
PedroCore declara quais versoes aceita, e versao desconhecida e **recusada**,
nunca adivinhada. Nao existe "melhor esforco" para interpretar um contrato que
o servidor nao conhece: interpretar errado um payload de aprendizado ou de
autorizacao e pior do que recusa-lo.

Regra de evolucao
-----------------

`ADDITIVE` — campo opcional novo, valor novo em enum aberto. Nao muda a versao.
Consumidores antigos continuam validos porque o campo tem default.

`BREAKING` — campo obrigatorio novo, remocao de campo, mudanca de tipo, mudanca
de semantica. Exige **versao nova** (`.../v2`), com a v1 mantida ate haver
migration path comprovado. Nunca se altera a v1 no lugar.

`DEPRECATED` — versao ainda aceita, porem anunciada como em fim de vida. O
PedroCore responde com aviso, e nao com erro, para que o consumidor migre sem
queda.

`UNKNOWN` — versao que o servidor nao conhece. Fail-closed.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# IDENTIFICADORES CONGELADOS E O RENAME PARA VELTRIX
# ---------------------------------------------------------------------------
#
# O produto se chama Veltrix. Os identificadores de contrato continuam com o
# prefixo `pedrocore-` — `pedrocore-integration/v1`, `pedrocore-risk-request/v1`
# e os demais — e isso e deliberado.
#
# Trocar o identificador mudaria o fingerprint congelado e quebraria todo
# consumidor que ja envia o nome antigo. Identificador de protocolo nao e
# marca: e contrato publicado, e contrato publicado nao se renomeia porque a
# empresa mudou de nome.
#
# O mesmo vale para as DOCSTRINGS dos modelos deste pacote: elas viram
# `description` no `model_json_schema()` e entram no fingerprint. Durante o
# rename, um replace de prosa as alterou e derrubou os seis fingerprints de uma
# vez. Foram revertidas.
#
# Identificador novo so com VERSAO nova e caminho de migracao.

from enum import Enum
from types import MappingProxyType

# Familia de versao dos contratos desta Era. Um unico identificador por
# contrato, com o sufixo explicito — `.../v1` e parte do contrato, nao um
# detalhe de implementacao.
CAPABILITY_MANIFEST_V1 = "pedrocore-capability-manifest/v1"
QUALITY_EVIDENCE_V1 = "pedrocore-quality-evidence/v1"
EXECUTION_OUTCOME_V1 = "pedrocore-execution-outcome/v1"
LEARNING_SOURCE_V1 = "pedrocore-learning-source/v1"
INTEGRATION_ENVELOPE_V1 = "pedrocore-integration/v1"
# Stage R4 do Risk Engine V2. Contrato proprio em vez de payload do envelope:
# acrescentar um valor a `IntegrationPayloadType` mudaria o JSON Schema do
# envelope e, com ele, um fingerprint congelado. Os cinco V1 ficam intactos.
RISK_REQUEST_V1 = "pedrocore-risk-request/v1"


class ContractVersionStatus(str, Enum):
    """Situacao de uma versao de contrato perante o PedroCore."""

    SUPPORTED = "supported"
    DEPRECATED = "deprecated"
    UNKNOWN = "unknown"


class ContractCompatibility(str, Enum):
    """Classificacao de uma mudanca de schema.

    Existe para que a decisao "isto exige v2?" seja discutida com um vocabulario
    comum, e nao caso a caso na revisao.
    """

    ADDITIVE = "additive"
    BREAKING = "breaking"


# Versoes aceitas. Um contrato ausente deste mapa e UNKNOWN por definicao —
# nao ha default permissivo.
_VERSION_STATUS: dict[str, ContractVersionStatus] = {
    CAPABILITY_MANIFEST_V1: ContractVersionStatus.SUPPORTED,
    QUALITY_EVIDENCE_V1: ContractVersionStatus.SUPPORTED,
    EXECUTION_OUTCOME_V1: ContractVersionStatus.SUPPORTED,
    LEARNING_SOURCE_V1: ContractVersionStatus.SUPPORTED,
    INTEGRATION_ENVELOPE_V1: ContractVersionStatus.SUPPORTED,
    RISK_REQUEST_V1: ContractVersionStatus.SUPPORTED,
}

CONTRACT_VERSION_STATUS: MappingProxyType[str, ContractVersionStatus] = MappingProxyType(
    _VERSION_STATUS
)

SUPPORTED_CONTRACT_VERSIONS: frozenset[str] = frozenset(
    name for name, status in _VERSION_STATUS.items() if status is not ContractVersionStatus.UNKNOWN
)

# Contratos que podem viajar como payload dentro do envelope de integracao.
# O manifesto NAO entra aqui: ele descreve o consumidor, e nao um evento dele.
PAYLOAD_CONTRACT_VERSIONS: frozenset[str] = frozenset(
    {QUALITY_EVIDENCE_V1, EXECUTION_OUTCOME_V1, LEARNING_SOURCE_V1}
)


def version_status(contract_version: str) -> ContractVersionStatus:
    """Situacao da versao informada. Desconhecida por default, nunca aceita."""
    return _VERSION_STATUS.get(
        (contract_version or "").strip(), ContractVersionStatus.UNKNOWN
    )


def is_supported(contract_version: str) -> bool:
    """A versao pode ser processada? `DEPRECATED` ainda pode — com aviso."""
    return version_status(contract_version) in {
        ContractVersionStatus.SUPPORTED,
        ContractVersionStatus.DEPRECATED,
    }


def deprecation_warning(contract_version: str) -> str | None:
    """Aviso para versao em fim de vida; `None` quando nao ha o que avisar.

    Deprecacao avisa, nao derruba: um consumidor em versao antiga precisa de
    uma janela para migrar, e transformar isso em erro empurra a queda para
    quem menos pode reagir.
    """
    if version_status(contract_version) is ContractVersionStatus.DEPRECATED:
        return (
            f"Contrato {contract_version} esta DEPRECATED e sera removido em "
            "versao futura; migre para a versao suportada mais recente."
        )
    return None
