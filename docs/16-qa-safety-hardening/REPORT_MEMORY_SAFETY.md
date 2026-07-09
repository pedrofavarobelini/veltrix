# Report Memory — Safety

## O que é

Memória técnica **opcional e controlada** (`app/modules/report_memory/`):
relatórios técnicos enviados por payload viram sinais e um snapshot agregado
consultável por projeto (`/api/reports/ingest`, `/api/reports/analyze`,
`/api/project-memory/{project_id}/summary`). Conteúdo é sanitizado (segredos
redigidos) antes de guardar; nada é lido de arquivo ou repositório externo.

## O que NÃO é

- **Não é treinamento**: nenhum peso de modelo é alterado, nunca.
- **Não é fine-tuning**: não existe pipeline de ajuste de modelo no PedroCore.
- **Não é autoaprendizado**: a memória não muda o comportamento do sistema
  automaticamente; ela só entra no prompt com opt-in explícito por request.
- **Não é RAG real**: é um snapshot limitado (máx. 2.000 chars) de sinais
  estruturados, não recuperação vetorial sobre corpus.

Toda task de memória (`report_ingestion`, `project_memory_summary`,
`report_memory_query`) e toda resposta de ingest/analyze carregam o warning
`REPORT_MEMORY_IS_NOT_TRAINING`.

## Defaults (imutáveis nesta frente)

| Controle | Default | Efeito |
|---|---|---|
| `PEDROCORE_REPORT_MEMORY_PERSISTENCE` | `off` | ingest retorna `disabled`/`stored=false`; snapshot `null`; valor inválido (ex.: `true`) = `off` |
| `context_from_memory` (payload) | `false` | `report_memory_service.context_block` nem é consultado; prompt sem seção `[Memória técnica]` |

Modos válidos de persistência: `off` (default), `memory` (volátil, in-process),
`local_json` (somente diretório configurado pelo operador via
`PEDROCORE_REPORT_MEMORY_DIR`).

## Garantias verificadas por teste

| Garantia | Teste |
|---|---|
| Ingest default-off: `disabled` + `stored=false` | `test_report_memory.py::test_persistence_off_by_default_and_ingest_stores_nothing` |
| Snapshot `null` sem dados (não inventa contexto) | `test_report_memory_safety.py::test_summary_returns_null_snapshot_without_data` |
| Flag inválida = off | `test_report_memory_safety.py::test_invalid_persistence_flag_value_behaves_as_off` |
| `context_from_memory` ausente = false (schema) | `test_report_memory_safety.py::test_chat_request_defaults_are_all_safe` |
| Sem flag, prompt não recebe memória (spy no Prompt Builder) | `test_report_memory_safety.py::test_memory_not_injected_into_prompt_without_flag` |
| Memória só entra com flag explícita, com nota de não-treinamento | `test_report_memory_safety.py::test_memory_injected_only_with_explicit_flag` |
| Memória não é sequer consultada sem flag | `test_report_memory_safety.py::test_context_block_never_consulted_without_flag` |
| Sem vazamento entre projetos | `test_report_memory.py::test_memory_is_isolated_by_project` + `test_report_memory_safety.py::test_memory_does_not_leak_between_projects_via_orchestrate` |
| Payload inválido falha controlado (422, sem stack) | `test_report_memory_safety.py::test_ingest_invalid_payload_fails_controlled` |
| Segredos redigidos antes de guardar | `test_report_memory.py::test_secrets_are_redacted_before_storage` |
| Eval: memória default-off não inventa persistência | fixtures `report-memory-query-no-fake-persistence`, `memory-context-disabled-by-default`, `no-memory-without-optin` |
