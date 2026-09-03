"""Identidade canônica de um recurso de escopo.

O problema
----------

O Auto Context propunha:

    alvo             risk_console
    escopo permitido module:risk_console

e o Scope Analyzer comparava conjuntos de strings. `"risk_console"` não é
igual a `"module:risk_console"`, então o alvo caía fora do escopo, o motor
emitia `SCOPE_UNBOUNDED` e o risco de escopo virava ALTO.

Conflito falso: o mesmo recurso, escrito de duas formas.

A forma canônica já existia
---------------------------

O domínio sempre usou `<tipo>:<nome>` — `module:billing`,
`file:billing/service.py` —, e o Post-Execution já normalizava caminho de
arquivo para `file:...` antes de comparar. O que faltava era **uma** função,
usada por todos os lados, em vez de a convenção viver na cabeça de quem
escreve cada chamador.

O que ela faz, e o que deliberadamente não faz
----------------------------------------------

Faz: dá ao mesmo recurso a mesma identidade. `risk_console` e
`module:risk_console` passam a comparar iguais.

**Não faz**: hierarquia. `file:billing/service.py` NÃO passa a pertencer a
`module:billing`. Isso seria alargar a verificação de escopo, e alargar
verificação de escopo é afrouxar autorização — exatamente o oposto do que esta
correção existe para fazer. A comparação continua sendo igualdade exata sobre
a forma canônica.

Tipo padrão
-----------

Nome sem prefixo assume `module:`. É o tipo que o domínio mais usa, e é o que
torna `risk_console` equivalente a `module:risk_console`. Um nome que queira
ser outra coisa declara o próprio tipo.
"""

from __future__ import annotations

from collections.abc import Iterable

DEFAULT_KIND = "module"

# Tipos que o domínio já usa. A lista existe para que um prefixo desconhecido
# não seja confundido com um nome que por acaso contém dois-pontos.
KNOWN_KINDS: frozenset[str] = frozenset(
    {
        "module",
        "file",
        "service",
        "database",
        "table",
        "capability",
        "environment",
        "user",
    }
)


def canonical_scope(value: str) -> str:
    """Identidade canônica de um recurso.

    `risk_console`         → `module:risk_console`
    `module:risk_console`  → `module:risk_console`
    `file:a/b.py`          → `file:a/b.py`
    `git.push`             → `module:git.push`

    O último caso parece estranho e é correto: sem tipo declarado, o valor é
    tratado como o tipo padrão. Quem quer dizer "capacidade" escreve
    `capability:git.push`.
    """
    texto = (value or "").strip()
    if not texto:
        return ""
    prefixo, separador, resto = texto.partition(":")
    if separador and prefixo.strip().lower() in KNOWN_KINDS and resto.strip():
        return f"{prefixo.strip().lower()}:{resto.strip()}"
    return f"{DEFAULT_KIND}:{texto}"


def canonical_scopes(values: Iterable[str]) -> list[str]:
    """Canonicaliza preservando ordem e removendo duplicata equivalente.

    Duas grafias do mesmo recurso viram uma entrada só — que é o ponto: se
    continuassem duas, a contagem de alcance passaria a mentir.
    """
    vistos: dict[str, None] = {}
    for item in values:
        canonico = canonical_scope(item)
        if canonico:
            vistos.setdefault(canonico, None)
    return list(vistos)


def scope_kind(value: str) -> str:
    """O tipo declarado de um recurso, já canonicalizado."""
    return canonical_scope(value).partition(":")[0]


def scope_name(value: str) -> str:
    """O nome, sem o tipo."""
    return canonical_scope(value).partition(":")[2]
