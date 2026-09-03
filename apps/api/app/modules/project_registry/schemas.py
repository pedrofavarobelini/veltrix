"""Project Registry: quais projetos o Veltrix conhece.

O que este módulo é — e o que ele não é
----------------------------------------

É um catálogo de IDENTIDADE: nome, id, onde fica, como chamar. Nada mais.

Não é fonte de capacidade. Um projeto estar no registry não diz que ele pode
fazer migração, push ou deploy — isso continua sendo o Capability Manifest, o
Executor Profile e a Policy, e a permissão efetiva continua sendo a interseção
dos três. Registrar um projeto chamado "FinGuard" não concede nada a ninguém.

    estar no registry   !=   ter capacidade
    ter nome conhecido  !=   ter manifesto

Um projeto sem manifesto funciona: os fatos que o manifesto traria ficam
`UNKNOWN`, que é a resposta segura, e não são inventados a partir do nome.

Por que o id é normalizado e imutável
--------------------------------------

`project_id` é chave de isolamento: ele decide de quem é cada linha, cada
análise e cada contrato. Se o usuário pudesse editá-lo depois, editar metadata
viraria mudar de identidade — e um projeto poderia assumir o lugar de outro.

Por isso: normalizado na criação, único, e nunca alterável. `display_name`
muda à vontade; a identidade não.
"""

from __future__ import annotations

import re
import unicodedata
from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator

PROJECT_REGISTRY_VERSION = "project-registry-v1"

# Só o que pode ser um segmento de identificador seguro. A lista é curta de
# propósito: tudo que não está aqui é recusado em vez de ser "limpo" em
# silêncio, porque limpar silenciosamente é como `../etc` vira `etc`.
_ID_PERMITIDO = re.compile(r"^[a-z0-9][a-z0-9_-]{1,62}[a-z0-9]$")
_NAO_ALFANUMERICO = re.compile(r"[^a-z0-9]+")

# Esquemas aceitos em `repository_url`. `file:` e `javascript:` ficam de fora:
# a URL é metadado exibido a um humano, e um esquema local ou executável num
# campo de exibição é superfície sem propósito.
_ESQUEMAS_URL = ("https://", "http://", "git@", "ssh://")


class ProjectRegistryError(ValueError):
    """Entrada recusada, com mensagem em PT-BR para a superfície humana."""


class ProjectStatus(str, Enum):
    """Estado mínimo. Duas respostas bastam para a pergunta que se faz."""

    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"


def normalize_project_id(value: str) -> str:
    """Deriva um id estável e seguro, ou recusa.

    Acento vira letra base, espaço e pontuação viram hífen, caixa some. O que
    sobrar precisa passar em `_ID_PERMITIDO` — e se não passar, o erro é
    explícito.

    Recusar em vez de sanear é deliberado: `../../etc` saneado viraria um id
    plausível, e um id plausível derivado de uma tentativa de travessia é
    exatamente o que não se quer guardar.
    """
    bruto = (value or "").strip()
    if not bruto:
        raise ProjectRegistryError("Informe um identificador para o projeto.")

    # Rejeita antes de normalizar: depois da normalização, a intenção some.
    if any(marca in bruto for marca in ("..", "/", "\\", "\x00")):
        raise ProjectRegistryError(
            f"Identificador inválido: {value!r}. "
            "Separadores de caminho não são permitidos em um id de projeto."
        )

    sem_acento = "".join(
        letra for letra in unicodedata.normalize("NFKD", bruto) if not unicodedata.combining(letra)
    )
    candidato = _NAO_ALFANUMERICO.sub("-", sem_acento.lower()).strip("-")
    if not _ID_PERMITIDO.match(candidato):
        raise ProjectRegistryError(
            f"Identificador inválido: {value!r}. "
            "Use de 3 a 64 caracteres entre letras, números, hífen e sublinhado."
        )
    return candidato


def _validar_caminho(value: str | None) -> str | None:
    """Caminho local é metadado exibido; travessia não entra no catálogo."""
    if value is None:
        return None
    texto = value.strip()
    if not texto:
        return None
    if ".." in texto or "\x00" in texto:
        raise ProjectRegistryError(
            "Caminho local inválido: referências a diretório pai não são aceitas."
        )
    if len(texto) > 512:
        raise ProjectRegistryError("Caminho local longo demais (máximo 512).")
    return texto


def _validar_repositorio(value: str | None) -> str | None:
    """URL de repositório é METADADO. Nada é buscado, clonado ou autenticado.

    Não há sincronização com GitHub nesta versão — nem token, nem OAuth, nem
    chamada de rede. O campo existe para um humano reconhecer o projeto.
    """
    if value is None:
        return None
    texto = value.strip()
    if not texto:
        return None
    if len(texto) > 512:
        raise ProjectRegistryError("URL de repositório longa demais (máximo 512).")
    if any(caractere in texto for caractere in (" ", "\n", "\r", "\x00")):
        raise ProjectRegistryError("URL de repositório inválida.")
    if not texto.lower().startswith(_ESQUEMAS_URL):
        raise ProjectRegistryError(
            f"URL de repositório inválida: {value!r}. Use https://, http://, ssh:// ou git@."
        )
    return texto


class ProjectRecord(BaseModel):
    """Um projeto no catálogo.

    Deliberadamente pequeno. Cada campo a mais aqui seria um fato sobre o
    projeto que o registry passaria a afirmar — e afirmar sem base é o defeito
    que as frentes anteriores corrigiram três vezes.
    """

    model_config = ConfigDict(extra="forbid")

    project_id: str = Field(..., min_length=3, max_length=64)
    display_name: str = Field(..., min_length=1, max_length=96)
    local_path: str | None = Field(default=None, max_length=512)
    repository_url: str | None = Field(default=None, max_length=512)
    status: ProjectStatus = ProjectStatus.ACTIVE
    created_at: datetime
    updated_at: datetime
    # Ponteiro, não conteúdo. O manifesto continua morando no Project Context;
    # o registry só registra que existe um, quando existe.
    capability_manifest_reference: str | None = Field(default=None, max_length=128)

    @field_validator("project_id")
    @classmethod
    def _id_canonico(cls, value: str) -> str:
        return normalize_project_id(value)

    @field_validator("local_path")
    @classmethod
    def _caminho(cls, value: str | None) -> str | None:
        return _validar_caminho(value)

    @field_validator("repository_url")
    @classmethod
    def _repositorio(cls, value: str | None) -> str | None:
        return _validar_repositorio(value)

    @field_validator("display_name")
    @classmethod
    def _nome(cls, value: str) -> str:
        texto = value.strip()
        if not texto:
            raise ProjectRegistryError("Informe um nome para o projeto.")
        return texto

    @property
    def active(self) -> bool:
        return self.status is ProjectStatus.ACTIVE


def now() -> datetime:
    return datetime.now(timezone.utc)
