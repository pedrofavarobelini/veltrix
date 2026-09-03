"""Capacidades técnicas: o que o executor sabe fazer, o que o projeto tem.

Por que um vocabulário novo, e não o `ProjectCapability` existente
------------------------------------------------------------------

`ProjectCapability` responde "o que este consumidor produz ou consome do
Veltrix" — `quality_evidence`, `risk_analysis`, `assistant`. É vocabulário de
INTEGRAÇÃO.

O Auto Context precisa de outra pergunta: "este pedido mexe em git? em banco?
no sistema de arquivos?". É vocabulário TÉCNICO, ortogonal ao primeiro. Forçar
os dois no mesmo enum misturaria duas perguntas diferentes — e o manifesto V1
está congelado, então estendê-lo mudaria um fingerprint.

Três camadas, três perguntas diferentes
---------------------------------------

    executor  →  o que ele CONSEGUE fazer
    projeto   →  o que existe para ser feito
    política  →  o que é permitido fazer

Nenhuma das três, sozinha, concede permissão. A permissão efetiva é a
interseção — e é isso que impede que "o prompt pediu push" vire "push
autorizado".

Sobre os registros serem dicionários
------------------------------------

`EXECUTOR_PROFILES` e `PROJECT_SURFACES` são DECLARAÇÕES, no mesmo formato de
`PROJECT_MANIFESTS`. Um projeto ou executor novo entra acrescentando uma
entrada; nenhum código muda, e não existe `if project == "..."` em lugar
nenhum. Projeto sem declaração não quebra: ele fica `UNKNOWN`, que é a resposta
segura.
"""

from __future__ import annotations

from enum import Enum
from types import MappingProxyType

from pydantic import BaseModel, ConfigDict, Field


class TechnicalCapability(str, Enum):
    """Superfície técnica que um pedido pode tocar.

    Derivada do que aparece de verdade em prompt de instrução. Uma capacidade
    sem uso real seria uma pergunta que ninguém faz.
    """

    FILESYSTEM_READ = "filesystem.read"
    FILESYSTEM_WRITE = "filesystem.write"
    TERMINAL = "terminal"
    TESTS = "tests"
    GIT_COMMIT = "git.commit"
    GIT_PUSH = "git.push"
    NETWORK = "network"
    CONTAINERS = "containers"
    DATABASE = "database"
    MIGRATION = "database.migration"
    DEPLOYMENT = "deployment"


# Termos que evidenciam cada capacidade. Casados SEMPRE através da polaridade:
# "não faça push" cita `push` e não pede push.
CAPABILITY_TERMS: dict[TechnicalCapability, tuple[str, ...]] = {
    TechnicalCapability.FILESYSTEM_READ: (
        "leia", "ler", "consulte", "revise", "inspecione", "audite", "read",
    ),
    TechnicalCapability.FILESYSTEM_WRITE: (
        "altere", "alterar", "modifique", "modificar", "edite", "editar",
        "atualize", "atualizar", "escreva", "escrever", "crie", "criar",
        "refatore", "refatorar", "corrija", "corrigir", "ajuste", "ajustar",
        "remova", "remover", "delete", "deletar", "apague", "apagar",
    ),
    TechnicalCapability.TERMINAL: (
        "execute", "executar", "rode", "rodar", "comando", "terminal", "shell",
    ),
    TechnicalCapability.TESTS: (
        "teste", "testes", "suíte", "suite", "pytest", "vitest", "cobertura",
    ),
    TechnicalCapability.GIT_COMMIT: ("commit", "commitar", "versionar"),
    TechnicalCapability.GIT_PUSH: ("push", "publique no repositório", "pushar"),
    TechnicalCapability.NETWORK: (
        "rede", "http", "api externa", "requisição externa", "download",
    ),
    TechnicalCapability.CONTAINERS: ("docker", "container", "compose", "imagem"),
    TechnicalCapability.DATABASE: (
        "banco de dados", "banco", "database", "tabela", "sql", "postgres",
    ),
    TechnicalCapability.MIGRATION: (
        "migration", "migrations", "migração", "migrar", "schema", "ddl",
    ),
    TechnicalCapability.DEPLOYMENT: ("deploy", "publicar em produção", "release"),
}


class ExecutorProfile(BaseModel):
    """O que um executor CONSEGUE fazer.

    Perfil informa capacidade; ele nunca concede autorização. Um executor com
    `git.push` continua precisando que projeto e política permitam.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    executor_id: str = Field(..., min_length=1, max_length=64)
    display_name: str = Field(..., min_length=1, max_length=64)
    capabilities: frozenset[TechnicalCapability] = Field(default_factory=frozenset)
    notes: str | None = Field(default=None, max_length=256)

    def supports(self, capability: TechnicalCapability) -> bool:
        return capability in self.capabilities


_ALL = frozenset(TechnicalCapability)

_EXECUTORS: dict[str, ExecutorProfile] = {
    "claude-code": ExecutorProfile(
        executor_id="claude-code",
        display_name="Claude Code",
        capabilities=_ALL,
        notes="Agente de terminal com acesso a arquivos, git e containers.",
    ),
    "codex": ExecutorProfile(
        executor_id="codex",
        display_name="Codex",
        capabilities=_ALL,
        notes="Agente de terminal com superfície equivalente.",
    ),
    "generic-agent": ExecutorProfile(
        executor_id="generic-agent",
        display_name="Agente genérico",
        # Conservador de proposito: agente nao identificado nao recebe git,
        # deploy, rede nem banco. Assumir capacidade e o comeco de assumir
        # permissao.
        capabilities=frozenset(
            {
                TechnicalCapability.FILESYSTEM_READ,
                TechnicalCapability.FILESYSTEM_WRITE,
                TechnicalCapability.TERMINAL,
                TechnicalCapability.TESTS,
            }
        ),
        notes="Superfície mínima; capacidade extra exige perfil declarado.",
    ),
    "manual": ExecutorProfile(
        executor_id="manual",
        display_name="Manual",
        capabilities=_ALL,
        notes="Execução humana; a capacidade é a do operador.",
    ),
}

EXECUTOR_PROFILES: MappingProxyType[str, ExecutorProfile] = MappingProxyType(_EXECUTORS)


def executor_profile(executor_id: str | None) -> ExecutorProfile | None:
    """Perfil declarado, ou `None`. Ausência não vira perfil permissivo."""
    if not executor_id:
        return None
    return _EXECUTORS.get(executor_id.strip().lower())


class ProjectSurface(BaseModel):
    """O que existe no projeto para ser tocado.

    `areas` são os nomes pelos quais o projeto se refere às próprias partes.
    Servem para inferir ALVO a partir do prompt sem adivinhação: se o texto
    não cita nenhuma área declarada, o alvo fica `UNKNOWN` em vez de virar
    "o projeto inteiro".
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    project_id: str = Field(..., min_length=1, max_length=128)
    capabilities: frozenset[TechnicalCapability] = Field(default_factory=frozenset)
    areas: tuple[str, ...] = Field(default_factory=tuple, max_length=64)

    def has(self, capability: TechnicalCapability) -> bool:
        return capability in self.capabilities


_SURFACES: dict[str, ProjectSurface] = {
    "pedrocore": ProjectSurface(
        project_id="pedrocore",
        capabilities=_ALL,
        areas=(
            "risk console",
            "risk engine",
            "policy engine",
            "control center",
            "consumer sdk",
            "model registry",
            "asset registry",
            "evaluation plane",
            "shadow mode",
            "routing",
            "audit",
            "slo",
            "compatibility",
            "disaster recovery",
            "documentação",
            "documentacao",
            "frontend",
            "backend",
            "contratos",
            "migrations",
            "testes",
        ),
    ),
}

PROJECT_SURFACES: MappingProxyType[str, ProjectSurface] = MappingProxyType(_SURFACES)


def project_surface(project_id: str | None) -> ProjectSurface | None:
    """Superfície declarada, ou `None`. Projeto sem declaração fica UNKNOWN."""
    if not project_id:
        return None
    return _SURFACES.get(project_id.strip().lower())


def area_slug(area: str) -> str:
    """`Risk Console` -> `risk_console`. Alvo é identificador, não frase."""
    return "_".join(area.strip().lower().split())
