"""Polaridade de menção: o que foi pedido, e o que foi proibido.

O problema
----------

    "Faça uma alteração apenas no Risk Console. Não altere migrations,
     banco de dados, autenticação..."

O motor lia `migrations` e `banco de dados` no texto e concluía MIGRAR BANCO,
com risco de dados CRÍTICO e cenário de falha de migração. A frase dizia
exatamente o contrário.

A causa era casamento de substring sem contexto: `term in texto`. Uma operação
citada como PROIBIDA era tratada como operação SOLICITADA.

O invariante que este módulo impõe
----------------------------------

    menção          !=  intenção
    menção negada   !=  operação solicitada
    alvo proibido   !=  alvo afetado

Por que segmentar por oração, e não parsear
-------------------------------------------

A menor solução robusta. Não há análise sintática, não há modelo de língua,
não há IA: o texto é partido em orações e cada uma é classificada pela
presença de marcador de negação ou proibição no seu início.

Isso resolve os casos que aparecem de verdade num prompt de instrução —
"não faça push; faça commit", "altere o módulo X, mas não toque no banco" —
sem trazer um analisador de linguagem para dentro do caminho determinístico,
que precisa continuar reproduzível e explicável.

O que ele NÃO tenta fazer
-------------------------

Negação de escopo fino ("altere tudo menos a coluna X"), ironia, negação
dupla, ou dependência de longa distância. Nesses casos a oração inteira é
classificada pelo marcador que ela carrega — e o resultado é conservador na
direção certa: deixa de INVENTAR intenção, e nunca deixa de detectar uma
operação pedida afirmativamente.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum


class Polarity(str, Enum):
    """Como um trecho do pedido se relaciona com a operação que ele cita."""

    # O texto pede que aconteça.
    REQUESTED = "REQUESTED"
    # O texto permite, sem pedir.
    ALLOWED = "ALLOWED"
    # O texto instrui a NÃO fazer. É restrição, não intenção.
    FORBIDDEN = "FORBIDDEN"
    # O texto nega o fato, sem ser instrução de proibição.
    NEGATED = "NEGATED"
    # Não há menção.
    UNKNOWN = "UNKNOWN"


# Polaridades que contam como pedido. Só estas alimentam inferência de operação
# e regras determinísticas.
AFFIRMATIVE = frozenset({Polarity.REQUESTED, Polarity.ALLOWED})

# Marcadores de PROIBIÇÃO: instrução para não fazer.
_FORBIDDING = (
    "não altere", "nao altere", "não alterar", "nao alterar",
    "não faça", "nao faca", "não fazer", "nao fazer",
    "não execute", "nao execute", "não executar", "nao executar",
    "não toque", "nao toque", "não tocar", "nao tocar",
    "não mexa", "nao mexa", "não mexer", "nao mexer",
    "não crie", "nao crie", "não criar", "nao criar",
    "não delete", "nao delete", "não deletar", "nao deletar",
    "não apague", "nao apague", "não apagar", "nao apagar",
    "não remova", "nao remova", "não remover", "nao remover",
    "não rode", "nao rode", "não rodar", "nao rodar",
    "não use", "nao use", "não usar", "nao usar",
    "não pode", "nao pode", "não deve", "nao deve",
    "nunca", "jamais", "proibido", "proibida", "vedado",
    "evite", "evitar", "sem alterar", "sem executar", "sem tocar",
    "sem criar", "sem deletar", "sem rodar", "sem fazer",
)

# Negação simples: nega o fato, sem ser ordem.
_NEGATING = ("não ", "nao ", "sem ", "nenhum", "nenhuma")

# Permissão explícita: citado como possível, não como pedido.
_ALLOWING = ("pode ", "permitido", "é permitido", "opcionalmente", "se necessário")

# Onde uma oração termina. Inclui o contraste, que é onde a polaridade vira:
# "altere o módulo X, mas não toque no banco".
_BOUNDARY = re.compile(
    r"[.;!?\n]"
    r"|,\s*(?=mas\b|porém\b|porem\b|contudo\b|entretanto\b|todavia\b|não\b|nao\b)"
    r"|\s+(?=mas\b|porém\b|porem\b|contudo\b|entretanto\b|todavia\b)"
    r"|\s+e\s+(?=não\b|nao\b|nunca\b|jamais\b)",
    re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class Clause:
    """Uma oração do pedido, com a polaridade que ela carrega."""

    text: str
    polarity: Polarity

    @property
    def affirmative(self) -> bool:
        return self.polarity in AFFIRMATIVE


def _classify(clause: str) -> Polarity:
    """Classifica uma oração pelo marcador que ela carrega.

    Proibição vence negação simples, e negação vence permissão: entre ler
    "não faça" como pedido e como proibição, só a segunda leitura é segura.
    """
    normal = clause.strip().lower()
    if not normal:
        return Polarity.UNKNOWN
    if any(marker in normal for marker in _FORBIDDING):
        return Polarity.FORBIDDEN
    if any(normal.startswith(marker) or f" {marker}" in normal for marker in _NEGATING):
        return Polarity.NEGATED
    if any(marker in normal for marker in _ALLOWING):
        return Polarity.ALLOWED
    return Polarity.REQUESTED


def split_clauses(text: str) -> tuple[Clause, ...]:
    """Parte o pedido em orações classificadas."""
    if not text or not text.strip():
        return ()
    partes = [item.strip() for item in _BOUNDARY.split(text) if item and item.strip()]
    return tuple(Clause(text=item, polarity=_classify(item)) for item in partes)


def affirmative_text(text: str) -> str:
    """Só o que o pedido efetivamente PEDE.

    É este texto que alimenta inferência de operação e regras determinísticas.
    O que foi proibido continua existindo — em `forbidden_terms` — mas não
    fabrica intenção.
    """
    return " ".join(item.text for item in split_clauses(text) if item.affirmative)


def forbidden_text(text: str) -> str:
    """Só o que o pedido proíbe ou nega."""
    return " ".join(item.text for item in split_clauses(text) if not item.affirmative)


def mention_polarity(text: str, term: str) -> Polarity:
    """Como um termo específico é citado no pedido.

    Se aparece em mais de uma oração, a polaridade AFIRMATIVA prevalece: pedir
    algo e depois restringi-lo continua sendo pedir. O contrário — citar como
    proibido e tratar como pedido — é o bug que este módulo existe para
    impedir.
    """
    alvo = term.strip().lower()
    if not alvo:
        return Polarity.UNKNOWN

    encontradas = [
        item.polarity
        for item in split_clauses(text)
        if alvo in item.text.lower()
    ]
    if not encontradas:
        return Polarity.UNKNOWN
    for polaridade in (Polarity.REQUESTED, Polarity.ALLOWED, Polarity.FORBIDDEN):
        if polaridade in encontradas:
            return polaridade
    return encontradas[0]


def forbidden_terms(text: str, vocabulary: tuple[str, ...]) -> tuple[str, ...]:
    """Termos do vocabulário citados como proibidos, e não como pedidos.

    Existe para que a proibição vire RESTRIÇÃO visível, em vez de sumir. O
    pedido dizia "não altere migrations"; o sistema precisa registrar que
    migrations foi citado, e que foi citado como proibido.
    """
    proibido = forbidden_text(text).lower()
    afirmativo = affirmative_text(text).lower()
    return tuple(
        termo
        for termo in vocabulary
        if termo in proibido and termo not in afirmativo
    )
