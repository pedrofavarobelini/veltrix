# Registro pós-tag v6.0.0 — PedroCore IA

## 1. Objetivo

Registrar o estado da tag anotada `v6.0.0` após sua criação, consolidando o fechamento do MVP backend após `PEDROCORE-IMPLEMENT-01`, `02`, `03` e `PEDROCORE-FINALIZE-04`. Este documento não move, recria nem substitui a tag; apenas registra o estado real pós-tag.

## 2. Base atual

- Commit técnico do MVP backend: `6ed4c41 — feat: implementar MVP backend PEDROCORE-IMPLEMENT-03`.
- Commit documental de consolidação: `ee2ac68 — docs: consolidar MVP e preparar tag v6`.
- Tag anotada atual: `v6.0.0`, apontando para `ee2ac68679feea6ac108abba8726d11da101576c` (`ee2ac68`).
- Mensagem da tag: `v6.0.0 - MVP backend PedroCore IA`.
- Frente fechada: `PEDROCORE-IMPLEMENT-03` (ver `docs/13-fechamento/FECHAMENTO_PEDROCORE_IMPLEMENT_03.md`).
- Frente documental fechada: `PEDROCORE-FINALIZE-04`.
- Tags existentes após o fechamento: `v2.0.0`, `v3.0.0`, `v4.0.0`, `v5.1.9`, `v6.0.0`.

## 3. Escopo consolidado do MVP

O que existe hoje no backend, de ponta a ponta:

- API FastAPI (`apps/api/app/main.py`) com `/`, `/health`, `GET /api/providers`, `POST /api/chat`, `POST /api/orchestrate`.
- **Task Router** (`task_router/`): normaliza `task_type`, define estratégia de resposta e criticidade.
- **Project Context** (`project_context/`): resolve configuração interna por `origin_system` (`pedrocore`/`finguard`/`unknown`) e avalia policy de `allowed_tasks` (sinaliza, não bloqueia).
- **Prompt Builder** (`prompt_builder/`): monta `system_prompt` enriquecido, incluindo seção de artefatos.
- **Artifacts via payload** (`artifacts/`): aceita até 10 artefatos textuais, 20k caracteres cada, 100k no total; rejeita metadata com campos de caminho de arquivo sem nunca ler disco.
- **QA textual local determinístico** (`qa_analysis/`): heurística por regex sobre o texto recebido — detecta sucesso/falha/erro/warning e risco crítico; nunca usa IA externa.
- **Release Gate conservador** (`qa_response/service.py: evaluate_release_gate`): só libera avanço com evidência limpa via análise local; mock, fallback e safe-mode-block sempre bloqueiam.
- **Safe Mode** (`orchestration/service.py`): `allow_real_provider=false` por padrão; providers reais nunca são chamados sem autorização explícita.
- **Auth interna opcional** (`orchestration/router.py`): `PEDROCORE_INTERNAL_API_KEY` + header `X-PedroCore-Api-Key`, exclusiva de `/api/orchestrate`.
- **Warning/Error contract** (`contracts/codes.py`): códigos padronizados com severidade (`info`/`warning`/`error`/`critical`).
- **Audit não persistente** (`audit/`): `audit_id`, `timestamp`, `provider_requested`/`provider_used`, `fallback_used`, `safe_mode_blocked`, `status`, `latency_ms`, `risk_level`, `can_advance` — gerado em memória, devolvido só na resposta.
- Testes backend: 125 testes cobrindo todas as camadas acima, sem depender de provider real.

## 4. O que não faz parte da v6

- Integração real com o FinGuard.
- Artifact Reader real (leitura automática de arquivo/pasta).
- Leitura real de arquivos por path recebido em payload.
- Execução de comandos por payload.
- QA visual real.
- OCR.
- Playwright.
- Agente exploratório.
- Dashboard.
- Log persistente (banco, arquivo, SQLite ou serviço externo).
- Provider real liberado em fluxo crítico sem autorização explícita.
- Blocos 7–11 do planejamento maior.
- Bloco 12.
- Blocos 13–15 finais.

## 5. Checklist de validação pós-tag

- [x] Tag anotada `v6.0.0` existe.
- [x] Tag `v6.0.0` aponta para `ee2ac68`.
- [x] Mensagem da tag: `v6.0.0 - MVP backend PedroCore IA`.
- [x] MVP backend consolidado documentalmente em `PEDROCORE-FINALIZE-04`.
- [x] `.env` e `apps/web` não fazem parte do conteúdo da tag.
- [x] A tag representa o fechamento do MVP backend, não o projeto completo.

## 6. Comando histórico de criação da tag

```powershell
git tag -a v6.0.0 -m "v6.0.0 - MVP backend PedroCore IA"
```

```powershell
git tag --list
```

Não executar estes comandos nesta microfrente. Qualquer decisão futura de mover, recriar ou substituir a tag deve ser humana e separada.

## 7. Recomendação

Manter `v6.0.0` apontando para `ee2ac68`. A próxima frente técnica pode avançar para `PEDROCORE-IMPLEMENT-04 — Expansão operacional segura — Blocos 7 a 11` sem criar, mover ou deletar tag nesta microfrente.

---

## Navegacao

- [[MOC_FECHAMENTOS]]
- [[MOC_PEDROCORE_IA]]
