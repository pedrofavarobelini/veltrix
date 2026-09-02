# Contrato — Post-Execution + QA

## Evidência

`POST /api/risk/execution-outcomes` aceita somente evidência estruturada e
autenticada: files changed, assinatura/estatísticas do diff, command IDs,
tests, security results, migrations, scope changes e unexpected effects.
Diff bruto não é transportado. Commands com secrets inline são rejeitados e
erros 422 não ecoam o payload recusado.

Contrato, current request e evidence devem pertencer ao projeto autenticado.
O contrato é revalidado por HMAC, contexto e expiração. Review record opcional
também precisa ter assinatura válida e o mesmo contract ID.

## Comparações

A policy `post-execution-v1` registra separadamente:

- intent targets × actual targets;
- allowed files/scope/commands × efeitos observados;
- predicted risk dimensions × actual issue codes;
- unexpected files, failed tests, security findings, migration incidents,
  forbidden operations e unexpected effects.

## QA e outcome

A evidência de testes é convertida em `ArtifactProcessingResult` e entregue ao
`qa_text_analyzer`/`qa_response_service` existentes. Não existe segundo QA.

O resultado é um `execution_outcome` no Report Intelligence V2. Quando a
Operational Persistence está habilitada, o report é armazenado e vira evidence
de Learning Candidate na Operational Memory existente. Promoção continua sob a
policy da Operational Memory; não há memória paralela.

## Navegação

- [[POST_EXECUTION_QA]]
- [[CONTRATO_HISTORICAL_RISK]]
