# Dataset Readiness Audit

Estado: **DATASET_NOT_READY**. Data da auditoria: 2026-08-20.

## Evidência observada

- `PEDROCORE_REPORT_MEMORY_PERSISTENCE`: não configurada;
- `PEDROCORE_REPORT_MEMORY_DATABASE_URL`: não configurada;
- `PEDROCORE_REPORT_MEMORY_DIR`: não configurada;
- `PEDROCORE_TEST_POSTGRES_URL`: não configurada no ambiente da auditoria;
- diretórios de dataset, training runs e checkpoints: ausentes;
- artefatos de Training Candidate ou Canonical Dataset: zero;
- candidatos reais com autorização neural e provenance verificada: zero.

Os objetos presentes em `test_dataset_foundation.py` são fixtures sintéticas
mínimas para validar o contrato. Eles não constituem dataset e não podem ser
promovidos para aparentar suficiência.

## Decisão

O Gate 13 não pode receber PASS porque não existe população real autorizada
para filtering, sanitization, deduplication, quality scoring e split. Nenhum
dataset foi gerado; nenhuma consulta a Hugging Face, seleção de modelo ou
operação de treinamento foi iniciada.

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
