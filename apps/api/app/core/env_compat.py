"""Compatibilidade de variaveis de ambiente entre Veltrix e o legado PedroCore.

O produto passou a se chamar Veltrix. As instalacoes existentes configuram
`PEDROCORE_*`, e quebra-las em silencio seria a pior forma de renomear: o
sistema subiria, a variavel nao seria lida, e o comportamento mudaria sem
ninguem ver.

A regra
-------

    VELTRIX_*    canonico
    PEDROCORE_*  legado, ainda aceito

Se so uma existe, ela vale. Se as duas existem com o MESMO valor, tudo bem —
e o estado normal de quem esta migrando aos poucos.

Se as duas existem com valores DIFERENTES, a configuracao e ambigua, e este
modulo nao escolhe. Escolher em silencio seria decidir por quem configurou, e
numa variavel de seguranca a escolha errada e invisivel ate o incidente.

Por que a ambiguidade e tratada por criticidade
-----------------------------------------------

Nem toda variavel merece derrubar o processo. Uma divergencia em modo de
persistencia muda onde o dado e gravado — isso precisa falhar alto. Uma
divergencia num rotulo de ambiente e ruim, mas nao vale impedir o sistema de
subir. Por isso o chamador declara a criticidade.

Segredo nunca e registrado
--------------------------

Nenhuma mensagem deste modulo inclui o VALOR de uma variavel. Ela diz qual
nome divergiu, e nada mais: a mensagem de erro de configuracao e lida em log,
e log e onde segredo vaza.
"""

from __future__ import annotations

import os
from enum import Enum

LEGACY_PREFIX = "PEDROCORE_"
CANONICAL_PREFIX = "VELTRIX_"


class AmbiguityPolicy(str, Enum):
    """O que fazer quando canonico e legado divergem."""

    # Falha alto. Para variaveis onde a escolha errada e invisivel: modo de
    # persistencia, URL de banco, chave de assinatura, registro de credenciais.
    FAIL = "fail"
    # Prefere o canonico e registra o aviso. Para rotulo e ajuste de conforto.
    PREFER_CANONICAL = "prefer_canonical"


class AmbiguousEnvironmentError(RuntimeError):
    """Canonico e legado presentes com valores diferentes.

    A mensagem nomeia as variaveis e nunca mostra os valores.
    """


def legacy_name(canonical: str) -> str:
    """`VELTRIX_X` -> `PEDROCORE_X`. Fora do padrao, devolve o proprio nome."""
    if canonical.startswith(CANONICAL_PREFIX):
        return LEGACY_PREFIX + canonical[len(CANONICAL_PREFIX) :]
    return canonical


def resolve(
    canonical: str,
    *,
    default: str | None = None,
    policy: AmbiguityPolicy = AmbiguityPolicy.FAIL,
    environ: dict[str, str] | None = None,
) -> str | None:
    """Le a variavel canonica, aceitando a legada como alias.

    Devolve `None` (ou o default) quando nenhuma das duas existe — quem chama
    decide o que fazer com a ausencia, porque "nao configurado" significa
    coisas diferentes em cada dominio.
    """
    fonte = environ if environ is not None else os.environ
    legado = legacy_name(canonical)

    novo = (fonte.get(canonical) or "").strip()
    velho = (fonte.get(legado) or "").strip()

    if novo and velho and novo != velho:
        if policy is AmbiguityPolicy.FAIL:
            raise AmbiguousEnvironmentError(
                f"Configuração ambígua: {canonical} e {legado} estão definidas "
                "com valores diferentes. Remova uma delas — o Veltrix não "
                "escolhe por você em configuração de segurança ou persistência."
            )
        return novo

    if novo:
        return novo
    if velho:
        return velho
    return default


def deprecation_notice(
    canonical: str, environ: dict[str, str] | None = None
) -> str | None:
    """Aviso quando so a variavel legada esta em uso.

    Aviso, e nao erro: quem ainda usa `PEDROCORE_*` continua funcionando. O
    texto existe para que a migracao aconteca por escolha, e nao por quebra.
    """
    fonte = environ if environ is not None else os.environ
    legado = legacy_name(canonical)
    if (fonte.get(legado) or "").strip() and not (fonte.get(canonical) or "").strip():
        return (
            f"{legado} está em uso e é o nome legado; o nome canônico é "
            f"{canonical}. Ambos funcionam nesta versão."
        )
    return None


def in_use(canonical: str, environ: dict[str, str] | None = None) -> bool:
    """Alguma das duas formas esta definida?"""
    fonte = environ if environ is not None else os.environ
    return bool(
        (fonte.get(canonical) or "").strip()
        or (fonte.get(legacy_name(canonical)) or "").strip()
    )
