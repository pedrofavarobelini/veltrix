"""O catálogo de projetos, como serviço.

O que ele decide
----------------

Identidade e metadata. Só.

Ele NÃO decide capacidade. `manifest_reference` aqui responde "existe um
manifesto declarado para este id?", que é uma pergunta de exibição — o
conteúdo do manifesto continua sendo lido pelo Project Context, e a permissão
efetiva continua sendo a interseção de executor, projeto e política.

    registrado          !=   autorizado
    tem manifesto       !=   pode tudo que o manifesto lista
    sem manifesto       →    UNKNOWN, nunca um padrão generoso

Sem ramificação por nome
------------------------

Nenhuma função aqui compara `project_id` com um nome literal. Os seeds são
dados de entrada; o comportamento é o mesmo para "veltrix" e para um projeto
criado agora. Há um teste que lê o AST do núcleo para manter isso verdadeiro.
"""

from __future__ import annotations

from pydantic import ValidationError

from app.modules.project_context.manifests import PROJECT_MANIFESTS
from app.modules.project_registry.repository import (
    ProjectRepository,
    build_project_repository,
)
from app.modules.project_registry.schemas import (
    ProjectRecord,
    ProjectRegistryError,
    ProjectStatus,
    normalize_project_id,
    now,
)
from app.modules.project_registry.seeds import SEED_PROJECTS


def _construir(**campos) -> ProjectRecord:
    """Monta o registro traduzindo falha de validacao para erro do dominio.

    Os validadores levantam `ProjectRegistryError`, mas o Pydantic os embrulha
    em `ValidationError`. Quem chama — a TUI, a CLI — precisa de UMA excecao
    com mensagem em PT-BR, e nao de duas conforme a camada que falhou.
    """
    try:
        return ProjectRecord(**campos)
    except ValidationError as error:
        primeiro = error.errors()[0]
        mensagem = primeiro.get("msg", "")
        raise ProjectRegistryError(
            mensagem.removeprefix("Value error, ") or "Dados de projeto inválidos."
        ) from error


def manifest_reference(project_id: str) -> str | None:
    """Ponteiro para o manifesto, quando existe. Consulta por chave, não por nome."""
    manifesto = PROJECT_MANIFESTS.get(project_id)
    return getattr(manifesto, "manifest_version", None) if manifesto else None


class ProjectRegistryService:
    """Catálogo de projetos. Uma instância, um repositório."""

    def __init__(self, repository: ProjectRepository | None = None) -> None:
        self._repository = repository or build_project_repository()
        self._seed()

    @property
    def repository(self) -> ProjectRepository:
        return self._repository

    # --- semente ----------------------------------------------------------

    def _seed(self) -> None:
        """Planta os projetos iniciais UMA vez, sem sobrescrever nada.

        Um seed nunca pisa em cima do que o usuário editou: se o id já existe,
        o registro dele fica como está. Semear é preencher um catálogo vazio,
        não restaurar um estado de fábrica.
        """
        existentes = {item.project_id for item in self._repository.list_all()}
        for project_id, display_name in SEED_PROJECTS:
            if project_id in existentes:
                continue
            instante = now()
            self._repository.upsert(
                ProjectRecord(
                    project_id=project_id,
                    display_name=display_name,
                    status=ProjectStatus.ACTIVE,
                    created_at=instante,
                    updated_at=instante,
                    capability_manifest_reference=manifest_reference(project_id),
                )
            )

    # --- leitura ----------------------------------------------------------

    def list_projects(self, *, include_archived: bool = False) -> list[ProjectRecord]:
        """Ordem de REGISTRO, e nao alfabetica.

        A ordenacao mora aqui, e nao no store, para que memoria, JSON e
        PostgreSQL apresentem a mesma lista — ordem de exibicao e decisao de
        servico, e tres stores decidindo por conta propria dariam tres listas.

        Por registro, e nao por nome, porque alfabetica escolheria como padrao
        do console qualquer projeto cujo nome comece com A. Ordenar por
        `created_at` mantem os seeds na ordem declarada e faz um projeto novo
        aparecer no fim, onde o usuario acabou de cria-lo — sem que nenhuma
        linha de codigo precise saber o nome de projeto nenhum.
        """
        registros = sorted(
            self._repository.list_all(),
            key=lambda item: (item.created_at, item.display_name.lower()),
        )
        if include_archived:
            return registros
        return [item for item in registros if item.active]

    def get(self, project_id: str) -> ProjectRecord | None:
        """Busca pelo id normalizado. Um id inválido não encontra nada."""
        try:
            chave = normalize_project_id(project_id)
        except ProjectRegistryError:
            return None
        return self._repository.get(chave)

    def require(self, project_id: str) -> ProjectRecord:
        registro = self.get(project_id)
        if registro is None:
            raise ProjectRegistryError(
                f"Projeto desconhecido: {project_id!r}. "
                "Selecione um projeto existente ou crie um novo."
            )
        return registro

    def exists(self, project_id: str) -> bool:
        return self.get(project_id) is not None

    def has_manifest(self, project_id: str) -> bool:
        registro = self.get(project_id)
        return bool(registro and registro.capability_manifest_reference)

    # --- escrita ----------------------------------------------------------

    def create(
        self,
        *,
        display_name: str,
        project_id: str | None = None,
        local_path: str | None = None,
        repository_url: str | None = None,
    ) -> ProjectRecord:
        """Cria um projeto. Recusa se o id já existir.

        Sem id informado, ele é derivado do nome — o que torna o campo `ID` da
        tela um auto-preenchimento, não uma obrigação.
        """
        chave = normalize_project_id(project_id or display_name)
        if self._repository.get(chave) is not None:
            # Criar por cima seria a rota mais silenciosa para um projeto
            # assumir a identidade de outro.
            raise ProjectRegistryError(
                f"Já existe um projeto com o identificador {chave!r}. Escolha outro identificador."
            )
        instante = now()
        registro = _construir(
            project_id=chave,
            display_name=display_name,
            local_path=local_path,
            repository_url=repository_url,
            status=ProjectStatus.ACTIVE,
            created_at=instante,
            updated_at=instante,
            capability_manifest_reference=manifest_reference(chave),
        )
        self._repository.upsert(registro)
        return registro

    def update(
        self,
        project_id: str,
        *,
        display_name: str | None = None,
        local_path: str | None = None,
        repository_url: str | None = None,
    ) -> ProjectRecord:
        """Edita metadata. NUNCA a identidade.

        `project_id` não é parâmetro alterável, e `created_at` é preservado.
        Editar o nome de exibição de um projeto não pode movê-lo para o lugar
        de outro no isolamento.
        """
        atual = self.require(project_id)
        atualizado = atual.model_copy(
            update={
                "display_name": display_name if display_name is not None else atual.display_name,
                "local_path": local_path if local_path is not None else atual.local_path,
                "repository_url": (
                    repository_url if repository_url is not None else atual.repository_url
                ),
                "updated_at": now(),
            }
        )
        # Revalida: `model_copy` não passa pelos validadores, e é justamente
        # aqui que chegariam caminho com `..` e URL malformada.
        validado = _construir(**atualizado.model_dump())
        self._repository.upsert(validado)
        return validado

    def archive(self, project_id: str) -> ProjectRecord:
        """Arquiva. Não apaga.

        Um projeto arquivado some do fluxo normal mas continua existindo, e a
        identidade dele continua reservada — o que impede que um projeto novo
        herde o id de um antigo e, com ele, o histórico dele.
        """
        atual = self.require(project_id)
        registro = atual.model_copy(update={"status": ProjectStatus.ARCHIVED, "updated_at": now()})
        self._repository.upsert(registro)
        return registro

    def restore(self, project_id: str) -> ProjectRecord:
        atual = self.require(project_id)
        registro = atual.model_copy(update={"status": ProjectStatus.ACTIVE, "updated_at": now()})
        self._repository.upsert(registro)
        return registro


_service: ProjectRegistryService | None = None


def project_registry() -> ProjectRegistryService:
    """Instância compartilhada, construída na primeira consulta."""
    global _service
    if _service is None:
        _service = ProjectRegistryService()
    return _service


def reset_project_registry(service: ProjectRegistryService | None = None) -> None:
    """Ponto de injeção para teste. Não é usado em caminho de produção."""
    global _service
    _service = service
