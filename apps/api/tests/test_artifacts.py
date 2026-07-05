from app.modules.artifacts.schemas import ArtifactInput
from app.modules.artifacts.service import (
    NO_ARTIFACTS_TEXT,
    VISUAL_NOT_SUPPORTED_WARNING,
    artifact_service,
)


def test_no_artifacts_returns_empty_result():
    result = artifact_service.process(None)

    assert result.count == 0
    assert result.types == []
    assert result.warnings == []
    assert result.text_block == NO_ARTIFACTS_TEXT


def test_markdown_artifact_with_content():
    result = artifact_service.process(
        [ArtifactInput(type="markdown", name="relatorio.md", content="# Relatório\nTudo ok.")]
    )

    assert result.count == 1
    assert result.types == ["markdown"]
    assert result.names == ["relatorio.md"]
    assert result.warnings == []
    assert "# Relatório" in result.text_block
    assert "relatorio.md" in result.text_block


def test_artifact_without_content_adds_warning():
    result = artifact_service.process([ArtifactInput(type="log", name="vazio.log")])

    assert result.count == 1
    assert any("sem conteúdo" in warning for warning in result.warnings)
    assert "[sem conteúdo]" in result.text_block


def test_visual_artifact_adds_not_supported_warning():
    result = artifact_service.process(
        [ArtifactInput(type="screenshot", name="tela.png", content="binario-fake")]
    )

    assert result.count == 1
    assert VISUAL_NOT_SUPPORTED_WARNING in result.warnings
    assert "análise visual não implementada" in result.text_block
    assert "binario-fake" not in result.text_block


def test_unknown_artifact_type_treated_as_text_with_warning():
    result = artifact_service.process(
        [ArtifactInput(type="tipo_inexistente", content="conteúdo qualquer")]
    )

    assert result.count == 1
    assert any("desconhecido" in warning for warning in result.warnings)
    assert "conteúdo qualquer" in result.text_block


def test_artifact_metadata_is_included_in_text_block():
    result = artifact_service.process(
        [
            ArtifactInput(
                type="qa_report",
                name="qa-2026-07-04.md",
                content="Smoke tests passaram.",
                metadata={"module": "personal-finance"},
            )
        ]
    )

    assert result.warnings == []
    assert '"module": "personal-finance"' in result.text_block
    assert "Smoke tests passaram." in result.text_block
