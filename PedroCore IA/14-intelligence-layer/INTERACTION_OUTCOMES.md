# Interaction Outcomes

Frente: `PEDROCORE-INTERACTION-OUTCOMES` — IMPLEMENTED
Atualizado em: 20/08/2026

Links: [[REPORT_MEMORY]] | [[OPERATIONAL_MEMORY]] | [[REPORT_INTELLIGENCE_FOUNDATION]] | [[../10-contratos/CONTRATO_INTERACTION_OUTCOMES]]

## 1. Objetivo

`InteractionOutcome` registra somente características úteis e mínimas de uma
interação para análise operacional futura. O módulo
`apps/api/app/modules/interaction_outcomes/` possui schema, serviço, contrato de
repositório e API próprios, mas reutiliza a mesma Caller Identity e a mesma
Operational Persistence de Report Memory.

Não existe segundo sistema de memória: outcomes são evidência de entrada para a
Operational Memory das etapas seguintes.

## 2. Fluxo implementado

```text
Ferramenta técnica autenticada
  -> POST /api/interaction-outcomes
  -> autorização por projeto + validação de producer
  -> normalização determinística
  -> InMemory | LocalJson | PostgreSQL
  -> reconnect
  -> GET /api/interaction-outcomes/{project_id}
```

O `outcome_id` é idempotente dentro do projeto. A unicidade PostgreSQL
`(project_id, outcome_id)` também cobre concorrência; repetição retorna
`status="duplicate"` sem novo efeito.

## 3. Minimização e privacidade

- prompt, mensagem, resposta e conversa brutos não fazem parte do schema;
- `input_signature` e `context_signature` exigem `sha256:<64 hex>`;
- hash é identificador pseudônimo e **não equivale a anonimização**;
- `response_characteristics` é tipado e contém apenas categorias/booleanos;
- provenance (`producer`, papel, ambiente e projeto) é validada ou derivada da
  credencial autenticada;
- retenção usa `PEDROCORE_REPORT_MEMORY_RETENTION_DAYS` e deleção é isolada por
  projeto autenticado.

## 4. Feedback é observacional

Valores: `positive`, `negative`, `neutral`, `unknown`.

Um feedback ou outcome individual não altera prompt, provider, policy,
autorização ou comportamento. Toda ingestão retorna
`INTERACTION_FEEDBACK_OBSERVATIONAL`. Promoção para padrão exige o pipeline de
Learning Candidate/Operational Memory da Etapa 4 e sua política versionada.

## 5. Persistência

- usa `PEDROCORE_REPORT_MEMORY_PERSISTENCE` (`off`, `memory`, `local_json`,
  `postgresql`) e a mesma URL operacional;
- `memory`/`local_json` preservam o limite local de 50 por projeto;
- PostgreSQL não possui esse limite e oferece paginação/filtros por correlação;
- migração aditiva `migrations/0002_interaction_outcomes.sql`;
- falha de configuração, conexão ou schema retorna 503
  `INTERACTION_OUTCOME_PERSISTENCE_UNAVAILABLE`, sem fallback.

## 6. Gate

`test_interaction_outcomes.py` cobre schema/versionamento, mass assignment,
provenance, idempotência, duplicidade, isolamento, correlação, todos os valores
de feedback, reconnect, retenção, deleção e falha de banco. O Security
Checkpoint A combina esses casos com Report Auth e Operational Persistence.
