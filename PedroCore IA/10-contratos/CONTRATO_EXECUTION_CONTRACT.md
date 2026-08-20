# Contrato — Execution Contract + Risk Gates

## Emissão

`POST /api/risk/contracts` recalcula a análise de risco no servidor e emite um
`ExecutionContract` assinado pela policy `execution-contract-v1`. Gate,
reason codes, controles e assinatura não são aceitos do caller.

O contrato inclui contract/risk policy, context signature, escopos e arquivos
permitidos/proibidos, comandos permitidos, operações proibidas, testes, backup,
review, controles, timestamps, expiração, dimensões e evidence IDs.

`allowed_commands` permanece vazio: este boundary não concede execução de
shell. O contrato governa um agente externo; não executa por ele.

## Gates

- `PASS`: contexto e permission satisfazem a policy, sem sinais relevantes;
- `PASS_WITH_WARNINGS`: somente riscos não bloqueantes;
- `REVIEW_REQUIRED`: contexto crítico ausente ou risco alto/histórico;
- `BLOCK`: escopo proibido, permission conflict, operação desconhecida ou
  mudança de secret em produção.

LLM nunca decide isoladamente. A decisão combina regras, evidence, history,
catálogo semântico e policy.

## Integridade e fail-closed

Contratos usam HMAC-SHA256 com segredo local de no mínimo 32 caracteres. A
validação recalcula a assinatura e o contexto e verifica expiração. Contrato
manipulado, expirado ou com contexto diferente nunca é válido. Ausência do
segredo bloqueia emissão/validação.

## Human review / override

Reviewers são credential IDs registrados em allowlist explícita. O registro
assinado contém reviewer autenticado, decision, reason, timestamp, policy,
contract ID e gates original/resultante. `BLOCK` não pode ser promovido nesta
versão; aprovação de `REVIEW_REQUIRED` resulta no máximo em
`PASS_WITH_WARNINGS`.

## Navegação

- [[EXECUTION_CONTRACT_RISK_GATES]]
