import json

from app.modules.artifacts.schemas import ArtifactInput, ArtifactProcessingResult

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

VISUAL_ARTIFACT_TYPES = {"screenshot", "image", "playwright_trace"}

VISUAL_NOT_SUPPORTED_WARNING = (
    "Artefato visual recebido, mas análise visual ainda não está implementada."
)

NO_ARTIFACTS_TEXT = "Nenhum artefato foi enviado."

# TODO: definir limites de tamanho para conteúdo de artefatos em etapa futura.


class ArtifactService:
    def process(self, artifacts: list[ArtifactInput] | None) -> ArtifactProcessingResult:
        if not artifacts:
            return ArtifactProcessingResult(text_block=NO_ARTIFACTS_TEXT)

        warnings: list[str] = []
        types: list[str] = []
        names: list[str] = []
        blocks: list[str] = []

        for index, artifact in enumerate(artifacts, start=1):
            normalized_type = artifact.type.strip().lower()
            label = artifact.name or f"artefato-{index}"

            types.append(normalized_type)
            if artifact.name:
                names.append(artifact.name)

            if normalized_type in VISUAL_ARTIFACT_TYPES:
                warnings.append(VISUAL_NOT_SUPPORTED_WARNING)
                blocks.append(
                    f"- tipo: {normalized_type}\n"
                    f"  nome: {label}\n"
                    "  conteúdo: [artefato visual recebido; análise visual não implementada]"
                )
                continue

            if normalized_type not in TEXT_ARTIFACT_TYPES:
                warnings.append(
                    f"Tipo de artefato desconhecido: '{normalized_type}'; "
                    "tratado como texto genérico."
                )

            content = (artifact.content or "").strip()
            if not content:
                warnings.append(f"Artefato '{label}' recebido sem conteúdo textual.")
                content = "[sem conteúdo]"

            block = f"- tipo: {normalized_type}\n  nome: {label}"
            if artifact.metadata:
                block += f"\n  metadata: {json.dumps(artifact.metadata, ensure_ascii=False)}"
            block += f"\n  conteúdo:\n{content}"
            blocks.append(block)

        return ArtifactProcessingResult(
            count=len(artifacts),
            types=types,
            names=names,
            warnings=warnings,
            text_block="\n\n".join(blocks),
        )


artifact_service = ArtifactService()
