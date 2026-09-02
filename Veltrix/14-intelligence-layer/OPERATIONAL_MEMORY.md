# Operational Memory

Frente: `PEDROCORE-OPERATIONAL-MEMORY` — IMPLEMENTED
Atualizado em: 20/08/2026

Links: [[REPORT_MEMORY]] | [[INTERACTION_OUTCOMES]] | [[../10-contratos/CONTRATO_OPERATIONAL_MEMORY]]

## 1. Papel arquitetural

Operational Memory é a memória canônica de padrões operacionais do Veltrix.
Não é um segundo cérebro, não substitui Report Intelligence e não executa
ações. Reports e Interaction Outcomes permanecem fontes de evidência; o módulo
`apps/api/app/modules/operational_memory/` resolve essas referências e aplica
uma política determinística/versionada.

```text
Report / Interaction Outcome
  -> EvidenceReference resolvida no mesmo projeto
  -> LearningCandidate
  -> OperationalPattern
  -> confiança + policy
  -> OperationalMemoryEntry
```

## 2. Tipos de padrão

`SUCCESS_PATTERN`, `FAILURE_PATTERN`, `ANTI_PATTERN`, `USER_PREFERENCE`,
`PROJECT_PATTERN`, `PROVIDER_PATTERN`, `PROMPT_PATTERN` e `RISK_PATTERN`.

Nesta etapa, todos permanecem observacionais. Uma entrada nunca altera
automaticamente auth, código, provider, secrets, segurança, policy financeira,
system prompt sensível ou futuras policies do Risk Engine.

## 3. Evidência e promoção

- somente IDs existentes de `report` ou `interaction_outcome` do mesmo projeto
  são aceitos;
- reliability, strength, QA validation e context match são derivados pelo
  Veltrix, não aceitos por mass assignment;
- `human_validation` existe no contrato de domínio, mas ingestão humana fica
  bloqueada até existir identidade/autorização próprias;
- evidência repetida é deduplicada por fonte, ID e efeito;
- um ou dois eventos permanecem `DETECTED`;
- promoção para `ACTIVE` exige ao menos três suportes distintos e confiança
  maior ou igual a `0.70`.

Policy version: `operational-memory-v1`.

Pesos: source reliability 20%, evidence strength 20%, frequency 20%, recency
10%, context match 15%, QA validation 10% e human validation 5%, menos
penalidade proporcional de contradição (máx. 40%).

## 4. Contradição e lifecycle

Lifecycle: `DETECTED`, `ACTIVE`, `MITIGATED`, `RESOLVED`.

- contradições ficam em lista separada e reduzem confiança; não apagam suporte;
- toda mudança de lifecycle gera `LifecycleTransition` com motivo e timestamp;
- `MITIGATED`/`RESOLVED` só se aplicam a failure/anti/risk pattern;
- resolução ou mitigação exige evidência posterior QA/humana validada;
- padrões resolvidos permanecem resolvidos e novas evidências ficam preservadas
  para revisão, sem reativação silenciosa.

## 5. Persistência e API

A mesma Operational Persistence (`off`, `memory`, `local_json`, `postgresql`)
é reutilizada. A migração aditiva `0003_operational_memory.sql` cria tabelas de
Learning Candidates e Operational Memory no mesmo PostgreSQL.

- `POST /api/operational-memory/candidates`;
- `GET /api/operational-memory/{project_id}` com filtros/paginação;
- `DELETE /api/operational-memory/{project_id}`.

Candidate e memory são persistidos atomicamente no PostgreSQL. Falha retorna
503 `OPERATIONAL_MEMORY_PERSISTENCE_UNAVAILABLE`, sem fallback. Retenção e
deleção são isoladas por projeto.

## 6. Gate

`test_operational_memory.py` cobre candidate, oito pattern types, promoção,
evidência, contradição, confidence, lifecycle, resolução, reconnect, retenção,
idempotência, isolamento, redaction e falha de banco.

## 7. Continuidade

- [[RETRIEVAL_V1]]
