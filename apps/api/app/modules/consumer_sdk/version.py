"""Versionamento do Consumer SDK.

Modulo separado de proposito: a matriz de compatibilidade precisa saber quais
versoes o servidor aceita SEM importar o cliente inteiro, e um import circular
entre SDK e compatibilidade seria pago em toda inicializacao.
"""

from __future__ import annotations

SDK_VERSION = "1.0.0"

# Versoes que ESTE servidor aceita. A lista e do servidor, nao do cliente:
# quem decide se uma versao ainda serve e quem responde por ela.
SDK_SUPPORTED_VERSIONS: frozenset[str] = frozenset({"1.0.0"})


def is_supported(version: str) -> bool:
    return version.strip() in SDK_SUPPORTED_VERSIONS
