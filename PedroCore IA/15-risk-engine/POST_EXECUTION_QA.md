# Post-Execution + QA

O pós-execução fecha a trilha:

`Prompt → Risk → Contract → Evidence → QA existente → Execution Outcome V2 → Operational Memory`

## Limites

O endpoint não executa commands, tests, migrations ou scanners. Ele recebe
resultados já produzidos pelo Agent/Test Harness em ambiente seguro e compara
esses resultados com o contrato assinado.

Um contrato `REVIEW_REQUIRED` sem review assinado ou qualquer contrato
manipulado/expirado resulta em outcome bloqueado. Evidência ausente não é
inventada: files changed sem assinatura de diff geram
`DIFF_EVIDENCE_MISSING`; testes ausentes bloqueiam o QA existente.

O response preserva IDs ponta a ponta e uma projeção mínima do candidato/memory
criados, sem transportar evidência integral para a memória.

## Navegação

- [[CONTRATO_POST_EXECUTION_QA]]
- [[EXECUTION_CONTRACT_RISK_GATES]]
- [[HISTORICAL_RISK_INTELLIGENCE]]
