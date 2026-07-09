# PedroCore Audit Study Map 01

Atualizado em: 09/07/2026
Frente: `PEDROCORE-AUDIT-STUDY-MAP-01`
Escopo: auditoria, validacao local e documentacao de estudo. Sem codigo novo.

## 1. Estado Git e ambiente

- Diretorio auditado: `C:\Projetos\pedrocore-ia`.
- Branch: `main`.
- HEAD: `e0ff8e3 - feat: consolidar inteligencia de ecossistema do PedroCore`.
- Commit anterior relevante: `689e50a - feat: preparar fundacao de inteligencia propria do PedroCore`.
- Tags locais: `v2.0.0`, `v3.0.0`, `v4.0.0`, `v5.1.9`, `v6.0.0`, `v7.0.0`.
- Working tree inicial: limpo. O primeiro `git status --short` exibiu apenas aviso de permissao no ignore global do usuario; a confirmacao com `git -c core.excludesfile= status --short` saiu vazia.
- `apps/api/.env`: nao tracked.
- `apps/api/.env.example`: tracked.
- `python --version`: falhou por alias local do Windows (`python.exe` em MicrosoftApps), sem impacto na suite porque `uv run` usou Python 3.13.9 da venv.
- `uv --version`: `uv 0.11.23`.

## 2. Testes automatizados

Comando:

```powershell
cd C:\Projetos\pedrocore-ia\apps\api
uv run pytest
```

Resultado:

- Coletados: 302 testes.
- Passaram: 296.
- Skipped: 6 (`test_real_optin.py`, opt-in real).
- Warnings: 2, ambos deprecations pre-existentes (`StarletteDeprecationWarning` e `PydanticDeprecatedSince20`).
- Tempo: 2.57s.
- Resultado esperado confirmado: `296 passed, 6 skipped, 2 warnings`.

Observacao operacional: o `uv run` precisou rodar fora do sandbox porque o cache do uv fica em `C:\Users\USUARIO\AppData\Local\uv\cache`. Nao houve provider real.

## 3. Eval harness

Comando:

```powershell
cd C:\Projetos\pedrocore-ia\apps\api
uv run python -m app.modules.eval_harness.run
```

Resultado:

- Total: 11 casos.
- Passed: 11.
- Failed: 0.
- Exit code: 0.
- `risk_level`: `none`.
- Providers usados nos casos: `mock` e `local_qa`.
- Nenhum provider real chamado.
- Nenhuma rede externa chamada.
- Nenhum modelo local real usado.

## 4. Rotas locais validadas

Servidor local usado apenas durante a auditoria:

```powershell
cd C:\Projetos\pedrocore-ia\apps\api
uv run uvicorn app.main:app --host 127.0.0.1 --port 3333
```

Rotas chamadas em `127.0.0.1:3333`:

- `GET /`: `status=ok`, `service=PedroCore IA`, `version=0.2.0`.
- `GET /health`: `status=ok`.
- `GET /api/providers`: retornou 7 providers (`mock`, `gemini`, `openai`, `claude`, `deepseek`, `grok`, `local_model`). `local_model` aparece `configured=false`, `real_provider=false`.
- `POST /api/chat`: respondeu via `mock`, sem fallback e sem provider real.
- `POST /api/orchestrate` com `assistant_chat`: respondeu via `mock`, `allow_real_provider=false`, `memory_used=false`.
- `POST /api/orchestrate` com `finance_advice`: respondeu via `mock`, incluiu disclaimer e warning `FINANCIAL_DISCLAIMER`.
- `POST /api/reports/analyze`: extraiu sinais de QA, `provider_real_blocked`, `database_safety_ok`, `smoke_coverage` e retornou `REPORT_MEMORY_IS_NOT_TRAINING`.
- `POST /api/reports/ingest`: retornou `status=disabled`, `stored=false`, `REPORT_MEMORY_DISABLED`.
- `GET /api/project-memory/finguard/summary`: retornou `status=disabled`, `snapshot=null`, sem inventar dados.
- `POST /api/orchestrate` com `provider=local_model` e `allow_local_model=false`: fallback mock, `LOCAL_MODEL_NOT_AUTHORIZED`.

Aviso recorrente esperado em ambiente local: `INTERNAL_AUTH_NOT_CONFIGURED`, porque `PEDROCORE_INTERNAL_API_KEY` nao esta configurada. Isso nao expos segredo; apenas indica modo dev/local sem autenticacao interna.

## 5. Arquitetura validada

Entrada publica:

- `/api/chat`: contrato legado/compatibilidade.
- `/api/orchestrate`: pipeline operacional principal.
- `/api/reports/analyze`, `/api/reports/ingest`, `/api/project-memory/{project_id}/summary`: memoria tecnica controlada.

Fluxo interno observado:

```text
ChatRequest
  -> Task Router
  -> Project Context
  -> Policy Enforcement
  -> Intelligence Layer
  -> Report Memory opcional
  -> Artifact Reader opcional
  -> Artifacts Service
  -> Prompt Builder
  -> Provider Registry / local_qa / local_model gate / fallback Mock
  -> QA Text Analyzer
  -> QA Response / Release Gate
  -> Visual QA / Exploration quando aplicavel
  -> Audit
  -> OrchestrateResponse ou ChatResponse
```

## 6. Providers

- `mock`: fallback local e provider padrao seguro.
- `local_qa`: pseudo-provider deterministico interno para QA textual/release gate. Nao aparece em `GET /api/providers` porque e tratado como caminho local no pipeline, nao como provider externo do registry.
- `local_model`: provider generativo local registrado, opt-in e default-off. Sem transport real nesta frente.
- `gemini`, `openai`, `claude`, `deepseek`, `grok`: providers reais/externos. Bloqueados por default quando `allow_real_provider=false`.

## 7. Seguranca validada

- `.env` nao esta tracked e nao foi lido.
- `allow_real_provider=true` nao foi usado.
- Providers reais nao foram chamados.
- `local_model` nao executou sem `allow_local_model=true`.
- Report Memory esta default-off e nao persistiu o payload.
- `context_from_memory=false` por default; summary vazio nao inventa snapshot.
- `finance_advice` inclui disclaimer e nao executa acao financeira.
- Release gate continua confiando somente em `local_qa`.
- Eval harness rejeita `allow_real_provider=true`.

## 8. Auditoria documental

Documentos oficiais revisados: `README.md`, `VERSION.md`, `docs/00_MAPEAMENTO_GERAL_PEDROCORE.md`, `docs/03-versoes/ROADMAP.md`, `docs/07-decisoes/DECISOES_TECNICAS.md`, `docs/08_CHANGELOG.md`, `docs/09_STATUS_ATUAL.md`, contratos em `docs/10-contratos/`, fechamentos em `docs/13-fechamento/`, docs de `docs/14-intelligence-layer/` e MOCs.

Inconsistencias factuais pequenas encontradas e corrigidas:

- `docs/09_STATUS_ATUAL.md` ainda dizia que `PEDROCORE-ECOSYSTEM-INTELLIGENCE-SUITE-01` nao estava commitada, mas o HEAD atual e `e0ff8e3`.
- `docs/08_CHANGELOG.md` ainda dizia que `PEDROCORE-MODEL-FOUNDATION-01` e `PEDROCORE-ECOSYSTEM-INTELLIGENCE-SUITE-01` estavam com commit pendente.
- `docs/14-intelligence-layer/LOCAL_MODEL_PROVIDER_CONTRACT.md` descrevia o contrato antigo como se `local_model` ainda nao tivesse sido registrado; foi mantido como historico e apontado para `LOCAL_MODEL_PROVIDER`.
- `docs/00_MAPEAMENTO_GERAL_PEDROCORE.md` recebeu ajuste para separar contrato de fundacao de provider registrado default-off.

## 9. Veredito tecnico

- Finalizado localmente como core seguro: sim, com base em Git, testes, eval harness e rotas locais.
- Pronto como core/orquestrador de IA do ecossistema: sim para uso local/controlado, mock/local_qa/report memory default-off/local_model default-off.
- Pronto como modelo proprio: nao. PedroCore nao e modelo treinado, nao faz fine-tuning, nao baixa modelo e nao tem transport generativo local real.
- FinGuard integrado como assistente real: nao. PedroCore ja aceita contrato de consumidor read-only, mas o cliente/assistente no FinGuard e frente separada.

## 10. Riscos restantes

- `PEDROCORE_INTERNAL_API_KEY` nao configurada em ambiente local: aceitavel para dev, mas nao para integracao real.
- Provider real pode chamar rede/custo se um humano configurar chave e enviar `allow_real_provider=true`.
- `local_model` ainda nao tem transport real; ativacao futura exige backend local manual e nova validacao.
- Report Memory com `local_json` e opt-in exigira governanca de diretorio, retencao e limpeza.
- Documentacao historica duplicada ainda existe; docs oficiais e MOCs devem prevalecer.

## 11. Proximos passos recomendados

1. Commitar somente docs da auditoria/estudo se aprovado.
2. Planejar `FINGUARD-PEDROCORE-ASSISTANT-01` como frente separada, sem tocar FinGuard sem autorizacao.
3. Planejar `PEDROCORE-LOCAL-MODEL-02` para transport real opt-in, atras de flag e testes reais separados.
4. Revisar autenticacao interna antes de qualquer consumidor real.
5. Manter provider real e recursos reais fora da suite padrao.

Sugestao de commit, se aprovado:

```text
docs: mapear auditoria e estudo do PedroCore
```
