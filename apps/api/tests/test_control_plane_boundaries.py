"""Fronteira Runtime Plane x Learning Plane, verificada e nao apenas descrita.

ADR-PEDROCORE-CONTROL-PLANE-01.

Estes testes existem porque a Era 1 encontrou um documento de arquitetura
listando 8 endpoints quando o codigo expunha 37. Documentacao descreve a
intencao; teste PRESERVA a intencao. A fronteira dos planos e declarada em
`app/architecture/planes.py` e cobrada aqui.

Um modulo novo sem plano declarado quebra o build. Um import na direcao errada
tambem. Nenhum dos dois depende de alguem lembrar de ler um Markdown.
"""

from __future__ import annotations

import ast
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

from app.architecture.planes import (
    MODULE_PLANES,
    RUNTIME_TO_LEARNING_EXCEPTIONS,
    Plane,
    is_declared_exception,
    modules_in,
    plane_of,
)

MODULES_DIR = Path(__file__).resolve().parents[1] / "app" / "modules"

IGNORED_DIRECTORIES = {"__pycache__"}


def _discovered_modules() -> set[str]:
    """Modulos reais no disco, nao os que alguem lembrou de declarar."""
    return {
        item.name
        for item in MODULES_DIR.iterdir()
        if item.is_dir() and item.name not in IGNORED_DIRECTORIES
    }


def _imported_modules(source_file: Path) -> set[str]:
    """Modulos de `app.modules.<nome>` importados por um arquivo.

    Usa AST em vez de regex: um import dentro de uma string ou de um comentario
    nao e um import, e um regex nao sabe a diferenca.
    """
    tree = ast.parse(source_file.read_text(encoding="utf-8-sig"), filename=str(source_file))
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            parts = node.module.split(".")
            if parts[:2] == ["app", "modules"] and len(parts) >= 3:
                found.add(parts[2])
        elif isinstance(node, ast.Import):
            for alias in node.names:
                parts = alias.name.split(".")
                if parts[:2] == ["app", "modules"] and len(parts) >= 3:
                    found.add(parts[2])
    return found


def _top_level_imported_modules(source_file: Path) -> set[str]:
    """Somente imports executados no carregamento do modulo.

    Um import dentro de uma funcao nao roda na importacao, entao ele nao pode
    derrubar o carregamento do plano que o contem. A distincao entre import de
    topo e import tardio e exatamente o mecanismo que sustenta o invariante de
    disponibilidade do Assistant.
    """
    tree = ast.parse(source_file.read_text(encoding="utf-8-sig"), filename=str(source_file))
    found: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and node.module:
            parts = node.module.split(".")
            if parts[:2] == ["app", "modules"] and len(parts) >= 3:
                found.add(parts[2])
        elif isinstance(node, ast.Import):
            for alias in node.names:
                parts = alias.name.split(".")
                if parts[:2] == ["app", "modules"] and len(parts) >= 3:
                    found.add(parts[2])
    return found


def _python_files(module_name: str) -> list[Path]:
    return sorted((MODULES_DIR / module_name).glob("*.py"))


# ---------------------------------------------------------------------------
# Completude da declaracao
# ---------------------------------------------------------------------------


def test_every_module_on_disk_has_a_declared_plane():
    """Modulo novo sem plano declarado falha aqui, e nao seis meses depois."""
    undeclared = sorted(_discovered_modules() - set(MODULE_PLANES))
    assert not undeclared, (
        "Modulos sem plano declarado em app/architecture/planes.py: "
        f"{undeclared}. Declare o plano do modulo — a fronteira nao se "
        "infere pelo nome da pasta."
    )


def test_every_declared_module_exists_on_disk():
    """A declaracao nao pode descrever um sistema que nao existe mais."""
    missing = sorted(set(MODULE_PLANES) - _discovered_modules())
    assert not missing, (
        f"Modulos declarados que nao existem em app/modules/: {missing}. "
        "Remova a declaracao obsoleta."
    )


def test_planes_are_disjoint_and_complete():
    """Todo modulo pertence a exatamente um agrupamento."""
    grouped = [modules_in(plane) for plane in Plane]
    union: set[str] = set()
    for group in grouped:
        overlap = union & group
        assert not overlap, f"Modulo declarado em mais de um plano: {sorted(overlap)}"
        union |= group
    assert union == set(MODULE_PLANES)


def test_learning_plane_owns_the_dataset_foundation():
    """Dataset Foundation e responsabilidade exclusiva do PedroCore.

    Se `training_data` deixar o Learning Plane, a ADR foi violada em silencio.
    """
    assert plane_of("training_data") is Plane.LEARNING
    assert "training_data" in modules_in(Plane.LEARNING)


# ---------------------------------------------------------------------------
# Direcao da dependencia
# ---------------------------------------------------------------------------


def test_learning_plane_never_imports_orchestration_or_providers():
    """O Learning Plane consome evidencia, nao pilota execucao.

    Ele pode importar contratos de fontes do Runtime Plane — e assim que
    aprende. O que ele nao pode e alcancar o motor: orquestrar ou escolher
    provider a partir do plano de aprendizado inverteria o sistema.
    """
    forbidden = {
        "orchestration",
        "providers",
        "provider_authorization",
        "provider_binding",
        "provider_catalog",
        "provider_health",
        "shadow_routing",
        "task_router",
        "chat",
    }
    violations: list[str] = []
    for module_name in sorted(modules_in(Plane.LEARNING)):
        for source_file in _python_files(module_name):
            for imported in sorted(_imported_modules(source_file) & forbidden):
                violations.append(f"{source_file.name} -> {imported}")
    assert not violations, (
        "Learning Plane importando o motor do Runtime Plane: "
        f"{violations}. A direcao correta e Runtime --evidencia--> Learning."
    )


def test_runtime_plane_does_not_import_the_learning_plane():
    """Runtime -> Learning so por excecao declarada e justificada."""
    learning = modules_in(Plane.LEARNING)
    violations: list[str] = []
    for module_name in sorted(modules_in(Plane.RUNTIME)):
        for source_file in _python_files(module_name):
            for imported in sorted(_imported_modules(source_file) & learning):
                if is_declared_exception(module_name, imported):
                    continue
                violations.append(f"{module_name}/{source_file.name} -> {imported}")
    assert not violations, (
        f"Runtime Plane importando o Learning Plane sem excecao declarada: "
        f"{violations}. Se a dependencia for legitima, declare-a com "
        "justificativa em RUNTIME_TO_LEARNING_EXCEPTIONS."
    )


def test_declared_exceptions_are_real_and_justified():
    """Uma excecao que ninguem usa mais e divida que finge ser regra."""
    for (runtime_module, learning_module), reason in RUNTIME_TO_LEARNING_EXCEPTIONS.items():
        assert plane_of(runtime_module) is Plane.RUNTIME, runtime_module
        assert plane_of(learning_module) is Plane.LEARNING, learning_module
        assert len(reason.strip()) >= 80, (
            f"Excecao {runtime_module} -> {learning_module} sem justificativa "
            "suficiente. Uma excecao enumerada e auditavel; uma excecao "
            "sem motivo escrito nao e."
        )
        used = any(
            learning_module in _imported_modules(source_file)
            for source_file in _python_files(runtime_module)
        )
        assert used, (
            f"Excecao declarada {runtime_module} -> {learning_module} nao "
            "corresponde a nenhum import real. Remova a excecao obsoleta."
        )


def test_orchestration_defers_the_learning_plane_import():
    """O invariante de disponibilidade, cobrado na estrutura do arquivo.

    A excecao `orchestration -> training_data` so e aceitavel porque a
    maquinaria pesada (Candidate Store, repository, driver PostgreSQL) entra
    por import TARDIO. Se alguem promover esse import para o topo, o Runtime
    Plane volta a nao carregar quando o Learning Plane falhar — e este teste
    e o unico lugar que perceberia.
    """
    service = MODULES_DIR / "orchestration" / "service.py"
    top_level = _top_level_imported_modules(service)
    all_imports = _imported_modules(service)

    assert "training_data" in all_imports, (
        "A submissao governada de candidato sumiu de orchestration/service.py. "
        "Se foi movida de proposito, atualize a excecao declarada."
    )

    tree = ast.parse(service.read_text(encoding="utf-8-sig"), filename=str(service))
    heavy_at_top = [
        node.module
        for node in tree.body
        if isinstance(node, ast.ImportFrom)
        and node.module
        and node.module.startswith("app.modules.training_data.")
        and not node.module.endswith(".schemas")
    ]
    assert not heavy_at_top, (
        f"Import de topo da maquinaria do Learning Plane: {heavy_at_top}. "
        "Somente `training_data.schemas` (contrato puro) pode vir no topo; "
        "`acquisition` deve permanecer em import tardio."
    )
    # `schemas` e contrato puro e nao arrasta repository nem driver de banco.
    assert "training_data" in top_level or "training_data" in all_imports


def test_shared_kernel_does_not_depend_on_either_plane():
    """Infraestrutura transversal nao pode conhecer quem a usa.

    Se o Shared Kernel importar um plano, ele deixa de ser kernel e vira parte
    daquele plano — e o outro plano passa a atravessar a fronteira para usar
    o basico.
    """
    planes = modules_in(Plane.RUNTIME) | modules_in(Plane.LEARNING)
    violations: list[str] = []
    for module_name in sorted(modules_in(Plane.SHARED_KERNEL)):
        for source_file in _python_files(module_name):
            for imported in sorted(_imported_modules(source_file) & planes):
                violations.append(f"{module_name}/{source_file.name} -> {imported}")
    assert not violations, (
        f"Shared Kernel dependendo de um plano: {violations}. "
        "Mova o modulo para o plano que ele realmente serve, ou remova a dependencia."
    )


# ---------------------------------------------------------------------------
# Invariante de disponibilidade do Assistant
# ---------------------------------------------------------------------------


def test_runtime_plane_imports_without_the_learning_machinery():
    """O Assistant carrega mesmo se o Learning Plane estiver quebrado.

    Roda em SUBPROCESSO por necessidade, nao por preferencia. Provar isto exige
    sabotar `app.modules.training_data.acquisition` e reimportar a orquestracao;
    fazer isso no processo do pytest substituiria singletons que outros testes
    ja seguram, e a suite passaria a falhar por ordem de execucao. Isolamento de
    processo e o unico jeito honesto de fazer a pergunta.

    Antes da ADR-PEDROCORE-CONTROL-PLANE-01 este teste falhava: o import da
    maquinaria de treinamento estava no topo do modulo de orquestracao.
    """
    probe = textwrap.dedent(
        """
        import sys

        class _Blocker:
            def find_module(self, name, path=None):
                if name == "app.modules.training_data.acquisition":
                    raise ImportError("Learning Plane indisponivel (simulado).")
                return None

        sys.meta_path.insert(0, _Blocker())

        from app.modules.orchestration.service import orchestration_service

        assert orchestration_service is not None
        assert "app.modules.training_data.acquisition" not in sys.modules
        print("RUNTIME_PLANE_LOADED")
        """
    )
    result = subprocess.run(
        [sys.executable, "-c", probe],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, (
        "O Runtime Plane nao carregou sem a maquinaria do Learning Plane. "
        f"stdout={result.stdout!r} stderr={result.stderr!r}"
    )
    assert "RUNTIME_PLANE_LOADED" in result.stdout


def test_assistant_answers_while_the_candidate_store_is_disabled():
    """Se o Learning Plane nao tem onde persistir, o Assistant nao se importa.

    O Candidate Store e default-off e fail-closed. Isso nao pode custar uma
    resposta normal do Assistant — e a razao de existir da fronteira.
    """
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as client:
        response = client.post(
            "/api/chat",
            json={"message": "ping de fronteira", "provider": "mock"},
        )
    assert response.status_code == 200, response.text
    assert response.json()["answer"]


def test_candidate_store_stays_fail_closed_when_disabled():
    """A recusa e o comportamento correto: fallback silencioso mentiria.

    Um store vazio de memoria lido como se fosse o store real faria uma
    auditoria de readiness reportar numeros que nao existem.
    """
    from app.modules.report_memory.repository import ReportMemoryRepositoryConfigurationError
    from app.modules.training_data.acquisition import training_candidate_service

    with pytest.raises(ReportMemoryRepositoryConfigurationError):
        training_candidate_service.readiness(project_id="pedrocore")
