"""Dataset Registry — contratos de governanca de dataset.

A separacao que este modulo existe para manter
-----------------------------------------------

    DEFINICAO de dataset   !=   MATERIALIZACAO de dataset

Definir um dataset e um ato de GOVERNANCA: alguem declara qual escopo, quais
origens, qual proposito, qual politica de split e sob qual autoridade. Isso
pode e deve acontecer antes de existir um unico candidato autorizado — e o
lugar onde se decide o que se quer, nao onde se produz.

Materializar e produzir os dados. Isso exige readiness real, e nao existe
caminho que produza dataset a partir de definicao bem escrita.

Manter os dois separados e o que permite governar sem fabricar. Se definir
implicasse materializar, a unica forma de exercitar a governanca seria inventar
populacao — que e exatamente o que nao se pode fazer.

Lineage
-------

Todo dataset materializado carrega de onde veio: quais candidatos, sob quais
politicas, com qual fingerprint. Sem isso, um modelo treinado seria
inauditavel: ninguem conseguiria responder "este exemplo podia estar aqui?"
depois que a resposta importasse.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.modules.training_data.schemas import TrainingPurpose, TrainingSourceType

DATASET_REGISTRY_POLICY_VERSION = "dataset-registry-v1"

ShortText = Annotated[str, Field(min_length=1, max_length=128)]
Signature = Annotated[str, Field(pattern=r"^sha256:[0-9a-f]{64}$")]


class DatasetScope(str, Enum):
    """Abrangencia do dataset.

    `CROSS_PROJECT` e deliberadamente separado: juntar dados de projetos
    diferentes e uma decisao com consequencia de privacidade, e ela precisa ser
    declarada, e nao emergir de um filtro esquecido.
    """

    PROJECT = "project"
    CROSS_PROJECT = "cross_project"


class DatasetStatus(str, Enum):
    """Estado de uma definicao de dataset.

    `DEFINED` e o estado normal enquanto nao ha populacao suficiente. Nao e
    erro nem pendencia: e governanca pronta esperando dado real.
    """

    DEFINED = "defined"
    MATERIALIZED = "materialized"
    ARCHIVED = "archived"


class SplitPolicy(BaseModel):
    """Politica de particao treino/validacao/teste.

    As fracoes somam exatamente 1.0. Um resto silencioso significaria exemplos
    autorizados que nao entram em split nenhum — dado coletado, aprovado e
    simplesmente esquecido.
    """

    model_config = ConfigDict(extra="forbid")

    train: float = Field(default=0.8, ge=0.0, le=1.0)
    validation: float = Field(default=0.1, ge=0.0, le=1.0)
    test: float = Field(default=0.1, ge=0.0, le=1.0)
    # Agrupar por fingerprint impede que duas copias do mesmo fato caiam em
    # lados opostos do split — o vazamento classico que infla a metrica de
    # validacao sem que nada esteja tecnicamente errado no codigo.
    group_by_fingerprint: bool = True
    seed: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def _fractions_must_sum_to_one(self) -> SplitPolicy:
        total = self.train + self.validation + self.test
        if abs(total - 1.0) > 1e-9:
            raise ValueError(
                f"as frações de split devem somar 1.0 (recebido {total:.6f})"
            )
        return self


class DatasetDefinition(BaseModel):
    """Governanca declarada de um dataset — antes de existir qualquer dado."""

    model_config = ConfigDict(extra="forbid")

    policy_version: Literal["dataset-registry-v1"] = DATASET_REGISTRY_POLICY_VERSION
    dataset_id: ShortText
    display_name: ShortText
    scope: DatasetScope
    project_ids: tuple[ShortText, ...] = Field(..., min_length=1, max_length=32)
    training_purpose: TrainingPurpose
    allowed_source_types: tuple[TrainingSourceType, ...] = Field(
        ..., min_length=1, max_length=16
    )
    split_policy: SplitPolicy = Field(default_factory=SplitPolicy)
    status: DatasetStatus = DatasetStatus.DEFINED
    created_by: ShortText
    created_at: datetime
    notes: str | None = Field(default=None, max_length=2048)

    @model_validator(mode="after")
    def _scope_must_match_project_count(self) -> DatasetDefinition:
        """Escopo declarado e contagem de projetos precisam concordar.

        Um dataset `PROJECT` com tres projetos seria cross-project sem nunca ter
        sido declarado como tal — e sem a revisao que essa declaracao exige.
        """
        unique = {item.strip().lower() for item in self.project_ids}
        if self.scope is DatasetScope.PROJECT and len(unique) != 1:
            raise ValueError("escopo 'project' exige exatamente um project_id")
        if self.scope is DatasetScope.CROSS_PROJECT and len(unique) < 2:
            raise ValueError("escopo 'cross_project' exige ao menos dois project_id")
        return self

    @model_validator(mode="after")
    def _created_at_requires_timezone(self) -> DatasetDefinition:
        if self.created_at.tzinfo is None:
            raise ValueError("created_at deve incluir timezone")
        return self


class DatasetLineageEntry(BaseModel):
    """Um candidato que entrou no dataset, e sob qual autoridade."""

    model_config = ConfigDict(extra="forbid")

    candidate_id: ShortText
    project_id: ShortText
    source_type: TrainingSourceType
    fingerprint: Signature
    authorization_policy_version: ShortText
    split: Literal["train", "validation", "test"]


class DatasetVersion(BaseModel):
    """Uma materializacao concreta e imutavel.

    `content_fingerprint` cobre a COMPOSICAO da versao. Duas versoes com os
    mesmos candidatos nos mesmos splits sao a mesma versao — e poder provar
    isso e o que torna um resultado de avaliacao reproduzivel.
    """

    model_config = ConfigDict(extra="forbid")

    dataset_id: ShortText
    version: int = Field(..., ge=1)
    content_fingerprint: Signature
    materialized_at: datetime
    materialized_by: ShortText
    total_examples: int = Field(..., ge=0)
    train_examples: int = Field(..., ge=0)
    validation_examples: int = Field(..., ge=0)
    test_examples: int = Field(..., ge=0)
    lineage: tuple[DatasetLineageEntry, ...] = Field(default_factory=tuple)

    @model_validator(mode="after")
    def _counts_must_match_lineage(self) -> DatasetVersion:
        parts = self.train_examples + self.validation_examples + self.test_examples
        if parts != self.total_examples:
            raise ValueError("soma dos splits difere do total de exemplos")
        if len(self.lineage) != self.total_examples:
            raise ValueError("lineage precisa cobrir cada exemplo do dataset")
        return self


class MaterializationRefusal(BaseModel):
    """Recusa de materializacao, com o motivo real.

    Uma recusa e resposta legitima e frequente. Ela vem com os blockers de
    readiness para que a acao seja obvia: o que falta e populacao autorizada,
    nao configuracao.
    """

    model_config = ConfigDict(extra="forbid")

    status: Literal["refused"] = "refused"
    dataset_id: ShortText
    readiness: Literal["DATASET_NOT_READY"] = "DATASET_NOT_READY"
    blocker_codes: list[str] = Field(default_factory=list)
    reason: str
    # Reafirmados: recusar materializacao nunca inicia treinamento nem cria
    # dataset parcial "so para nao voltar vazio".
    canonical_dataset_created: Literal[False] = False
    training_started: Literal[False] = False
