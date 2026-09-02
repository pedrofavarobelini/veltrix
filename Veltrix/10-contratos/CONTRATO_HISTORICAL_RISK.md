# Contrato — Historical Risk Intelligence

## Endpoints

`POST /api/risk/history/query` consulta exclusivamente a Operational Memory
existente. `POST /api/risk/history/benchmark` compara quatro estratégias:
deterministic-only, semantic-only, history-only e hybrid. Ambos exigem a mesma
autenticação técnica e a mesma fronteira de `project_id`/`producer` do Motor de
Risco.

Nenhum endpoint treina modelo, executa command, chama provider ou cria memória
paralela. `training_performed=false` faz parte do contrato de resposta.

## Consulta histórica

A policy `historical-risk-v1` registra explicitamente:

- janela temporal e filtros efetivamente aplicados;
- tamanho da amostra, outcomes e confiança média;
- lifecycle, tipo, policy e evidências de cada padrão aceito;
- amostras excluídas e o motivo da exclusão;
- versões da policy de risco solicitadas.

Uma amostra com evidência de múltiplas versões incompatíveis é excluída com
`INCOMPATIBLE_POLICY_MIX`. Evidência sem `risk_policy_version` também não é
misturada silenciosamente. Amostras menores que 30 permanecem
`small_sample_warning=true` e `generalizable=false`.

## Benchmark

Casos rotulados pelo chamador produzem TP, FP, TN, FN, false negatives severos,
precision, recall, erro ponderado por severidade, erro de calibração e taxa de
abstenção para revisão. A recomendação prioriza, nesta ordem, evitar false
negatives severos, evitar demais false negatives, reduzir erros ponderados e
maximizar recall.

O identificador derivado do payload, as policies, os casos, as predições e as
métricas tornam o benchmark reproduzível e auditável. O resultado não altera
regras nem promove aprendizado automaticamente.

## Navegação

- [[HISTORICAL_RISK_INTELLIGENCE]]
- [[CONTRATO_POST_EXECUTION_QA]]
- [[CONTRATO_PRE_EXECUTION_RISK_V1]]
