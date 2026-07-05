# Preparação da tag v6.0.0 — PedroCore IA

## 1. Objetivo

Preparar a decisão futura de criação da tag `v6.0.0`, consolidando o estado do MVP backend após `PEDROCORE-IMPLEMENT-01`, `02` e `03`. Este documento **não cria a tag** — apenas organiza a base de decisão para quando um humano decidir criá-la.

## 2. Base atual

- Último commit no momento desta preparação: `6ed4c41 — feat: implementar MVP backend PEDROCORE-IMPLEMENT-03`.
- Frente fechada: `PEDROCORE-IMPLEMENT-03` (ver `docs/13-fechamento/FECHAMENTO_PEDROCORE_IMPLEMENT_03.md`).
- Working tree confirmado limpo antes do início da frente `PEDROCORE-FINALIZE-04`.
- Tags existentes antes de uma eventual `v6.0.0`: `v2.0.0`, `v3.0.0`, `v4.0.0`, `v5.1.9` (todas de entregas de frontend/produto; nenhuma delas cobre o backend MVP atual).

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

## 5. Checklist para criar tag futura

- [ ] Working tree limpo.
- [ ] `pytest` passando (125 passed, sem falhas).
- [ ] `compileall` passando.
- [ ] Smoke `/api/chat` passando.
- [ ] Smoke `/api/orchestrate` passando.
- [ ] `.env` intocado.
- [ ] `apps/web` intocado.
- [ ] Nenhuma tag duplicada (`v6.0.0` ainda não existe).
- [ ] Documentação atualizada e coerente.
- [ ] Decisão humana aprovada.

## 6. Comando futuro sugerido (não executar agora)

```powershell
git tag -a v6.0.0 -m "v6.0.0 - MVP backend PedroCore IA"
```

```powershell
git tag --list
```

## 7. Recomendação

Ver seção "Recomendação sobre tag" no relatório da frente `PEDROCORE-FINALIZE-04`. Este documento serve apenas de checklist e base de decisão — a decisão final é humana.
