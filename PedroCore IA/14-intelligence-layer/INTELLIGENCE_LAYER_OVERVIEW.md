# Intelligence Layer — Visão Geral

Frente: `PEDROCORE-MODEL-FOUNDATION-01`
Atualizado em: 08/07/2026

> **Escopo histórico da Model Foundation.** Este documento explica a camada no
> momento em que foi criada. Para o estado posterior de persistência,
> Operational Memory, Risk Engine e Training Foundation, ver
> [[PEDROCORE_FECHAMENTO_DOCUMENTAL_FINAL_ERAS_1_A_3]].

Links: [[../00_MAPEAMENTO_GERAL_PEDROCORE]] | [[REPORT_INTELLIGENCE_FOUNDATION]] | [[LOCAL_MODEL_PROVIDER_CONTRACT]] | [[EVALUATION_FOUNDATION]] | [[../13-fechamento/FECHAMENTO_PEDROCORE_MODEL_FOUNDATION_01]]

## 1. O que é

A Intelligence Layer é a fundação do PedroCore como **núcleo de inteligência operacional do ecossistema**. É uma camada determinística que prepara a decisão cognitiva/operacional ANTES do provider:

- classifica a intenção operacional (`task_type` → `response_profile`);
- define a política de contexto (`IntelligenceContextPolicy`);
- indica uso futuro de memória técnica (`memory_hints`);
- aponta necessidade de revisão humana;
- reforça o bloqueio de provider real por padrão;
- padroniza instruções e hints de avaliação para o pipeline.

## 2. O que ela NÃO é

- **Não é um modelo de IA treinado.** O PedroCore continua sendo orquestrador multi-provider.
- **Não substitui** Claude, OpenAI, Gemini, DeepSeek ou Grok.
- **Não chama provider** (local ou real), nunca.
- **Não habilita** `allow_real_provider=true` — o schema `IntelligenceContextPolicy` rejeita esse valor por validação.
- **Não altera** prompt de produção automaticamente.
- **Não persiste** memória.
- Modelo local generativo é futuro (ver [[LOCAL_MODEL_PROVIDER_CONTRACT]]).

## 3. Onde vive

- Módulo: `apps/api/app/modules/intelligence_layer/` (`schemas.py`, `service.py`).
- Integração: `OrchestrationService.execute()` chama `intelligence_layer_service.build_plan(strategy, project)` após Task Router / Project Context / Policy Enforcement e antes do Prompt Builder.
- O plano é anexado ao `OrchestrationOutcome.intelligence_plan` como **metadado interno**: não é exposto em `ChatResponse` nem em `OrchestrateResponse` nesta frente, garantindo compatibilidade total dos contratos públicos.

## 4. Schemas

### `IntelligenceContextPolicy`

| Campo | Default | Observação |
|---|---|---|
| `allow_memory_context` | `False` | memória técnica é futura |
| `allow_project_context` | `True` | Project Context já existe |
| `allow_report_context` | `False` | `True` só para tasks de relatório/QA |
| `allow_real_provider` | `False` | **imutável**: validação rejeita `True` |
| `requires_human_review` | `False` | `True` em fluxos críticos |
| `sensitive_data_policy` | `"sanitize"` | ou `"block"` |

### `IntelligencePlan`

`task_type`, `response_profile`, `context_policy`, `safety_flags`, `instructions`, `memory_hints`, `evaluation_hints`.

## 5. Response profiles

`technical_direct`, `qa_strict`, `release_gate_strict`, `financial_cautious`, `educational`, `executive_summary`, `implementation_plan`, `general_assistant`.

Mapeamento determinístico atual (resumo):

- `general_chat` → `general_assistant`
- `technical_explanation` / `code_help` / `model_foundation_review` → `technical_direct`
- `qa_report_analysis` / `qa_failure_diagnosis` / `manual_exploration_report` / `assisted_exploration_review` → `qa_strict`
- `release_gate_review` → `release_gate_strict` (+ revisão humana obrigatória)
- `artifact_summary` / `report_ingestion` / `project_memory_summary` → `executive_summary`
- `exploratory_test_plan` / `intelligence_planning` → `implementation_plan`
- `unknown` → `general_assistant`

`financial_cautious` e `educational` existem no contrato para consumidores futuros (ex.: assistente do FinGuard em frente própria), sem mapeamento nesta fase.

## 6. Diferença entre os conceitos (glossário obrigatório)

- **Provider externo**: Gemini/OpenAI/Claude/DeepSeek/Grok — estruturais, exigem chave.
- **Provider real autorizado**: provider externo chamado somente com `allow_real_provider=true` explícito no payload; nunca aprova release gate sozinho.
- **Mock**: provider local simulado, fallback padrão, sem custo.
- **local_qa**: pseudo-provider **determinístico** de QA, já ativo; único confiável para release gate.
- **Futuro local_model**: provider **generativo** local (Ollama/llama.cpp/LM Studio/custom); apenas contrato nesta frente.
- **Memória técnica**: sinais agregados de relatórios que poderão virar contexto — não é treinamento.
- **RAG**: recuperação de contexto por busca/embeddings — não existe nesta frente.
- **Fine-tuning**: ajuste de pesos de um modelo existente — proibido nesta frente.
- **Treinamento do zero**: criação de modelo próprio — fora do escopo do projeto (Decisão 001).

## 7. Task types novos (fundação)

Adicionados ao Task Router com criticidade `medium` e `allow_mock=true`, permitidos apenas para `origin_system=pedrocore`:

- `report_ingestion`
- `project_memory_summary`
- `model_foundation_review`
- `intelligence_planning`

FinGuard/finguard-local **não** recebem essas tasks nesta frente.

## 8. Regras absolutas

1. Intelligence Layer nunca chama provider.
2. Intelligence Layer nunca habilita `allow_real_provider=true`.
3. Intelligence Layer nunca altera prompt de produção automaticamente.
4. Intelligence Layer nunca persiste memória.
5. Intelligence Layer é testável isoladamente (`tests/test_intelligence_layer.py`).

## 9. Próxima frente (conexão ao Prompt Builder)

Nesta frente o plano é metadado interno. A conexão segura recomendada para a próxima frente:

- `PromptBuilder` recebe `plan.instructions` como seção adicional `[Plano de inteligência]` do prompt enriquecido;
- `OrchestrateResponse` pode ganhar campo opcional `intelligence_plan` (aditivo, retrocompatível);
- avaliação (`EvaluationService`) roda sobre o plano antes do provider e adiciona warnings padronizados.
