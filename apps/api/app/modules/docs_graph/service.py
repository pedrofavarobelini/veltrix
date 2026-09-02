"""Validador determinístico do grafo documental do vault Obsidian.

FINGUARD-PEDROCORE-CANONICAL-REPLAY-DOCS-GRAPH-FINALIZE-01.

Por que este módulo existe
--------------------------

O Graph View do Obsidian mostra bolinhas isoladas quando um documento não é
alcançável, mas `.obsidian/graph.json` é CONFIGURAÇÃO VISUAL — cor, zoom,
filtro. Ele não prova nada sobre a estrutura do vault e não falha em CI. A
prova estrutural precisa vir da leitura dos próprios arquivos Markdown.

O que é considerado "conectado"
-------------------------------

Um documento está conectado quando satisfaz as TRÊS condições:

  1. é alcançável a partir do MOC raiz, seguindo links;
  2. possui pelo menos um link de entrada (backlink);
  3. possui pelo menos um link de saída.

As três são independentes de propósito. Um documento pode ter backlink e ainda
ser inalcançável (componente desconectado do resto); pode ser alcançável e não
apontar para lugar nenhum (beco sem saída, que quebra a navegação de volta).

Isenções
--------

Só o MOC raiz é isento por natureza — ele não precisa de backlink. Qualquer
outra isenção precisa ser declarada explicitamente em `EXEMPT_DOCUMENTS`, com
justificativa no próprio código. Isenção genérica por padrão de caminho é
proibida: seria esconder órfão em vez de conectar.
"""

from __future__ import annotations

import re
from collections import deque
from pathlib import Path

from app.modules.docs_graph.schemas import (
    DocumentNode,
    GraphReport,
    Violation,
    ViolationKind,
)

# apps/api/app/modules/docs_graph/service.py -> repositório
REPO_ROOT = Path(__file__).resolve().parents[5]

DOCS_DIR = "Veltrix"
ROOT_MOC = "Veltrix/MOC_VELTRIX.md"

# Diretórios de configuração do Obsidian: não são documentos do vault.
IGNORED_PARTS = {".obsidian", ".git", "node_modules", "__pycache__", ".venv"}

# Isenções nominais. Vazio por decisão: nenhum documento do vault precisa de
# exceção hoje. Manter a lista vazia é o que impede que "conectar o grafo" vire
# "declarar órfão como aceitável".
EXEMPT_DOCUMENTS: frozenset[str] = frozenset()

# [[alvo]] e [[alvo|texto]]; ignora ![[embed]] de imagem por não ser navegação.
WIKILINK_PATTERN = re.compile(r"(?<!\!)\[\[([^\]\|#]+)(?:#[^\]\|]+)?(?:\|[^\]]*)?\]\]")
# [texto](caminho.md) e [texto](caminho.md#ancora)
MARKDOWN_LINK_PATTERN = re.compile(r"\[[^\]]*\]\(([^)]+?\.md)(?:#[^)]*)?\)")
# Blocos de código não contêm navegação — um exemplo de comando não é um link.
FENCED_CODE_PATTERN = re.compile(r"```.*?```", re.DOTALL)
INLINE_CODE_PATTERN = re.compile(r"`[^`\n]*`")


def _normalize(path: str) -> str:
    return path.replace("\\", "/").strip().lstrip("./")


def discover_documents(repo_root: Path = REPO_ROOT) -> list[str]:
    """Todos os Markdown do vault, em caminho relativo POSIX e ordem estável."""
    found: list[str] = []
    for candidate in sorted((repo_root / DOCS_DIR).rglob("*.md")):
        if any(part in IGNORED_PARTS for part in candidate.parts):
            continue
        found.append(_normalize(str(candidate.relative_to(repo_root))))
    return found


def strip_code(text: str) -> str:
    """Remove código antes de procurar links.

    Sem isto, um exemplo como ``[[NOME]]`` dentro de bloco de comando vira
    link quebrado e o validador passa a cobrar documentos que nunca existiram.
    """
    without_fences = FENCED_CODE_PATTERN.sub(" ", text)
    return INLINE_CODE_PATTERN.sub(" ", without_fences)


def extract_link_targets(text: str) -> list[str]:
    body = strip_code(text)
    targets = [match.group(1) for match in WIKILINK_PATTERN.finditer(body)]
    targets.extend(match.group(1) for match in MARKDOWN_LINK_PATTERN.finditer(body))
    return [target.strip() for target in targets if target.strip()]


def _resolution_index(documents: list[str]) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    """Índices de resolução: por caminho completo e por basename sem extensão."""
    by_path: dict[str, list[str]] = {}
    by_basename: dict[str, list[str]] = {}
    for path in documents:
        by_path.setdefault(path.lower(), []).append(path)
        by_path.setdefault(path.lower().removesuffix(".md"), []).append(path)
        basename = Path(path).stem
        by_basename.setdefault(basename.lower(), []).append(path)
    return by_path, by_basename


def resolve_target(
    raw_target: str,
    source: str,
    by_path: dict[str, list[str]],
    by_basename: dict[str, list[str]],
) -> tuple[str | None, bool]:
    """Resolve um link para um documento.

    Devolve `(alvo, ambiguo)`. Ambiguidade não é resolvida por heurística: um
    wikilink que casa com dois arquivos diferentes é reportado, porque o
    Obsidian também não garante qual dos dois abriria.
    """
    target = _normalize(raw_target)
    if not target:
        return None, False

    candidates = [target.lower(), f"{target.lower()}.md"]

    # Link relativo ao diretório do documento de origem.
    source_dir = str(Path(source).parent).replace("\\", "/")
    if source_dir and source_dir != ".":
        candidates.append(_normalize(f"{source_dir}/{target}").lower())
        candidates.append(_normalize(f"{source_dir}/{target}.md").lower())
    # Wikilinks do vault costumam ser relativos à raiz canônica do vault.
    candidates.append(f"{DOCS_DIR}/{target}".lower())
    candidates.append(f"{DOCS_DIR}/{target}.md".lower())

    for candidate in candidates:
        matches = by_path.get(candidate)
        if matches:
            unique = sorted(set(matches))
            return unique[0], len(unique) > 1

    matches = by_basename.get(Path(target).stem.lower())
    if matches:
        unique = sorted(set(matches))
        return unique[0], len(unique) > 1

    return None, False


def build_graph(repo_root: Path = REPO_ROOT, root_moc: str = ROOT_MOC) -> GraphReport:
    documents = discover_documents(repo_root)
    by_path, by_basename = _resolution_index(documents)
    nodes: dict[str, DocumentNode] = {
        path: DocumentNode(path=path, basename=Path(path).stem) for path in documents
    }

    for path, node in nodes.items():
        text = (repo_root / path).read_text(encoding="utf-8", errors="replace")
        for raw_target in extract_link_targets(text):
            resolved, ambiguous = resolve_target(raw_target, path, by_path, by_basename)
            if resolved is None:
                node.unresolved.append(raw_target)
                continue
            if ambiguous:
                node.ambiguous.append(raw_target)
            if resolved == path:
                # Autoligação não conecta nada; ignorada dos dois lados.
                continue
            node.outbound.add(resolved)
            nodes[resolved].inbound.add(path)

    reachable = _reachable_from(nodes, root_moc)
    violations = _collect_violations(nodes, root_moc, reachable)

    return GraphReport(
        root=root_moc,
        documents=nodes,
        violations=violations,
        exempt=EXEMPT_DOCUMENTS,
    )


def _reachable_from(nodes: dict[str, DocumentNode], root: str) -> set[str]:
    """Alcançabilidade por links de SAÍDA, que é como se navega de fato."""
    if root not in nodes:
        return set()
    seen = {root}
    queue = deque([root])
    while queue:
        current = queue.popleft()
        for neighbour in nodes[current].outbound:
            if neighbour not in seen:
                seen.add(neighbour)
                queue.append(neighbour)
    return seen


def _collect_violations(
    nodes: dict[str, DocumentNode],
    root: str,
    reachable: set[str],
) -> list[Violation]:
    violations: list[Violation] = []

    if root not in nodes:
        violations.append(
            Violation(ViolationKind.UNREACHABLE_FROM_ROOT, root, "MOC raiz nao encontrado")
        )
        return violations

    basenames: dict[str, list[str]] = {}
    for path, node in nodes.items():
        basenames.setdefault(node.basename.lower(), []).append(path)

    for basename, paths in sorted(basenames.items()):
        if len(paths) > 1:
            violations.append(
                Violation(
                    ViolationKind.DUPLICATE_BASENAME,
                    basename,
                    f"resolve para {len(paths)}: {', '.join(sorted(paths))}",
                )
            )

    for path in sorted(nodes):
        node = nodes[path]

        for target in sorted(set(node.unresolved)):
            violations.append(
                Violation(ViolationKind.BROKEN_LINK, path, f"alvo inexistente: {target}")
            )
        for target in sorted(set(node.ambiguous)):
            violations.append(
                Violation(ViolationKind.AMBIGUOUS_LINK, path, f"alvo ambiguo: {target}")
            )

        if path in EXEMPT_DOCUMENTS:
            continue

        # O MOC raiz é o único que não precisa de backlink: ele é a entrada.
        if path != root and not node.inbound:
            violations.append(Violation(ViolationKind.ORPHAN_NO_INBOUND, path))

        if not node.outbound:
            violations.append(Violation(ViolationKind.NO_OUTBOUND, path))

        if path not in reachable:
            violations.append(
                Violation(ViolationKind.UNREACHABLE_FROM_ROOT, path, f"a partir de {root}")
            )

    return violations


def main() -> int:
    report = build_graph()
    print(report.render())
    return 0 if report.ok else 1


if __name__ == "__main__":  # pragma: no cover - entrada de linha de comando
    raise SystemExit(main())
