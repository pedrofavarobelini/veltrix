"""Telas de projeto: criar e gerenciar.

Duas telas modais, deliberadamente pequenas
--------------------------------------------

A pergunta "que projeto é este?" não merece um painel administrativo. Criar
pede quatro campos, dois deles opcionais; gerenciar edita metadata e arquiva.
Nada além disso, porque nada além disso é necessário para analisar risco.

O que estas telas NÃO fazem
---------------------------

Não concedem capacidade. Não sincronizam com GitHub — `repository_url` é
metadado exibido, e nenhuma rede é tocada. Não apagam: arquivar preserva o
registro e a identidade, para que um projeto novo não herde o id de um antigo
junto com o histórico dele.

E não deixam trocar o `project_id`. Ele é a chave de isolamento; editar
metadata não pode virar assumir a identidade de outro projeto.
"""

from __future__ import annotations

from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Select, Static

from app.modules.project_registry.schemas import (
    ProjectRegistryError,
    normalize_project_id,
)
from app.modules.project_registry.service import project_registry

_MODAL_CSS = """
    NovoProjetoScreen, GerenciarProjetosScreen {
        align: center middle;
    }
    #caixa {
        width: 66;
        max-width: 90%;
        height: auto;
        max-height: 90%;
        border: round $accent;
        border-title-style: bold;
        background: $surface;
        padding: 1 2;
    }
    #caixa Label { width: 100%; height: auto; }
    #caixa Input { margin: 0 0 1 0; }
    #caixa Select { margin: 0 0 1 0; }
    .ajuda-modal { color: $text-muted; text-style: italic; }
    #erro-modal { color: $error; height: auto; width: 100%; }
    #acoes-modal { height: 3; margin: 1 0 0 0; }
    #acoes-modal Button { margin: 0 2 0 0; }
"""


class NovoProjetoScreen(ModalScreen[str | None]):
    """Cria um projeto. Devolve o `project_id` criado, ou `None`."""

    CSS = _MODAL_CSS
    BINDINGS = [("escape", "cancelar", "Cancelar")]

    def compose(self) -> ComposeResult:
        with Vertical(id="caixa"):
            yield Label("Nome")
            yield Input(placeholder="ex.: Meu Projeto", id="np-nome")

            yield Label("ID")
            yield Label(
                "Gerado a partir do nome. A identidade não muda depois.",
                classes="ajuda-modal",
            )
            yield Input(placeholder="gerado automaticamente", id="np-id")

            yield Label("Caminho local — opcional")
            yield Input(placeholder="ex.: C:\\Projetos\\meu-projeto", id="np-caminho")

            yield Label("Repositório GitHub — opcional")
            yield Label("Apenas metadado. Nada é sincronizado.", classes="ajuda-modal")
            yield Input(placeholder="ex.: https://github.com/org/repo", id="np-repo")

            yield Static("", id="erro-modal")
            with Horizontal(id="acoes-modal"):
                yield Button("CRIAR PROJETO", id="np-criar", variant="primary")
                yield Button("CANCELAR", id="np-cancelar")

    def on_mount(self) -> None:
        self.query_one("#caixa").border_title = "NOVO PROJETO"
        self.query_one("#np-nome", Input).focus()

    @on(Input.Changed, "#np-nome")
    def _espelha_id(self, event: Input.Changed) -> None:
        """Mostra o id que será usado, enquanto o nome é digitado.

        O usuário vê a identidade antes de confirmá-la; descobrir depois que
        "Meu Projeto!" virou outra coisa seria descobrir tarde demais.
        """
        campo = self.query_one("#np-id", Input)
        try:
            campo.placeholder = normalize_project_id(event.value)
        except ProjectRegistryError:
            campo.placeholder = "gerado automaticamente"

    def _erro(self, texto: str) -> None:
        self.query_one("#erro-modal", Static).update(texto)

    @on(Button.Pressed, "#np-criar")
    def _criar(self) -> None:
        nome = self.query_one("#np-nome", Input).value.strip()
        identificador = self.query_one("#np-id", Input).value.strip()
        caminho = self.query_one("#np-caminho", Input).value.strip()
        repositorio = self.query_one("#np-repo", Input).value.strip()
        try:
            registro = project_registry().create(
                display_name=nome,
                project_id=identificador or None,
                local_path=caminho or None,
                repository_url=repositorio or None,
            )
        except ProjectRegistryError as error:
            self._erro(str(error))
            return
        self.dismiss(registro.project_id)

    @on(Button.Pressed, "#np-cancelar")
    def _cancelar(self) -> None:
        self.action_cancelar()

    def action_cancelar(self) -> None:
        self.dismiss(None)


class GerenciarProjetosScreen(ModalScreen[str | None]):
    """Edita metadata e arquiva. Devolve o id afetado, ou `None`."""

    CSS = _MODAL_CSS
    BINDINGS = [("escape", "cancelar", "Fechar")]

    def compose(self) -> ComposeResult:
        registros = project_registry().list_projects(include_archived=True)
        opcoes = [
            (f"{item.display_name}  ({item.status.value})", item.project_id) for item in registros
        ]
        with VerticalScroll(id="caixa"):
            yield Label("Projeto")
            yield Select(
                opcoes,
                id="gp-projeto",
                allow_blank=False,
                value=opcoes[0][1] if opcoes else Select.BLANK,
            )

            yield Label("Identificador")
            yield Label(
                "Identidade de isolamento. Não pode ser alterada.",
                classes="ajuda-modal",
            )
            yield Static("", id="gp-id")

            yield Label("Manifesto de capacidades")
            yield Static("", id="gp-manifesto")

            yield Label("Nome de exibição")
            yield Input(id="gp-nome")

            yield Label("Caminho local")
            yield Input(id="gp-caminho")

            yield Label("Repositório")
            yield Input(id="gp-repo")

            yield Static("", id="erro-modal")
            with Horizontal(id="acoes-modal"):
                yield Button("SALVAR", id="gp-salvar", variant="primary")
                yield Button("ARQUIVAR", id="gp-arquivar")
                yield Button("REATIVAR", id="gp-reativar")
                yield Button("FECHAR", id="gp-fechar")

    def on_mount(self) -> None:
        self.query_one("#caixa").border_title = "GERENCIAR PROJETOS"
        self._carregar()

    def _selecionado(self) -> str:
        return str(self.query_one("#gp-projeto", Select).value)

    def _carregar(self) -> None:
        registro = project_registry().get(self._selecionado())
        if registro is None:
            return
        self.query_one("#gp-id", Static).update(registro.project_id)
        self.query_one("#gp-manifesto", Static).update(
            registro.capability_manifest_reference or "não configurado"
        )
        self.query_one("#gp-nome", Input).value = registro.display_name
        self.query_one("#gp-caminho", Input).value = registro.local_path or ""
        self.query_one("#gp-repo", Input).value = registro.repository_url or ""
        self.query_one("#gp-arquivar", Button).disabled = not registro.active
        self.query_one("#gp-reativar", Button).disabled = registro.active

    @on(Select.Changed, "#gp-projeto")
    def _trocou(self) -> None:
        self.query_one("#erro-modal", Static).update("")
        self._carregar()

    def _erro(self, texto: str) -> None:
        self.query_one("#erro-modal", Static).update(texto)

    @on(Button.Pressed, "#gp-salvar")
    def _salvar(self) -> None:
        try:
            project_registry().update(
                self._selecionado(),
                display_name=self.query_one("#gp-nome", Input).value.strip(),
                local_path=self.query_one("#gp-caminho", Input).value.strip() or None,
                repository_url=self.query_one("#gp-repo", Input).value.strip() or None,
            )
        except ProjectRegistryError as error:
            self._erro(str(error))
            return
        self.dismiss(self._selecionado())

    @on(Button.Pressed, "#gp-arquivar")
    def _arquivar(self) -> None:
        try:
            project_registry().archive(self._selecionado())
        except ProjectRegistryError as error:
            self._erro(str(error))
            return
        self.dismiss(self._selecionado())

    @on(Button.Pressed, "#gp-reativar")
    def _reativar(self) -> None:
        try:
            project_registry().restore(self._selecionado())
        except ProjectRegistryError as error:
            self._erro(str(error))
            return
        self.dismiss(self._selecionado())

    @on(Button.Pressed, "#gp-fechar")
    def _fechar(self) -> None:
        self.action_cancelar()

    def action_cancelar(self) -> None:
        self.dismiss(None)
