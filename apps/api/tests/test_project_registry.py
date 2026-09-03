"""Project Registry: identidade de projeto, e só isso.

O que o registry responde
-------------------------

"Que projetos existem, como se chamam, onde ficam." Nada mais.

O que ele NÃO responde é o que estes testes protegem com mais cuidado:

    estar registrado   !=   ter capacidade
    ter nome conhecido !=   ter manifesto
    editar metadata    !=   trocar de identidade
    arquivar           !=   apagar

Um projeto entra no catálogo sem ganhar permissão nenhuma. A permissão efetiva
continua sendo a interseção de executor, projeto e política, e um projeto sem
Capability Manifest continua produzindo `UNKNOWN` — que é a resposta segura —
em vez de um padrão generoso deduzido do nome.
"""

from __future__ import annotations

import ast
from datetime import timedelta
from pathlib import Path

import pytest

from app.modules.project_registry.repository import (
    InMemoryProjectRepository,
    LocalJsonProjectRepository,
    ProjectRepositoryConfigurationError,
    project_registry_mode,
)
from app.modules.project_registry.schemas import (
    ProjectRecord,
    ProjectRegistryError,
    ProjectStatus,
    normalize_project_id,
)
from app.modules.project_registry.seeds import SEED_PROJECTS
from app.modules.project_registry.service import ProjectRegistryService


@pytest.fixture
def registry() -> ProjectRegistryService:
    return ProjectRegistryService(InMemoryProjectRepository())


# ===========================================================================
# Semente
# ===========================================================================


def test_the_seed_projects_are_present_on_a_fresh_catalogue(registry):
    ids = {item.project_id for item in registry.list_projects()}
    assert ids == {project_id for project_id, _ in SEED_PROJECTS}


def test_the_product_keeps_its_historical_identifier(registry):
    """O nome de exibição mudou para Veltrix; a identidade não.

    Trocar a chave orfanaria o Capability Manifest, a Project Surface e todo o
    histórico de análise já gravado sob ela.
    """
    registro = registry.require("pedrocore")
    assert registro.display_name == "Veltrix"


def test_seeding_twice_does_not_overwrite_what_the_user_edited():
    store = InMemoryProjectRepository()
    ProjectRegistryService(store).update("rivvo", display_name="RIVVO Renomeado")
    # Uma instância nova semeia de novo — e não pode restaurar o nome de fábrica.
    assert ProjectRegistryService(store).require("rivvo").display_name == "RIVVO Renomeado"


def test_the_listing_follows_registration_order_not_the_alphabet(registry):
    """Alfabética elegeria como padrão do console qualquer nome começado com A."""
    nomes = [item.display_name for item in registry.list_projects()]
    assert nomes[0] == "Veltrix"


# ===========================================================================
# Criação
# ===========================================================================


def test_a_new_project_can_be_created_and_is_found_afterwards(registry):
    criado = registry.create(display_name="Meu Projeto")
    assert criado.project_id == "meu-projeto"
    assert registry.require("meu-projeto").display_name == "Meu Projeto"


def test_the_id_is_derived_from_the_name_when_not_given(registry):
    assert registry.create(display_name="Contas a Pagar").project_id == "contas-a-pagar"


def test_an_explicit_id_wins_over_the_derived_one(registry):
    criado = registry.create(display_name="Meu Projeto", project_id="mp-2026")
    assert criado.project_id == "mp-2026"


def test_a_created_project_starts_active_and_without_a_manifest(registry):
    criado = registry.create(display_name="Sem Manifesto")
    assert criado.status is ProjectStatus.ACTIVE
    assert criado.capability_manifest_reference is None


def test_creating_a_project_grants_no_capability(registry):
    """O teste que mais importa aqui: catálogo não é autorização."""
    criado = registry.create(display_name="Projeto Novo")
    assert not hasattr(criado, "permissions")
    assert not hasattr(criado, "capabilities")
    assert registry.has_manifest(criado.project_id) is False


def test_a_project_that_exists_is_never_overwritten_by_create(registry):
    """Criar por cima seria a rota mais silenciosa para roubar uma identidade."""
    with pytest.raises(ProjectRegistryError, match="Já existe"):
        registry.create(display_name="Outro Nome", project_id="pedrocore")
    assert registry.require("pedrocore").display_name == "Veltrix"


def test_a_duplicate_is_caught_through_the_derived_id_too(registry):
    registry.create(display_name="Meu Projeto")
    with pytest.raises(ProjectRegistryError, match="Já existe"):
        registry.create(display_name="MEU PROJETO!")


# ===========================================================================
# Identidade: normalização e recusa
# ===========================================================================


def test_the_id_is_normalised_deterministically():
    assert normalize_project_id("  Minha Área 2026 ") == "minha-area-2026"
    assert normalize_project_id("Já-Existe") == "ja-existe"


def test_normalisation_is_idempotent():
    uma = normalize_project_id("Meu Projeto")
    assert normalize_project_id(uma) == uma


@pytest.mark.parametrize(
    "hostil",
    ["../etc/passwd", "..", "a/b", "a\\b", "projeto\x00nulo"],
)
def test_a_path_traversal_attempt_is_refused_not_cleaned(hostil):
    """Sanear produziria um id plausível a partir de uma tentativa de travessia."""
    with pytest.raises(ProjectRegistryError):
        normalize_project_id(hostil)


@pytest.mark.parametrize("invalido", ["", "   ", "ab", "!", "-", "x" * 100])
def test_an_unusable_id_is_refused(invalido):
    with pytest.raises(ProjectRegistryError):
        normalize_project_id(invalido)


def test_an_invalid_id_finds_nothing_instead_of_raising(registry):
    assert registry.get("../pedrocore") is None


def test_an_unknown_project_is_refused_with_a_readable_message(registry):
    with pytest.raises(ProjectRegistryError, match="desconhecido"):
        registry.require("nao-existe")


# ===========================================================================
# Metadata: caminho e repositório
# ===========================================================================


def test_a_local_path_is_optional(registry):
    assert registry.create(display_name="Sem Caminho").local_path is None


def test_a_traversing_local_path_is_refused(registry):
    with pytest.raises(ProjectRegistryError, match="diretório pai"):
        registry.create(display_name="Hostil", local_path="C:/x/../../Windows")


@pytest.mark.parametrize(
    "url",
    [
        "javascript:alert(1)",
        "file:///etc/passwd",
        "não é url",
        "https://exemplo\n.com",
    ],
)
def test_a_malformed_repository_url_is_refused(registry, url):
    with pytest.raises(ProjectRegistryError):
        registry.create(display_name="Hostil", repository_url=url)


@pytest.mark.parametrize(
    ("nome", "url"),
    [
        ("Repo Https", "https://github.com/org/repo"),
        ("Repo Scp", "git@github.com:org/repo.git"),
        ("Repo Ssh", "ssh://git@github.com/org/repo.git"),
    ],
)
def test_an_acceptable_repository_url_is_stored_as_metadata_only(registry, nome, url):
    criado = registry.create(display_name=nome, repository_url=url)
    assert criado.repository_url == url


def test_the_repository_url_is_never_fetched(registry):
    """Não há sincronização com GitHub nesta versão — nem token, nem rede.

    O teste vigia a ausência: se um dia alguém adicionar uma chamada, o
    módulo passa a importar um cliente HTTP, e isto falha.
    """
    fonte = Path("app/modules/project_registry").rglob("*.py")
    proibidos = ("httpx", "requests", "urllib.request", "aiohttp")
    for arquivo in fonte:
        texto = arquivo.read_text(encoding="utf-8")
        for termo in proibidos:
            assert termo not in texto, f"{arquivo.name} importa {termo}"


# ===========================================================================
# Edição: metadata muda, identidade não
# ===========================================================================


def test_editing_metadata_never_changes_the_project_id(registry):
    """`project_id` é chave de isolamento; editar nome não pode movê-la."""
    antes = registry.require("rivvo")
    depois = registry.update(
        "rivvo", display_name="RIVVO Plataforma", local_path="C:/Projetos/rivvo"
    )
    assert depois.project_id == antes.project_id == "rivvo"
    assert depois.display_name == "RIVVO Plataforma"


def test_update_has_no_parameter_that_could_change_the_identity():
    """A garantia é da assinatura, não da disciplina de quem chama."""
    import inspect

    parametros = set(inspect.signature(ProjectRegistryService.update).parameters)
    assert "project_id" in parametros  # é o alvo…
    assert parametros & {"new_project_id", "identity", "rename_id"} == set()


def test_editing_preserves_the_creation_instant(registry):
    antes = registry.require("structa")
    depois = registry.update("structa", display_name="Structa 2")
    assert depois.created_at == antes.created_at
    assert depois.updated_at >= antes.updated_at


def test_editing_revalidates_instead_of_trusting_the_caller(registry):
    with pytest.raises(ProjectRegistryError):
        registry.update("structa", local_path="../../etc")


def test_editing_one_project_does_not_touch_another(registry):
    """Isolamento entre projetos, na escrita."""
    antes = registry.require("elyra").model_dump()
    registry.update("structa", display_name="Structa Alterada")
    assert registry.require("elyra").model_dump() == antes


# ===========================================================================
# Arquivamento
# ===========================================================================


def test_an_archived_project_leaves_the_normal_flow(registry):
    registry.archive("orlabyte")
    ativos = {item.project_id for item in registry.list_projects()}
    assert "orlabyte" not in ativos


def test_an_archived_project_still_exists_and_keeps_its_identity(registry):
    registry.archive("orlabyte")
    registro = registry.require("orlabyte")
    assert registro.status is ProjectStatus.ARCHIVED
    assert registro.project_id == "orlabyte"


def test_an_archived_id_cannot_be_reused_by_a_new_project(registry):
    """Herdar o id de um projeto arquivado seria herdar o histórico dele."""
    registry.archive("orlabyte")
    with pytest.raises(ProjectRegistryError, match="Já existe"):
        registry.create(display_name="Outra Coisa", project_id="orlabyte")


def test_an_archived_project_can_be_restored(registry):
    registry.archive("orlabyte")
    registry.restore("orlabyte")
    assert "orlabyte" in {item.project_id for item in registry.list_projects()}


def test_the_service_offers_no_destructive_delete():
    """Arquivar preserva; apagar não é oferecido por padrão."""
    metodos = {name for name in dir(ProjectRegistryService) if not name.startswith("_")}
    assert metodos & {"delete", "remove", "destroy", "drop"} == set()


# ===========================================================================
# Persistência
# ===========================================================================


def test_a_project_survives_a_restart_with_the_json_store(tmp_path: Path):
    """Restart verificável: uma instância nova enxerga o que a anterior gravou."""
    primeira = ProjectRegistryService(LocalJsonProjectRepository(tmp_path))
    primeira.create(display_name="Persistente", local_path="C:/Projetos/persistente")

    segunda = ProjectRegistryService(LocalJsonProjectRepository(tmp_path))
    registro = segunda.require("persistente")
    assert registro.display_name == "Persistente"
    assert registro.local_path == "C:/Projetos/persistente"


def test_an_edit_survives_a_restart(tmp_path: Path):
    ProjectRegistryService(LocalJsonProjectRepository(tmp_path)).update(
        "elyra", display_name="Elyra QA"
    )
    segunda = ProjectRegistryService(LocalJsonProjectRepository(tmp_path))
    assert segunda.require("elyra").display_name == "Elyra QA"


def test_an_archive_survives_a_restart(tmp_path: Path):
    ProjectRegistryService(LocalJsonProjectRepository(tmp_path)).archive("rivvo")
    segunda = ProjectRegistryService(LocalJsonProjectRepository(tmp_path))
    assert segunda.require("rivvo").status is ProjectStatus.ARCHIVED


def test_writing_twice_is_idempotent(tmp_path: Path):
    servico = ProjectRegistryService(LocalJsonProjectRepository(tmp_path))
    servico.update("structa", display_name="Structa")
    servico.update("structa", display_name="Structa")
    assert len(servico.list_projects()) == len(SEED_PROJECTS)


def test_an_invalid_mode_fails_instead_of_falling_back(monkeypatch):
    """Modo inválido não vira `memory` em silêncio."""
    monkeypatch.setenv("VELTRIX_PROJECT_REGISTRY", "talvez")
    with pytest.raises(ProjectRepositoryConfigurationError):
        project_registry_mode()


def test_postgresql_without_a_url_refuses_instead_of_using_memory(monkeypatch):
    from app.modules.project_registry.repository import build_project_repository

    monkeypatch.setenv("VELTRIX_PROJECT_REGISTRY", "postgresql")
    monkeypatch.delenv("VELTRIX_PROJECT_REGISTRY_DATABASE_URL", raising=False)
    monkeypatch.delenv("VELTRIX_TEST_POSTGRES_URL", raising=False)
    monkeypatch.delenv("PEDROCORE_TEST_POSTGRES_URL", raising=False)
    with pytest.raises(ProjectRepositoryConfigurationError):
        build_project_repository()


def test_a_corrupt_catalogue_is_never_read_as_an_empty_one(tmp_path: Path):
    (tmp_path / "project_registry.json").write_text("{ isto não é json", encoding="utf-8")
    with pytest.raises(Exception, match="ilegível"):
        LocalJsonProjectRepository(tmp_path)


def test_the_store_isolates_projects_by_key():
    """Duas linhas não podem disputar a mesma identidade."""
    store = InMemoryProjectRepository()
    base = ProjectRegistryService(store).require("structa")
    store.upsert(base.model_copy(update={"display_name": "Sobrescrito"}))
    assert len([item for item in store.list_all() if item.project_id == "structa"]) == 1


# ===========================================================================
# O núcleo não conhece nome de projeto
# ===========================================================================

_CORE = (
    "app/modules/project_registry/service.py",
    "app/modules/project_registry/repository.py",
    "app/modules/project_registry/schemas.py",
    "app/modules/risk_console/domain.py",
    "app/modules/risk_intake/builder.py",
    "app/modules/risk_engine/analyzers.py",
)

_NOMES = {project_id for project_id, _ in SEED_PROJECTS} | {
    display.lower() for _, display in SEED_PROJECTS
}


def test_the_core_never_branches_on_a_project_name():
    """`if project == "finguard"` no núcleo, lido do AST.

    Seeds são configuração. Se algum dia um deles virar caso especial, um
    projeto criado pelo usuário deixa de ser cidadão de primeira classe — e é
    exatamente isso que este teste impede.
    """
    for caminho in _CORE:
        arvore = ast.parse(Path(caminho).read_text(encoding="utf-8"))
        for no in ast.walk(arvore):
            if not isinstance(no, ast.Compare):
                continue
            literais = [
                filho.value.lower()
                for filho in [no.left, *no.comparators]
                if isinstance(filho, ast.Constant) and isinstance(filho.value, str)
            ]
            assert not (set(literais) & _NOMES), (
                f"{caminho}:{no.lineno} compara com um nome de projeto"
            )


def test_a_user_created_project_behaves_like_a_seed(registry):
    """A prova positiva: nenhum caminho trata seed e projeto novo diferente."""
    novo = registry.create(display_name="Projeto Do Usuário")
    seed = registry.require("orlabyte")
    assert type(novo) is type(seed)
    assert novo.status is seed.status
    # Nenhum dos dois tem manifesto, e ambos dizem isso da mesma forma.
    assert registry.has_manifest(novo.project_id) == registry.has_manifest("orlabyte")


# ===========================================================================
# O modelo continua pequeno
# ===========================================================================


def test_the_record_stays_minimal():
    """Cada campo a mais seria um fato que o registry passaria a afirmar."""
    assert set(ProjectRecord.model_fields) == {
        "project_id",
        "display_name",
        "local_path",
        "repository_url",
        "status",
        "created_at",
        "updated_at",
        "capability_manifest_reference",
    }


def test_the_record_refuses_unknown_fields():
    from datetime import datetime, timezone

    agora = datetime.now(timezone.utc)
    with pytest.raises(Exception):
        ProjectRecord(
            project_id="x-projeto",
            display_name="X",
            created_at=agora,
            updated_at=agora,
            capabilities=["tudo"],
        )


def test_only_two_states_exist():
    assert {item.value for item in ProjectStatus} == {"ACTIVE", "ARCHIVED"}


def test_the_created_instant_is_timezone_aware(registry):
    criado = registry.create(display_name="Com Fuso")
    assert criado.created_at.tzinfo is not None
    assert criado.updated_at - criado.created_at < timedelta(seconds=5)
