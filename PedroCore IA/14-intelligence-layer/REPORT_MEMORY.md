# Report Memory — Memória Técnica Controlada

Frente: `PEDROCORE-OPERATIONAL-PERSISTENCE` — IMPLEMENTED
Atualizado em: 20/08/2026

Links: [[REPORT_INTELLIGENCE_FOUNDATION]] | [[../10-contratos/CONTRATO_REPORT_MEMORY]] | [[EVALUATION_FOUNDATION]]

## 1. O que é

Evolução da Report Intelligence Foundation para memória técnica **controlada e consultável**: módulo `apps/api/app/modules/report_memory/` (`schemas.py`, `repository.py`, `service.py`, `router.py`).

- `ReportMemoryEntry` — relatório ingerido + sinais + riscos + marcos.
- `ProjectMemorySnapshot` — agregado por projeto (status, riscos, sinais recorrentes, próximos passos, confiança determinística).
- Repository Contract único: `InMemory`, `LocalJson` e `PostgreSQL`.

## 2. O que NÃO é

- Não é treinamento, fine-tuning ou autoaprendizado — relatórios viram **sinais e histórico**, nunca pesos.
- Não é RAG/embeddings — o snapshot é agregação determinística.
- PostgreSQL é opt-in e nunca recebe fallback silencioso para memória local.
- Não lê arquivos nem repositórios: relatórios chegam exclusivamente por payload.

## 3. Fluxo

```text
POST /api/reports/ingest
  -> normalize_report (sanitização)
  -> extract_signals (determinístico)
  -> evaluate_report_signals (crítico => revisão humana)
  -> redação de segredos ([REDACTED])
  -> repositório configurado (off | memory | local_json | postgresql)
  -> memory_id + ProjectMemorySnapshot

POST /api/orchestrate (context_from_memory=true)
  -> snapshot limitado (2k chars) => seção [Memória técnica] do prompt
  -> memory_used=true + REPORT_MEMORY_USED
```

## 4. Limites e defaults

- `PEDROCORE_REPORT_MEMORY_PERSISTENCE=off` por padrão — nada guardado.
- `context_from_memory=false` por padrão — nada consultado.
- Máx. 50 entradas por projeto apenas em `memory`/`local_json`; PostgreSQL não
  herda esse limite e expõe consulta paginada.
- Memória isolada por `project_id`.
- Testes de persistência usam `tmp_path`; dados de runtime não são versionados.

## 5. PostgreSQL, privacy e lifecycle

- URL exclusiva: `PEDROCORE_REPORT_MEMORY_DATABASE_URL`; nunca reutiliza outra
  `DATABASE_URL` implicitamente.
- Migração aditiva `migrations/0001_operational_reports.sql`, aplicada apenas
  pelo comando explícito `python -m app.modules.report_memory.migrate`.
- Campos relacionais cobrem projeto, report ID, schema, producer, correlações,
  lifecycle e timestamps; conteúdo extensível e sanitizado fica em JSONB.
- `PEDROCORE_REPORT_MEMORY_RETENTION_DAYS` define retenção (default 90 dias).
- `GET /api/project-memory/{project_id}/reports` pagina dados autorizados;
  `DELETE /api/project-memory/{project_id}` faz deleção isolada e explícita.
- Falha de configuração, conexão ou schema retorna 503
  `REPORT_PERSISTENCE_UNAVAILABLE`; nenhum repositório alternativo é usado.

## 6. Testes

`test_operational_persistence.py` prova migração idempotente, ingestão,
reconnect, query paginada, mais de 50 entradas, isolamento/IDOR, duplicidade,
retenção, deleção e falha de banco sem fallback.

## Links relacionados

- [[../MOC_QA_SAFETY_HARDENING]]
- [[../16-qa-safety-hardening/REPORT_MEMORY_SAFETY]]
- [[../10-contratos/CONTRATO_REPORT_MEMORY]]
- [[EVALUATION_FOUNDATION]]
