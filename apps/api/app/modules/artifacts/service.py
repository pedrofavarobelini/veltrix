import json

from app.modules.artifacts.schemas import ArtifactInput, ArtifactProcessingResult
from app.modules.contracts import codes

TEXT_ARTIFACT_TYPES = {
    "markdown",
    "qa_report",
    "log",
    "terminal_output",
    "json_result",
    "documentation",
    "changelog",
    "pending_list",
    "text",
}

VISUAL_ARTIFACT_TYPES = {"screenshot", "image", "playwright_trace", "pdf", "binary"}

# Limites conservadores de processamento textual.
MAX_ARTIFACTS = 10
MAX_ARTIFACT_CONTENT_CHARS = 20000
MAX_TOTAL_ARTIFACT_CHARS = 100000

# Campos de metadata que indicam leitura em disco — sempre rejeitados, nunca lidos.
PATH_LIKE_METADATA_KEYS = {
    "path",
    "file_path",
    "absolute_path",
    "relative_path",
    "filesystem_path",
    "local_path",
    "directory",
    "folder",
    "glob",
}

VISUAL_NOT_SUPPORTED_WARNING = (
    "Artefato visual recebido, mas análise visual ainda não está implementada."
)

ARTIFACT_LIMIT_WARNING = (
    "Quantidade de artefatos excedeu o limite seguro; alguns itens foram ignorados."
)

ARTIFACT_TRUNCATED_WARNING = (
    "Artefato truncado para limite seguro de processamento textual."
)

ARTIFACT_TOTAL_LIMIT_WARNING = (
    "Limite total de caracteres de artefatos excedido; conteúdo excedente ignorado."
)

ARTIFACT_PATH_REJECTED_WARNING = (
    "Artefato rejeitado: campos de caminho de arquivo não são suportados; "
    "leitura automática de arquivos não está implementada."
)

NO_ARTIFACTS_TEXT = "Nenhum artefato foi enviado."


class ArtifactService:
    def process(self, artifacts: list[ArtifactInput] | None) -> ArtifactProcessingResult:
        if not artifacts:
            return ArtifactProcessingResult(text_block=NO_ARTIFACTS_TEXT)

        warnings: list[str] = []
        warning_codes: list[str] = []
        types: list[str] = []
        names: list[str] = []
        blocks: list[str] = []
        analysis_parts: list[str] = []
        textual_count = 0
        rejected_count = 0
        path_rejected = False
        truncated = False
        total_chars = 0

        def add_warning(code: str, message: str) -> None:
            warnings.append(message)
            warning_codes.append(code)

        processed = artifacts
        if len(artifacts) > MAX_ARTIFACTS:
            add_warning(codes.QA_ARTIFACT_LIMIT_EXCEEDED, ARTIFACT_LIMIT_WARNING)
            processed = artifacts[:MAX_ARTIFACTS]

        for index, artifact in enumerate(processed, start=1):
            normalized_type = artifact.type.strip().lower()
            label = artifact.name or f"artefato-{index}"

            types.append(normalized_type)
            if artifact.name:
                names.append(artifact.name)

            metadata_keys = (
                {str(key).strip().lower() for key in artifact.metadata}
                if artifact.metadata
                else set()
            )
            if metadata_keys & PATH_LIKE_METADATA_KEYS:
                add_warning(codes.ARTIFACT_PATH_REJECTED, ARTIFACT_PATH_REJECTED_WARNING)
                rejected_count += 1
                path_rejected = True
                blocks.append(
                    f"- tipo: {normalized_type}\n"
                    f"  nome: {label}\n"
                    "  conteúdo: [artefato rejeitado por conter caminho de arquivo]"
                )
                continue

            if normalized_type in VISUAL_ARTIFACT_TYPES:
                add_warning(codes.ARTIFACT_VISUAL_UNSUPPORTED, VISUAL_NOT_SUPPORTED_WARNING)
                blocks.append(
                    f"- tipo: {normalized_type}\n"
                    f"  nome: {label}\n"
                    "  conteúdo: [artefato visual recebido; análise visual não implementada]"
                )
                continue

            if normalized_type not in TEXT_ARTIFACT_TYPES:
                add_warning(
                    codes.ARTIFACT_TYPE_UNKNOWN,
                    f"Tipo de artefato desconhecido: '{normalized_type}'; "
                    "tratado como texto genérico.",
                )

            content = (artifact.content or "").strip()
            if not content:
                add_warning(
                    codes.ARTIFACT_EMPTY_CONTENT,
                    f"Artefato '{label}' recebido sem conteúdo textual.",
                )
                content = "[sem conteúdo]"
            else:
                if len(content) > MAX_ARTIFACT_CONTENT_CHARS:
                    content = content[:MAX_ARTIFACT_CONTENT_CHARS]
                    add_warning(codes.ARTIFACT_TRUNCATED, ARTIFACT_TRUNCATED_WARNING)
                    truncated = True

                remaining = MAX_TOTAL_ARTIFACT_CHARS - total_chars
                if remaining <= 0:
                    content = "[conteúdo ignorado: limite total de caracteres excedido]"
                    add_warning(codes.ARTIFACT_TRUNCATED, ARTIFACT_TOTAL_LIMIT_WARNING)
                    truncated = True
                else:
                    if len(content) > remaining:
                        content = content[:remaining]
                        add_warning(codes.ARTIFACT_TRUNCATED, ARTIFACT_TOTAL_LIMIT_WARNING)
                        truncated = True
                    total_chars += len(content)
                    textual_count += 1
                    analysis_parts.append(content)

            block = f"- tipo: {normalized_type}\n  nome: {label}"
            if artifact.metadata:
                block += f"\n  metadata: {json.dumps(artifact.metadata, ensure_ascii=False)}"
            block += f"\n  conteúdo:\n{content}"
            blocks.append(block)

        return ArtifactProcessingResult(
            count=len(processed),
            types=types,
            names=names,
            warnings=warnings,
            warning_codes=warning_codes,
            text_block="\n\n".join(blocks),
            analysis_text="\n\n".join(analysis_parts),
            textual_count=textual_count,
            rejected_count=rejected_count,
            path_rejected=path_rejected,
            truncated=truncated,
        )


artifact_service = ArtifactService()
