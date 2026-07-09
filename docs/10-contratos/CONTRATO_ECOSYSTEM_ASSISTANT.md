# Contrato — Ecosystem Assistant

Frente: `PEDROCORE-ECOSYSTEM-INTELLIGENCE-SUITE-01` (Fase A)
Atualizado em: 09/07/2026

Links: [[CONTRATO_ORQUESTRACAO]] | [[CONTRATO_REPORT_MEMORY]] | [[../14-intelligence-layer/INTELLIGENCE_LAYER_OVERVIEW]] | [[../00_MAPEAMENTO_GERAL_PEDROCORE]]

## 1. Princípio

O PedroCore IA é o **serviço central de IA do ecossistema**. Sistemas consumidores (FinGuard, AutoIntel, futuros projetos) consomem IA **através do backend deles → `POST /api/orchestrate`**, nunca integrando providers diretamente.

Regra inegociável: **o front-end de um sistema consumidor nunca chama provider externo diretamente.** O fluxo é sempre:

```text
Front-end do sistema consumidor
  -> backend do sistema consumidor
  -> PedroCore POST /api/orchestrate (com X-PedroCore-Api-Key quando configurada)
  -> resposta padronizada de volta ao backend consumidor
  -> front-end
```

## 2. Payload de entrada (ChatRequest)

| Campo | Default | Observação |
|---|---|---|
| `message` | obrigatório | entrada do usuário/sistema |
| `origin_system` | `"pedrocore"` | identifica o consumidor (`finguard`, `finguard-local`, ...); resolve o `project_id` |
| `task_type` | `"general_chat"` | ver seção 4 |
| `mode` | `"tecnico"` | estilo de resposta |
| `provider` | `"mock"` | `mock`, `local_qa`, `local_model` (opt-in) ou provider real (bloqueado por padrão) |
| `model` | `null` | opcional |
| `context` / `metadata` | `null` | dicionários livres; chaves de comando são bloqueadas por policy |
| `artifacts` | `null` | conteúdo textual por payload; path é rejeitado |
| `allow_real_provider` | `false` | **nunca enviar `true` sem autorização humana explícita** |
| `allow_local_model` | `false` | opt-in explícito do provider generativo local |
| `context_from_memory` | `false` | opt-in para anexar snapshot da memória técnica |

`project_id` não é campo do payload: é resolvido internamente a partir de `origin_system` pelo Project Context.

## 3. Resposta (OrchestrateResponse)

Contrato preservado e aditivo: todos os campos anteriores continuam (`status`, `answer`, `provider_used`, `provider_requested`, `warning_codes`, `warnings`, `error_code`, `blocked_reason`, `qa`, `release_gate`, `visual_qa_analysis`, `exploration`, `audit`, `safe_mode_blocked`, `allow_real_provider`...). Campo novo aditivo:

- `memory_used: bool` — `true` somente quando `context_from_memory=true` e um snapshot foi anexado.

## 4. Task types de assistente/ecossistema

| task_type | Uso | Quem pode |
|---|---|---|
| `assistant_chat` | conversa de assistente de produto | pedrocore, finguard* |
| `ecosystem_assistant` | assistente genérico do ecossistema | pedrocore |
| `finance_advice` | orientação financeira **conservadora** | pedrocore, finguard* |
| `project_status` | status consolidado de um projeto | pedrocore, finguard* |
| `report_memory_query` | consulta à memória técnica | pedrocore, finguard* |
| `local_model_chat` | chat via provider local opt-in | pedrocore |
| `evaluation_run` | execução do eval harness | pedrocore |

\* FinGuard/finguard-local participam **somente como consumidores read-only**: sem execução de comandos, sem escrita, sem leitura de repositório. `general_chat` e `report_ingestion` continuam não permitidos para FinGuard.

### finance_advice — regras obrigatórias

- Resposta sempre conservadora e **com disclaimer** anexado automaticamente pelo pipeline (`FINANCIAL_DISCLAIMER` em `warning_codes`).
- Nunca dá aconselhamento financeiro absoluto; nunca executa ação financeira; nunca altera dados; é read-only.
- Funciona com mock/local e com o futuro modelo local; provider real continua bloqueado por padrão e, mesmo autorizado no futuro, não remove o disclaimer.

## 5. AssistantResponsePayload (projeção auxiliar)

Para o backend consumidor que quer um formato de assistente pronto, existe a projeção `AssistantResponsePayload` (`orchestration/schemas.py`), montada por `OrchestrationService.build_assistant_payload(outcome)`:

`answer`, `suggestions`, `disclaimer`, `safety_flags`, `provider_used`, `model`, `audit_id`, `memory_used`, `evaluation`, `warnings`.

Ela **não substitui** `OrchestrateResponse` — é uma conveniência interna/documentada que o consumidor pode replicar do próprio JSON de resposta.

## 6. FinGuard é consumidor, não parte interna

- O FinGuard já possui estrutura de assistente/tela/botão no repositório próprio; a integração do Assistente FinGuard via PedroCore pertence à frente `FINGUARD-PEDROCORE-ASSISTANT-01` e **não foi implementada nesta frente**.
- O PedroCore não lê, não escreve e não executa nada no FinGuard; artefatos chegam por payload.
- Nenhuma regra deste contrato é específica do FinGuard a ponto de impedir outros consumidores: qualquer sistema com `origin_system` reconhecido usa o mesmo fluxo.

## 7. Segurança

- `allow_real_provider=false` é o default e o modo de operação normal; violação gera `PROVIDER_REAL_BLOCKED` + fallback Mock.
- Policy enforcement bloqueia tasks perigosas e payloads com chaves de comando antes de qualquer provider.
- Release gate só confia em `local_qa`; `local_model` e providers reais nunca aprovam sozinhos.
- Autenticação interna opcional: `PEDROCORE_INTERNAL_API_KEY` + header `X-PedroCore-Api-Key` (mesma regra para as rotas de memória técnica).
