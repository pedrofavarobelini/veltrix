import os
import re
from pathlib import Path

from app.modules.artifact_reader.schemas import ArtifactReadResult
from app.modules.contracts import codes

# Artifact Reader real controlado por allowlist (Bloco 9).
#
# Este é o ÚNICO módulo do PedroCore autorizado a ler arquivos do disco, e
# somente sob todas as condições abaixo:
#   - PEDROCORE_ARTIFACT_READER_ENABLED=true (desabilitado por padrão);
#   - caminho resolvido dentro de PEDROCORE_ARTIFACT_ALLOWED_DIRS;
#   - extensão em PEDROCORE_ARTIFACT_ALLOWED_EXTENSIONS;
#   - sem path traversal, sem .env, sem binário, sem segredo identificável;
#   - nunca para caminhos do FinGuard (bloqueio explícito nesta frente).
# O reader nunca escreve, nunca deleta e nunca executa nada.

ENV_ENABLED = "PEDROCORE_ARTIFACT_READER_ENABLED"
ENV_ALLOWED_DIRS = "PEDROCORE_ARTIFACT_ALLOWED_DIRS"
ENV_MAX_FILE_CHARS = "PEDROCORE_ARTIFACT_MAX_FILE_CHARS"
ENV_MAX_TOTAL_CHARS = "PEDROCORE_ARTIFACT_MAX_TOTAL_CHARS"
ENV_ALLOWED_EXTENSIONS = "PEDROCORE_ARTIFACT_ALLOWED_EXTENSIONS"

DEFAULT_MAX_FILE_CHARS = 20000
DEFAULT_MAX_TOTAL_CHARS = 100000
DEFAULT_ALLOWED_EXTENSIONS = ".txt,.md,.log,.json,.csv"

READER_DISABLED_WARNING = (
    "Artifact Reader desabilitado (PEDROCORE_ARTIFACT_READER_ENABLED=false); "
    "leitura por path não realizada."
)
READER_USED_WARNING = (
    "Artifact Reader controlado utilizado: arquivo allowlisted lido como artefato textual."
)
READER_PATH_NOT_ALLOWED_WARNING = (
    "Caminho fora da allowlist do Artifact Reader; leitura bloqueada."
)
READER_FINGUARD_BLOCKED_WARNING = (
    "Leitura de caminhos do FinGuard não é permitida nesta frente; leitura bloqueada."
)
READER_TRAVERSAL_WARNING = (
    "Path traversal detectado; leitura bloqueada."
)
READER_ENV_BLOCKED_WARNING = (
    "Leitura de arquivos .env é proibida; leitura bloqueada."
)
READER_EXTENSION_BLOCKED_WARNING = (
    "Extensão de arquivo não permitida pelo Artifact Reader; leitura bloqueada."
)
READER_FILE_TOO_LARGE_WARNING = (
    "Arquivo excede o limite de caracteres do Artifact Reader; leitura bloqueada."
)
READER_TOTAL_LIMIT_WARNING = (
    "Limite total de leitura do Artifact Reader excedido nesta requisição; leitura bloqueada."
)
READER_BINARY_BLOCKED_WARNING = (
    "Arquivo binário ou não decodificável como texto; leitura bloqueada."
)
READER_SECRET_BLOCKED_WARNING = (
    "Conteúdo com aparência de segredo (senha/token/chave) detectado; leitura bloqueada."
)

_SECRET_PATTERN = re.compile(
    r"(password|senha|secret|api[_-]?key|token|private[_-]?key)\s*[=:]\s*\S+"
    r"|-----BEGIN [A-Z ]*PRIVATE KEY-----",
    re.IGNORECASE,
)


def _blocked(code: str, message: str) -> ArtifactReadResult:
    return ArtifactReadResult(
        allowed=False,
        warnings=[message],
        warning_codes=[code],
    )


class ArtifactReaderService:
    def is_enabled(self) -> bool:
        return (os.environ.get(ENV_ENABLED) or "").strip().lower() == "true"

    def allowed_dirs(self) -> list[Path]:
        raw = (os.environ.get(ENV_ALLOWED_DIRS) or "").strip()
        dirs: list[Path] = []
        for part in raw.split(";" if ";" in raw else ","):
            part = part.strip()
            if part:
                try:
                    dirs.append(Path(part).resolve())
                except OSError:
                    continue
        return dirs

    def max_file_chars(self) -> int:
        try:
            return int(os.environ.get(ENV_MAX_FILE_CHARS) or DEFAULT_MAX_FILE_CHARS)
        except ValueError:
            return DEFAULT_MAX_FILE_CHARS

    def max_total_chars(self) -> int:
        try:
            return int(os.environ.get(ENV_MAX_TOTAL_CHARS) or DEFAULT_MAX_TOTAL_CHARS)
        except ValueError:
            return DEFAULT_MAX_TOTAL_CHARS

    def allowed_extensions(self) -> set[str]:
        raw = os.environ.get(ENV_ALLOWED_EXTENSIONS) or DEFAULT_ALLOWED_EXTENSIONS
        return {
            ext.strip().lower()
            for ext in raw.split(",")
            if ext.strip()
        }

    def read(self, requested_path: str, remaining_budget: int | None = None) -> ArtifactReadResult:
        if not self.is_enabled():
            return _blocked(codes.ARTIFACT_READER_DISABLED, READER_DISABLED_WARNING)

        raw = (requested_path or "").strip()
        if not raw:
            return _blocked(
                codes.ARTIFACT_READER_PATH_NOT_ALLOWED, READER_PATH_NOT_ALLOWED_WARNING
            )

        if ".." in raw.replace("\\", "/").split("/"):
            return _blocked(
                codes.ARTIFACT_READER_PATH_TRAVERSAL_BLOCKED, READER_TRAVERSAL_WARNING
            )

        try:
            resolved = Path(raw).resolve()
        except OSError:
            return _blocked(
                codes.ARTIFACT_READER_PATH_NOT_ALLOWED, READER_PATH_NOT_ALLOWED_WARNING
            )

        if "finguard" in str(resolved).lower():
            return _blocked(
                codes.ARTIFACT_READER_PATH_NOT_ALLOWED, READER_FINGUARD_BLOCKED_WARNING
            )

        if resolved.name.lower().startswith(".env") or resolved.name.lower() == ".env":
            return _blocked(codes.ARTIFACT_READER_ENV_BLOCKED, READER_ENV_BLOCKED_WARNING)

        allowed_dirs = self.allowed_dirs()
        inside_allowlist = any(
            resolved == base or base in resolved.parents for base in allowed_dirs
        )
        if not inside_allowlist:
            return _blocked(
                codes.ARTIFACT_READER_PATH_NOT_ALLOWED, READER_PATH_NOT_ALLOWED_WARNING
            )

        if resolved.suffix.lower() not in self.allowed_extensions():
            return _blocked(
                codes.ARTIFACT_READER_EXTENSION_BLOCKED, READER_EXTENSION_BLOCKED_WARNING
            )

        if not resolved.is_file():
            return _blocked(
                codes.ARTIFACT_READER_PATH_NOT_ALLOWED, READER_PATH_NOT_ALLOWED_WARNING
            )

        max_chars = self.max_file_chars()
        try:
            if resolved.stat().st_size > max_chars * 4:
                return _blocked(
                    codes.ARTIFACT_READER_FILE_TOO_LARGE, READER_FILE_TOO_LARGE_WARNING
                )
            raw_bytes = resolved.read_bytes()
        except OSError:
            return _blocked(
                codes.ARTIFACT_READER_PATH_NOT_ALLOWED, READER_PATH_NOT_ALLOWED_WARNING
            )

        if b"\x00" in raw_bytes:
            return _blocked(
                codes.ARTIFACT_READER_BINARY_BLOCKED, READER_BINARY_BLOCKED_WARNING
            )

        try:
            content = raw_bytes.decode("utf-8")
        except UnicodeDecodeError:
            return _blocked(
                codes.ARTIFACT_READER_BINARY_BLOCKED, READER_BINARY_BLOCKED_WARNING
            )

        if len(content) > max_chars:
            return _blocked(
                codes.ARTIFACT_READER_FILE_TOO_LARGE, READER_FILE_TOO_LARGE_WARNING
            )

        if remaining_budget is not None and len(content) > remaining_budget:
            return _blocked(
                codes.ARTIFACT_READER_TOTAL_LIMIT_EXCEEDED, READER_TOTAL_LIMIT_WARNING
            )

        if _SECRET_PATTERN.search(content):
            return _blocked(
                codes.ARTIFACT_READER_SECRET_BLOCKED, READER_SECRET_BLOCKED_WARNING
            )

        return ArtifactReadResult(
            allowed=True,
            file_name=resolved.name,
            content=content,
            chars_read=len(content),
            warnings=[READER_USED_WARNING],
            warning_codes=[codes.ARTIFACT_READER_USED],
        )


artifact_reader_service = ArtifactReaderService()
