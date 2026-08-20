# Pre-Execution Risk Analysis V1

O pipeline híbrido combina regras, sinais contextuais e histórico sem tornar
qualquer fonte soberana isoladamente. `project_id` continua sendo fronteira de
autorização; relevância histórica é obtida pelo Retrieval V1.

## Regras e dimensões

Cada regra acionada vira evidence, signal e finding rastreáveis. Os efeitos são
mantidos em seis dimensões independentes; a policy não colapsa risco de dados,
segurança, migração, escopo, regressão e operação em um número opaco.

## Simulação segura

São modelados success, partial failure, scope deviation, dependency failure,
rollback requirement e security impact. Todos os cenários são projeções
analíticas e mantêm `target_operation_executed=false`.

## Memória

O Motor de Risco consulta a Operational Memory por meio do Retrieval existente
e guarda na resposta apenas IDs, tipos, lifecycle, confidence, relevance e
policy. Não há segunda memória, treinamento ou promoção automática.

## Navegação

- [[CONTRATO_PRE_EXECUTION_RISK_V1]]
- [[RISK_ENGINE_FOUNDATION]]
- [[EXECUTION_CONTRACT_RISK_GATES]]
