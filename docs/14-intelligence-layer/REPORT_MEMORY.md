# Report Memory — Memória Técnica Controlada

Frente: `PEDROCORE-ECOSYSTEM-INTELLIGENCE-SUITE-01` (Fase B)
Atualizado em: 09/07/2026

Links: [[REPORT_INTELLIGENCE_FOUNDATION]] | [[../10-contratos/CONTRATO_REPORT_MEMORY]] | [[EVALUATION_FOUNDATION]]

## 1. O que é

Evolução da Report Intelligence Foundation para memória técnica **controlada e consultável**: módulo `apps/api/app/modules/report_memory/` (`schemas.py`, `repository.py`, `service.py`, `router.py`).

- `ReportMemoryEntry` — relatório ingerido + sinais + riscos + marcos.
- `ProjectMemorySnapshot` — agregado por projeto (status, riscos, sinais recorrentes, próximos passos, confiança determinística).
- Repositórios: in-memory (padrão quando habilitada) e `local_json` opcional.

## 2. O que NÃO é

- Não é treinamento, fine-tuning ou autoaprendizado — relatórios viram **sinais e histórico**, nunca pesos.
- Não é RAG/embeddings — o snapshot é agregação determinística.
- Não é banco de dados novo — in-process por padrão; `local_json` é arquivo simples opcional, default OFF.
- Não lê arquivos nem repositórios: relatórios chegam exclusivamente por payload.

## 3. Fluxo

```text
POST /api/reports/ingest
  -> normalize_report (sanitização)
  -> extract_signals (determinístico)
  -> evaluate_report_signals (crítico => revisão humana)
  -> redação de segredos ([REDACTED])
  -> repositório configurado (off | memory | local_json)
  -> memory_id + ProjectMemorySnapshot

POST /api/orchestrate (context_from_memory=true)
  -> snapshot limitado (2k chars) => seção [Memória técnica] do prompt
  -> memory_used=true + REPORT_MEMORY_USED
```

## 4. Limites e defaults

- `PEDROCORE_REPORT_MEMORY_PERSISTENCE=off` por padrão — nada guardado.
- `context_from_memory=false` por padrão — nada consultado.
- Máx. 50 entradas por projeto; snapshot lista no máximo 5 itens por categoria.
- Memória isolada por `project_id`.
- Testes de persistência usam `tmp_path`; dados de runtime não são versionados.

## 5. Testes

`apps/api/tests/test_report_memory.py`: default off, analyze sem persistência, ingestão/snapshot, criticidade de provider real, isolamento por projeto, redação de segredos, `local_json` com tmp_path, integração `context_from_memory` (off/on/disabled).
