import importlib.util
import io

from app.modules.artifact_reader.service import _SECRET_PATTERN
from app.modules.contracts import codes
from app.modules.ocr.schemas import OCRResult
from app.modules.real_features import service as real_features

# OCR local opt-in (IMPLEMENT-05D).
#
# Regras: desabilitado por padrão (PEDROCORE_OCR_ENABLED=false); só usa engine
# LOCAL (pytesseract/PIL) — nunca serviço externo, nunca provider real; a
# dependência NÃO é instalada por este projeto (sem instalação pesada sem
# aprovação); se indisponível, o resultado é um bloqueio seguro, não uma falha.

OCR_NOT_ENABLED_WARNING = (
    "OCR local desabilitado (PEDROCORE_OCR_ENABLED=false); "
    "imagem não foi processada."
)

OCR_DEPENDENCY_UNAVAILABLE_WARNING = (
    "Dependência local de OCR (pytesseract/PIL) não instalada; "
    "OCR não executado. Instalação requer aprovação explícita."
)

OCR_HUMAN_REVIEW_WARNING = (
    "Texto extraído por OCR local exige revisão humana; "
    "não é evidência suficiente para decisões críticas."
)

OCR_SECRET_BLOCKED_WARNING = (
    "OCR detectou conteúdo com aparência de segredo; texto descartado por segurança."
)

MAX_OCR_TEXT_CHARS = 20000


def dependency_available() -> bool:
    return (
        importlib.util.find_spec("pytesseract") is not None
        and importlib.util.find_spec("PIL") is not None
    )


class OCRService:
    def extract_from_bytes(self, image_bytes: bytes) -> OCRResult:
        if not real_features.ocr_enabled():
            return OCRResult(
                attempted=False,
                executed=False,
                warnings=[OCR_NOT_ENABLED_WARNING],
                warning_codes=[codes.OCR_NOT_ENABLED],
            )

        if not dependency_available():
            return OCRResult(
                attempted=True,
                executed=False,
                warnings=[OCR_DEPENDENCY_UNAVAILABLE_WARNING],
                warning_codes=[codes.OCR_DEPENDENCY_UNAVAILABLE],
            )

        # Caminho real: só é alcançável com flag ligada E dependência instalada
        # pelo humano. Nunca roda no pytest padrão.
        import pytesseract  # noqa: PLC0415 - import tardio deliberado (opt-in)
        from PIL import Image  # noqa: PLC0415

        image = Image.open(io.BytesIO(image_bytes))
        text = (pytesseract.image_to_string(image) or "").strip()
        text = text[:MAX_OCR_TEXT_CHARS]

        if text and _SECRET_PATTERN.search(text):
            return OCRResult(
                attempted=True,
                executed=True,
                text=None,
                warnings=[OCR_SECRET_BLOCKED_WARNING, OCR_HUMAN_REVIEW_WARNING],
                warning_codes=[
                    codes.ARTIFACT_READER_SECRET_BLOCKED,
                    codes.OCR_REQUIRES_HUMAN_REVIEW,
                ],
            )

        return OCRResult(
            attempted=True,
            executed=True,
            text=text or None,
            warnings=[OCR_HUMAN_REVIEW_WARNING],
            warning_codes=[codes.OCR_REQUIRES_HUMAN_REVIEW],
        )


ocr_service = OCRService()
