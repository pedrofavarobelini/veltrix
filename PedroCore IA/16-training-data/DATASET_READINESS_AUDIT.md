# Dataset Readiness Audit

Estado: **DATASET_NOT_READY**. Data da auditoria V2: 2026-08-20.

Candidate Acquisition Foundation: **IMPLEMENTED** (`training-acquisition-v1`).

## Evidência observada

- `PEDROCORE_REPORT_MEMORY_PERSISTENCE`: não configurada;
- `PEDROCORE_REPORT_MEMORY_DATABASE_URL`: não configurada;
- `PEDROCORE_REPORT_MEMORY_DIR`: não configurada;
- `PEDROCORE_TEST_POSTGRES_URL`: não configurada no ambiente da auditoria;
- diretórios de dataset, training runs e checkpoints: ausentes;
- artefatos de Training Candidate ou Canonical Dataset: zero;
- candidatos reais com autorização neural e provenance verificada: zero.
- `PEDROCORE_TRAINING_DATA_ADMIN_IDS`: não configurada no ambiente da auditoria;
- `PEDROCORE_DATASET_READINESS_MIN_AUTHORIZED`: não configurada; o volume mínimo
  permanece decisão explícita de governança e bloqueia readiness por default.

## Métricas V2 observadas

- total: 0;
- authorized: 0;
- eligible: 0;
- review_required: 0;
- excluded: 0;
- revoked: 0;
- by source/project/task/purpose: vazio;
- known outcomes, QA evidence e human feedback: 0;
- duplicate groups: 0;
- privacy rejections reais: 0.

Os objetos presentes em `test_dataset_foundation.py` são fixtures sintéticas
mínimas para validar o contrato. Eles não constituem dataset e não podem ser
promovidos para aparentar suficiência.

## Decisão

O Gate 13A pode receber PASS para o mecanismo de aquisição. O Gate 13 continua
`DATASET_NOT_READY` porque não existe população real autorizada
para filtering, sanitization, deduplication, quality scoring e split. Nenhum
dataset foi gerado; nenhuma consulta a Hugging Face, seleção de modelo ou
operação de treinamento foi iniciada. Linhas sintéticas criadas pela integração
PostgreSQL foram exclusivas de QA e removidas ao final; não contam nas métricas.

## Validação do mecanismo

- regressão backend: `924 passed, 7 skipped, 2 warnings`;
- Ruff global: PASS;
- Pyright no escopo alterado: `0 errors, 0 warnings`;
- PostgreSQL 16 efêmero: migração, reconexão, isolamento e revogação PASS;
- Candidate Store após cleanup da suíte: 0 linhas;
- Strix: `STRIX_BLOCKED_BY_LOCAL_PREREQUISITES` (CLI, LLM e token cloud ausentes;
  nenhuma instalação ou chamada paga realizada).

## Condições para nova auditoria

Uma continuação exige candidatos derivados de fontes reais, cada um com:

- autorização explícita de uso neural;
- classificação do conteúdo;
- provenance verificada e project-bound;
- policy e outcome observados;
- ausência de secrets, credenciais, PII desnecessária e dados financeiros
  pessoais.

A nova população deverá ser auditada sem imprimir conteúdo privado. Somente
depois disso o Canonical Dataset V1 poderá ser implementado e avaliado.

## Navegação

- [[DATASET_FOUNDATION]]
- [[CONTRATO_TRAINING_DATA_CANDIDATE]]
- [[TRAINING_CANDIDATE_LIFECYCLE]]
