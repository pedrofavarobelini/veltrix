# Contrato — Operational Memory

Frente: `PEDROCORE-OPERATIONAL-MEMORY` — IMPLEMENTED
Atualizado em: 20/08/2026

Links: [[CONTRATO_REPORT_MEMORY]] | [[CONTRATO_INTERACTION_OUTCOMES]] | [[../14-intelligence-layer/OPERATIONAL_MEMORY]]

## 1. Learning Candidate

`LearningCandidateInput` usa `schema_version="1.0"`, `extra="forbid"` e contém:

- `candidate_id`, `producer`, `project_id`;
- `pattern_type`, `pattern_key`, `task_type`, `summary`;
- uma a vinte referências `{source_type, source_id, effect}`.

Campos derivados como confidence, QA/human validation, reliability, lifecycle,
papel e ambiente não são aceitos na entrada. `producer` e projeto são validados
contra Caller Identity. Resumos são redigidos antes de persistir.

## 2. Evidence Reference

Fontes atuais:

- `report`: exige `report_id` persistido no mesmo projeto;
- `interaction_outcome`: exige `outcome_id` persistido no mesmo projeto;
- `human_validation`: modelado, mas bloqueado até contrato próprio.

Efeitos: `supports`, `contradicts`, `mitigates`, `resolves`.
`mitigates`/`resolves` só valem para `FAILURE_PATTERN`, `ANTI_PATTERN` e
`RISK_PATTERN`; resolução/mitigação exige validação QA/humana derivada.

## 3. Idempotência e decisões

`candidate_id` é único por projeto. Repetição retorna `status="duplicate"` e
não recalcula nem duplica evidência. A decisão pode ser `detected`, `promoted`,
`mitigated` ou `resolved`, sempre pela policy
`operational-memory-v1`.

Uma amostra isolada nunca vira regra ativa. Confidence e seu breakdown são
armazenados para auditoria; policies futuras não devem misturar resultados
incompatíveis silenciosamente.

## 4. Operational Memory Entry

Contém padrão, confidence/breakdown, lifecycle, candidate IDs, evidências,
contradições, sample size, policy version, histórico de lifecycle e timestamps.
Não contém prompt, resposta ou conversa brutos.

## 5. Segurança

- autorização `technical_tool` e isolamento por projeto em todas as rotas;
- referência cross-project é tratada como evidência inexistente;
- SQL parametrizado e migração somente aditiva;
- nenhuma chamada de provider, leitura de arquivo, execução ou mutação externa;
- Operational Memory não é treinamento e não é aplicada automaticamente.
