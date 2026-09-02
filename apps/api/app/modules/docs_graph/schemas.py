"""Contratos do validador de grafo documental (DOCS-GRAPH-FINALIZE-01)."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class ViolationKind(str, Enum):
    """Tipos de defeito estrutural do vault.

    Cada um responde a uma pergunta diferente e nenhum implica o outro:
    um documento pode ter backlink e ainda assim ser inalcançável a partir da
    raiz, e um wikilink pode existir apontando para lugar nenhum.
    """

    BROKEN_LINK = "broken_link"
    AMBIGUOUS_LINK = "ambiguous_link"
    DUPLICATE_BASENAME = "duplicate_basename"
    ORPHAN_NO_INBOUND = "orphan_no_inbound"
    NO_OUTBOUND = "no_outbound"
    UNREACHABLE_FROM_ROOT = "unreachable_from_root"


@dataclass(frozen=True)
class Violation:
    kind: ViolationKind
    document: str
    detail: str = ""

    def render(self) -> str:
        suffix = f" - {self.detail}" if self.detail else ""
        return f"[{self.kind.value}] {self.document}{suffix}"


@dataclass
class DocumentNode:
    """Um documento do vault e suas arestas já resolvidas."""

    path: str
    basename: str
    outbound: set[str] = field(default_factory=set)
    inbound: set[str] = field(default_factory=set)
    unresolved: list[str] = field(default_factory=list)
    ambiguous: list[str] = field(default_factory=list)


@dataclass
class GraphReport:
    root: str
    documents: dict[str, DocumentNode]
    violations: list[Violation]
    exempt: frozenset[str]

    @property
    def total_documents(self) -> int:
        return len(self.documents)

    @property
    def total_links(self) -> int:
        return sum(len(node.outbound) for node in self.documents.values())

    @property
    def ok(self) -> bool:
        return not self.violations

    def by_kind(self, kind: ViolationKind) -> list[Violation]:
        return [item for item in self.violations if item.kind is kind]

    def render(self) -> str:
        lines = [
            "=== VELTRIX DOCS GRAPH ===",
            f"raiz: {self.root}",
            f"documentos: {self.total_documents}",
            f"links resolvidos: {self.total_links}",
            f"isentos declarados: {len(self.exempt)}",
            "",
        ]
        if self.ok:
            # Sem travessao: a saida vai para console Windows (cp1252) e um
            # caractere fora da pagina de codigo vira ruido no relatorio de QA.
            lines.append("RESULTADO: GRAFO INTEGRO - zero orfaos, zero links quebrados.")
            return "\n".join(lines)

        lines.append(f"RESULTADO: {len(self.violations)} VIOLACOES")
        for kind in ViolationKind:
            items = self.by_kind(kind)
            if not items:
                continue
            lines.append("")
            lines.append(f"-- {kind.value} ({len(items)}) --")
            lines.extend(f"   {item.render()}" for item in items)
        return "\n".join(lines)
