# Fechamento — PEDROCORE-IMPLEMENT-05D — OCR local opt-in

## Implementado

- Módulo `apps/api/app/modules/ocr/` (`OCRResult`, `OCRService.extract_from_bytes`):
  - `PEDROCORE_OCR_ENABLED=false` (padrão) → `OCR_NOT_ENABLED`, nada processado;
  - flag ligada sem `pytesseract`/`PIL` instalados → `OCR_DEPENDENCY_UNAVAILABLE`, tratado sem falha (a dependência **não foi instalada** — instalação pesada requer aprovação explícita, e este ambiente não a possui);
  - flag ligada + dependência instalada pelo humano → OCR local (engine `local`, nunca serviço externo), texto truncado a 20k chars, sanitizado: se contiver segredo identificável, o texto é **descartado** (`ARTIFACT_READER_SECRET_BLOCKED`); sempre `requires_human_review=true` e `OCR_REQUIRES_HUMAN_REVIEW`.
- Integração leve no QA visual: `visual_qa_analysis` agora informa `OCR_NOT_ENABLED`/`OCR_DEPENDENCY_UNAVAILABLE`; `ocr_attempted` permanece `false` no stub.
- Release gate: evidência OCR/visual continua insuficiente para avanço (teste dedicado).

## Testes

`tests/test_ocr_guard.py` (6): desabilitado bloqueia; dependência ausente tratada; revisão humana sempre; visual reporta status do OCR; gate nunca avança com OCR-only; módulo sem bibliotecas de rede. Teste real opt-in em `test_real_optin.py` (`PEDROCORE_RUN_REAL_OCR_TESTS`), skipado por padrão.

## Garantias

Nenhum OCR executado no pytest padrão; nenhum serviço externo; nenhuma dependência instalada; release gate conservador.
