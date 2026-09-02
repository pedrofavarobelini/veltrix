# Contrato final FinGuard → Veltrix (integração real controlada, lado Veltrix)

Frente: `PEDROCORE-IMPLEMENT-05B`. Complementa `CONTRATO_FINGUARD_PEDROCORE.md` (Bloco 8).

## 1. O que está pronto no lado Veltrix

O Veltrix está pronto para receber chamadas HTTP reais do FinGuard em `POST /api/orchestrate`, com:

- reconhecimento de `origin_system` `finguard`/`finguard-local` (Project Context read-only);
- autenticação interna: se `PEDROCORE_INTERNAL_API_KEY` estiver configurada, o header `X-Veltrix-Api-Key` é obrigatório (401 `INTERNAL_AUTH_MISSING`/`INTERNAL_AUTH_INVALID`);
- task types permitidos: `qa_report_analysis`, `qa_failure_diagnosis`, `release_gate_review`, `exploratory_test_plan`, `manual_exploration_report`, `assisted_exploration_review`, `artifact_summary`, `technical_explanation`, `assistant_chat`, `finance_advice`, `project_status`, `report_memory_query`;
- resposta estruturada completa (`qa`, `release_gate`, `visual_qa_analysis`, `exploration`, `audit`, `warning_codes`, `blocked_reason`).

## 2. Bloqueio forte de tasks perigosas (policy enforcement)

Diferente da fase anterior (warning apenas), agora há **bloqueio real** (`status="blocked"`, `error_code=PROJECT_POLICY_BLOCKED`, provider nunca chamado) para:

- `task_type` com semântica de execução/escrita/deleção/migração/deploy (ex.: `execute_command`, `run_migration`, `delete_records`, `write_file_to_repo`, `drop_database`);
- payload com chaves de comando em `metadata`/`context` (`command`, `exec`, `shell`, `script`, etc.);
- task crítica não permitida para o projeto (`FINGUARD_TASK_NOT_ALLOWED` quando a origem é FinGuard);
- origem desconhecida em fluxo crítico.

Tasks não críticas fora da lista continuam gerando warning (`PROJECT_TASK_NOT_ALLOWED`) sem quebrar o fluxo.

## 3. Bloqueios permanentes para FinGuard

- Leitura de path real: rejeitada (`ARTIFACT_PATH_REJECTED`); Artifact Reader indisponível para origem FinGuard e para qualquer caminho contendo "finguard".
- Execução de comandos: inexistente no Veltrix; intenção de comando é bloqueada por policy.
- Escrita/commit/push no FinGuard: inexistentes.
- Provider real: bloqueado por padrão (`PROVIDER_REAL_BLOCKED`); requer `allow_real_provider=true` explícito e mesmo assim nunca aprova release gate sozinho.
- Assistente IA: FinGuard pode enviar `provider=mock|auto|gemini`; `mock` e default, `auto` escolhe Gemini somente quando autorizado e configurado, e `gemini` sem autorizacao cai em fallback seguro. `GEMINI_API_KEY` pertence somente ao ambiente Veltrix.

## 4. Testes

- Padrão (sempre rodam): payload fake aceito, todas as tasks permitidas aceitas, tasks perigosas bloqueadas, payload com comando bloqueado, origem desconhecida crítica bloqueada, reader/paths bloqueados para FinGuard, API key interna respeitada, provider real bloqueado, `/api/chat` intacto (`tests/test_finguard_enforcement.py`, `tests/test_finguard_contract.py`).
- Real-provider stubado (sempre roda): `tests/test_real_provider_policy.py` cobre `mock`, `auto`, `gemini`, chave ausente, `local_qa`, auth interna e segredo nao vazado, sem rede real.
- Fallback seguro/sem vazamento tecnico (sempre roda): `tests/test_provider_real_safety.py::test_fallback_answer_never_leaks_technical_debug_text` e `::test_fallback_answer_never_leaks_technical_debug_text_for_auto_real_provider` cobrem os 3 gatilhos de fallback (provider invalido, provider real bloqueado, `auto` sem provider real disponivel) contra uma lista de substrings tecnicas proibidas (`MockProvider`, `mock-v1`, erro bruto, etc.).
- Opt-in (skipado por padrão): `tests/test_real_optin.py::test_real_finguard_contract_roundtrip`, controlado por `PEDROCORE_RUN_REAL_FINGUARD_TESTS=true`.
- Opt-in real Gemini (skipado por padrao): `tests/test_real_optin.py::test_real_gemini_orchestrate_authorized_call`, controlado por `PEDROCORE_RUN_REAL_GEMINI_TESTS=true`.
- Validado manualmente em 2026-07-09: `provider=auto` + `allow_real_provider=true` retornou resposta conversacional real via Gemini (`provider_used=gemini`, `fallback_used=false`), sem texto tecnico/debug em nenhum cenario de fallback testado. Ver `docs/08_CHANGELOG.md`.

## 5. O que falta (fora deste repositório)

O cliente HTTP do Assistente no repositório do FinGuard já consome `/api/orchestrate` para `assistant_chat`/`finance_advice`. Integrações de QA/release gate e evoluções de produto continuam separadas por frente; o Veltrix não acessa, não lê e não altera o FinGuard real.

---

## Navegacao

- [[MOC_INTEGRACOES]]
- [[MOC_VELTRIX]]
