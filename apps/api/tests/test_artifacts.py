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


def test_large_artifact_is_truncated_with_warning():
    result = artifact_service.process(
        [ArtifactInput(type="log", name="grande.log", content="x" * 25000)]
    )

    assert result.truncated is True
    assert "ARTIFACT_TRUNCATED" in result.warning_codes
    assert "x" * 20001 not in result.text_block
    assert "x" * 20000 in result.analysis_text


def test_too_many_artifacts_are_limited_with_warning():
    artifacts = [
        ArtifactInput(type="text", name=f"a{i}.txt", content=f"conteudo {i}")
        for i in range(12)
    ]
    result = artifact_service.process(artifacts)

    assert result.count == 10
    assert "QA_ARTIFACT_LIMIT_EXCEEDED" in result.warning_codes
    assert "conteudo 11" not in result.text_block


def test_total_char_limit_is_enforced():
    artifacts = [
        ArtifactInput(type="log", name=f"l{i}.log", content=("y" * 19000))
        for i in range(6)
    ]
    result = artifact_service.process(artifacts)

    assert result.truncated is True
    assert "ARTIFACT_TRUNCATED" in result.warning_codes
    assert len(result.analysis_text) <= 100000 + len(artifacts) * 2


def test_path_metadata_is_rejected_and_content_ignored():
    result = artifact_service.process(
        [
            ArtifactInput(
                type="qa_report",
                name="externo.md",
                content="conteudo-que-nao-deve-ser-analisado",
                metadata={"path": "C:\\Projetos\\qualquer\\arquivo.md"},
            )
        ]
    )

    assert result.path_rejected is True
    assert result.rejected_count == 1
    assert "ARTIFACT_PATH_REJECTED" in result.warning_codes
    assert "conteudo-que-nao-deve-ser-analisado" not in result.text_block
    assert "conteudo-que-nao-deve-ser-analisado" not in result.analysis_text


def test_file_path_and_absolute_path_keys_are_rejected():
    for key in ["file_path", "absolute_path", "relative_path", "directory", "glob"]:
        result = artifact_service.process(
            [
                ArtifactInput(
                    type="text",
                    content="abc",
                    metadata={key: "qualquer-valor"},
                )
            ]
        )
        assert result.path_rejected is True, f"chave nao rejeitada: {key}"
        assert "ARTIFACT_PATH_REJECTED" in result.warning_codes


def test_real_local_file_is_never_read(tmp_path):
    real_file = tmp_path / "segredo-local.txt"
    real_file.write_text("CONTEUDO-REAL-DO-DISCO-NUNCA-LIDO", encoding="utf-8")

    result = artifact_service.process(
        [
            ArtifactInput(
                type="text",
                name="segredo-local.txt",
                metadata={"path": str(real_file)},
            )
        ]
    )

    assert result.path_rejected is True
    assert "CONTEUDO-REAL-DO-DISCO-NUNCA-LIDO" not in result.text_block
    assert "CONTEUDO-REAL-DO-DISCO-NUNCA-LIDO" not in result.analysis_text
