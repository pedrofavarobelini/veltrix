"""Grafo documental do vault Obsidian (DOCS-GRAPH-FINALIZE-01).

Este teste é a prova ESTRUTURAL do grafo. O `.obsidian/graph.json` é
configuração visual — cor, zoom, filtro — e não falha quando um documento fica
órfão. A única forma de garantir "zero bolinha isolada" no Graph View é ler os
próprios arquivos Markdown e cobrar alcançabilidade, backlink e saída.
"""

from __future__ import annotations

import pytest

from app.modules.docs_graph.schemas import ViolationKind
from app.modules.docs_graph.service import (
    ROOT_MOC,
    build_graph,
    extract_link_targets,
    resolve_target,
    strip_code,
)


@pytest.fixture(scope="module")
def report():
    return build_graph()


def test_vault_encontrado(report):
    assert report.total_documents > 0, "nenhum Markdown encontrado no vault"
    assert ROOT_MOC in report.documents, "MOC raiz ausente do vault"


def test_sem_links_quebrados(report):
    quebrados = report.by_kind(ViolationKind.BROKEN_LINK)
    assert not quebrados, "wikilinks apontando para documento inexistente:\n" + "\n".join(
        item.render() for item in quebrados
    )


def test_sem_links_ambiguos(report):
    ambiguos = report.by_kind(ViolationKind.AMBIGUOUS_LINK)
    assert not ambiguos, "links que resolvem para mais de um documento:\n" + "\n".join(
        item.render() for item in ambiguos
    )


def test_sem_basename_duplicado(report):
    duplicados = report.by_kind(ViolationKind.DUPLICATE_BASENAME)
    assert not duplicados, "basenames duplicados tornam wikilinks ambiguos:\n" + "\n".join(
        item.render() for item in duplicados
    )


def test_sem_documento_orfao(report):
    orfaos = report.by_kind(ViolationKind.ORPHAN_NO_INBOUND)
    assert not orfaos, "documentos sem nenhum backlink:\n" + "\n".join(
        item.render() for item in orfaos
    )


def test_sem_beco_sem_saida(report):
    becos = report.by_kind(ViolationKind.NO_OUTBOUND)
    assert not becos, "documentos sem nenhum link de saida:\n" + "\n".join(
        item.render() for item in becos
    )


def test_tudo_alcancavel_a_partir_da_raiz(report):
    isolados = report.by_kind(ViolationKind.UNREACHABLE_FROM_ROOT)
    assert not isolados, f"documentos inalcancaveis a partir de {ROOT_MOC}:\n" + "\n".join(
        item.render() for item in isolados
    )


def test_grafo_integro(report):
    assert report.ok, report.render()


# ----------------------------------------------------------------------
# Núcleo do parser: exercitado sem tocar o vault.
# ----------------------------------------------------------------------


def test_codigo_nao_produz_link():
    """Um exemplo de comando não é navegação.

    Sem isto, `[[EXEMPLO]]` dentro de bloco de código viraria link quebrado e o
    validador passaria a cobrar documentos que nunca existiram.
    """
    texto = "```\n[[NAO_E_LINK]]\n```\ntexto `[[NEM_ESTE]]` fim [[E_LINK]]"
    alvos = extract_link_targets(texto)
    assert alvos == ["E_LINK"]
    assert "NAO_E_LINK" not in strip_code(texto)


def test_embed_de_imagem_nao_e_navegacao():
    assert extract_link_targets("![[diagrama.png]]") == []


def test_alias_e_ancora_sao_ignorados_no_alvo():
    assert extract_link_targets("[[ALVO|texto visivel]]") == ["ALVO"]
    assert extract_link_targets("[[ALVO#secao]]") == ["ALVO"]


def test_link_markdown_relativo_e_reconhecido():
    assert extract_link_targets("[rotulo](../pasta/DOC.md)") == ["../pasta/DOC.md"]


def test_resolucao_por_basename_e_por_caminho():
    documentos = ["docs/MOC_PEDROCORE_IA.md", "docs/13-fechamento/FECHAMENTO_PEDROCORE_FINAL.md"]
    by_path = {}
    by_basename = {}
    for path in documentos:
        by_path[path.lower()] = [path]
        by_path[path.lower().removesuffix(".md")] = [path]
        by_basename[path.rsplit("/", 1)[-1].removesuffix(".md").lower()] = [path]

    alvo, ambiguo = resolve_target(
        "13-fechamento/FECHAMENTO_PEDROCORE_FINAL", "docs/MOC_PEDROCORE_IA.md", by_path, by_basename
    )
    assert alvo == "docs/13-fechamento/FECHAMENTO_PEDROCORE_FINAL.md"
    assert ambiguo is False


def test_alvo_inexistente_nao_resolve():
    alvo, ambiguo = resolve_target("NAO_EXISTE", "docs/MOC_PEDROCORE_IA.md", {}, {})
    assert alvo is None
    assert ambiguo is False


def test_isencoes_sao_nominais_e_justificadas():
    """Isenção genérica esconderia órfão em vez de conectar."""
    from app.modules.docs_graph.service import EXEMPT_DOCUMENTS

    assert isinstance(EXEMPT_DOCUMENTS, frozenset)
    for item in EXEMPT_DOCUMENTS:
        assert item.endswith(".md"), "isencao deve nomear um arquivo, nunca um padrao"
