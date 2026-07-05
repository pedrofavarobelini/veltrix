from pydantic import BaseModel, Field


class ArtifactReadResult(BaseModel):
    """Resultado de uma tentativa de leitura controlada de arquivo.

    O conteúdo só é preenchido quando a leitura foi permitida por todas as
    regras de segurança (reader habilitado, allowlist, extensão, tamanho,
    sem binário, sem segredo, sem .env, sem FinGuard).
    """

    allowed: bool = False
    file_name: str | None = None
    content: str | None = None
    chars_read: int = 0
    warnings: list[str] = Field(default_factory=list)
    warning_codes: list[str] = Field(default_factory=list)
