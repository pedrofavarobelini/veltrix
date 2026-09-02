"""Identidade visual e textual do console, centralizada.

Por que um modulo so para isto
------------------------------

O produto foi renomeado de PedroCore para Veltrix. Se as
strings de marca ficarem espalhadas por telas, mensagens e testes, o rename
vira uma cacada a `grep` com risco de trocar tambem identificador tecnico —
que e justamente o que NAO pode mudar (variavel de ambiente, tabela, id de
contrato congelado).

Aqui a marca fica em um lugar. O rename passa a ser a edicao deste arquivo.

Nomenclatura tecnica x nome de exibicao
---------------------------------------

`PRODUCT_NAME` e o que o humano le. `COMMAND_NAME` e o que o humano digita, e
ainda e `pedrocore` porque o pacote, o console script e os identificadores
tecnicos continuam com esse nome. Os dois sao deliberadamente separados: a
tela ja pode mostrar a identidade aprovada sem que nada tecnico mude.
"""

from __future__ import annotations

# --- marca ----------------------------------------------------------------

PRODUCT_NAME = "VELTRIX RISK ENGINE"
PRODUCT_SUBTITLE = "Console de Risco Pré-Execução"

# Nome do produto inteiro, usado fora do console.
PLATFORM_NAME = "Veltrix"
PLATFORM_TAGLINE = "AI Runtime & Learning Control Plane"

# Comando canonico. `pedrocore` continua funcionando como alias legado para
# nao quebrar script, atalho e documentacao de quem ja usava.
COMMAND_NAME = "veltrix"
LEGACY_COMMAND_NAME = "pedrocore"
CONSOLE_SUBCOMMAND = "risk"

# Identificador tecnico do console como produtor de analises. Nao e marca: e
# PROVENANCE, e mudar provenance quebraria a correspondencia com analises ja
# gravadas. Preservado de proposito.
CONSOLE_PRODUCER = "pedrocore-risk-console"
CONSOLE_AGENT_ID = "risk-console"


def console_command() -> str:
    """`pedrocore risk` — como o usuário abre o console."""
    return f"{COMMAND_NAME} {CONSOLE_SUBCOMMAND}"


# --- paleta ---------------------------------------------------------------
#
# Terminal tecnico: fundo grafite, texto claro, ciano como cor de estrutura.
# Verde/amarelo/vermelho carregam significado e por isso NAO sao usados como
# decoracao — se tudo fosse colorido, a cor pararia de informar.

COLOR_BACKGROUND = "#0b0d10"
COLOR_PANEL = "#14181d"
COLOR_BORDER = "#2a3138"
COLOR_TEXT = "#e6edf3"
COLOR_MUTED = "#8b98a5"
COLOR_ACCENT = "#22d3ee"

COLOR_OK = "#3fb950"
COLOR_WARN = "#d29922"
COLOR_DANGER = "#f85149"
COLOR_CRITICAL = "#ff6b6b"
