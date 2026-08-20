# Contrato — Risk Engine Foundation

## Boundary

`POST /api/risk/foundation/analyze` recebe um `RiskRequest` técnico,
autenticado e vinculado ao projeto. O subsistema analisa intenção e contexto;
ele não possui adapter capaz de executar a operação solicitada.

A resposta fixa como `false`:

- `target_operation_executed`;
- `provider_called`;
- `operational_memory_created`.

## Entrada estruturada

O contrato inclui texto do pedido, projeto, environment, agent, permissions,
contexto e `RequestedOperation`. Contexto separa escopo permitido/proibido,
arquivos, módulos, banco, usuários, integrações, constraints, critérios,
testes e presença de rollback.

O texto do pedido é analisado em memória e não é ecoado na resposta.

## Saída reproduzível

`risk-foundation-v1` produz `ExecutionIntent`, `ResolvedContext`, qualidade do
prompt, ambiguidades, análise de escopo, `RiskSignal`, `RiskFinding`, confiança
e incerteza. IDs derivam de conteúdo canônico; a mesma entrada gera exatamente
a mesma avaliação.

Esta fundação não emite ainda o gate executivo final e não usa LLM isolada.

## Navegação

- [[RISK_ENGINE_FOUNDATION]]
- [[CONTRATO_PRE_EXECUTION_RISK_V1]]
