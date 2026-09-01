"""Métrica quantitativa de alcance do blast radius (Stage R3, resolve P3).

O problema
----------

`BlastRadius` descrevia alcance de forma qualitativa — listas de arquivos,
módulos, banco, permissões — mais uma `magnitude` categórica. Sem número
comparável, duas análises não podiam ser ordenadas por alcance, e o histórico
não conseguia aprender "isto atingiu mais do que aquilo".

O que esta métrica é — e o que ela NÃO é
-----------------------------------------

Ela mede **alcance**, não perigo. Alterar 40 arquivos de teste tem alcance
maior e severidade menor que alterar um único arquivo de credencial. Misturar
as duas coisas produziria um número que não responde nenhuma das duas
perguntas.

Por isso a métrica é deliberadamente **separada** de `RiskSeverity`, das
dimensões de risco e do gate de execução. Ela não entra no cálculo do gate: um
`BLOCK` continua vindo de escopo proibido, permissão ausente, operação
desconhecida ou segredo em produção.

Sem pesos arbitrários
---------------------

Não há "banco vale 3, arquivo vale 1". Pesar fronteiras exigiria uma teoria
sobre qual delas é pior, e essa teoria seria inventada aqui. O que se conta é
o que dá para contar sem opinar:

- `boundary_breadth` — quantas fronteiras distintas foram tocadas (0–8);
- `item_extent` — quantos itens distintos, somados;
- `boundary_counts` — a contagem por fronteira, para que o número seja
  explicável e auditável item a item.

Quem quiser ponderar fronteiras faz isso depois, com política própria e
versionada — e a métrica crua continua disponível para conferir.

Propriedades garantidas por teste
---------------------------------

- **determinística** — mesma entrada, mesmo resultado, sempre;
- **invariante a ordem** — listas reordenadas produzem o mesmo número;
- **invariante a duplicata** — o mesmo alvo repetido conta uma vez;
- **monotônica** — acrescentar alvo nunca diminui o alcance;
- **versionada** — `metric_version` permite evoluir sem reinterpretar
  silenciosamente números antigos.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

BLAST_RADIUS_METRIC_VERSION = "blast-radius-metric-v1"

# As fronteiras que o `BlastRadius` V1 ja descrevia. A metrica nao inventa
# categoria nova: ela conta o que o dominio ja declarava.
BOUNDARY_FIELDS: tuple[str, ...] = (
    "files",
    "modules",
    "database",
    "users",
    "permissions",
    "environments",
    "external_integrations",
    "security_boundaries",
)

MAX_BOUNDARY_BREADTH = len(BOUNDARY_FIELDS)

ShortText = Annotated[str, Field(min_length=1, max_length=64)]


class BlastRadiusMetric(BaseModel):
    """Alcance quantificado, explicável e comparável entre análises."""

    model_config = ConfigDict(extra="forbid")

    metric_version: Literal["blast-radius-metric-v1"] = BLAST_RADIUS_METRIC_VERSION

    # Quantas fronteiras DISTINTAS foram tocadas. Atingir arquivos e banco e
    # mais amplo que atingir dois arquivos, mesmo que os dois arquivos sejam
    # muitos itens.
    boundary_breadth: int = Field(..., ge=0, le=MAX_BOUNDARY_BREADTH)

    # Quantos itens distintos no total, somados entre fronteiras.
    item_extent: int = Field(..., ge=0)

    # A conta aberta. Sem isto o numero seria uma opiniao; com isto, ele e
    # verificavel item a item por quem for auditar a decisao.
    boundary_counts: dict[str, int] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _counts_must_explain_the_totals(self) -> BlastRadiusMetric:
        """O agregado tem que bater com o detalhe.

        Um total que nao decorre das contagens tornaria a metrica impossivel
        de conferir — e uma metrica que nao se confere e um numero bonito.
        """
        unknown = set(self.boundary_counts) - set(BOUNDARY_FIELDS)
        if unknown:
            raise ValueError(f"fronteiras desconhecidas: {sorted(unknown)}")
        if any(value < 0 for value in self.boundary_counts.values()):
            raise ValueError("contagem de fronteira não pode ser negativa")
        touched = sum(1 for value in self.boundary_counts.values() if value > 0)
        if touched != self.boundary_breadth:
            raise ValueError(
                "boundary_breadth diverge das fronteiras efetivamente tocadas"
            )
        if sum(self.boundary_counts.values()) != self.item_extent:
            raise ValueError("item_extent diverge da soma das contagens")
        return self


def compute_blast_radius_metric(blast_radius) -> BlastRadiusMetric:
    """Deriva a métrica a partir do `BlastRadius` já produzido pelo motor.

    Usa `set` por fronteira: o mesmo alvo listado duas vezes é um alvo, e a
    ordem em que ele aparece não é informação. As duas invariâncias saem daí,
    e não de uma normalização feita depois.
    """
    counts: dict[str, int] = {}
    for field in BOUNDARY_FIELDS:
        items = getattr(blast_radius, field, None) or ()
        distinct = {str(item).strip() for item in items if str(item).strip()}
        if distinct:
            counts[field] = len(distinct)
    return BlastRadiusMetric(
        boundary_breadth=len(counts),
        item_extent=sum(counts.values()),
        boundary_counts=counts,
    )
