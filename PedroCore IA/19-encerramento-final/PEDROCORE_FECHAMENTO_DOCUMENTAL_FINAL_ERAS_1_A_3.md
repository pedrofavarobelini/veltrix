# PedroCore — Fechamento documental final das Eras 1 a 3

Atualizado em: 20/08/2026

Entrada do vault: [[MOC_PEDROCORE_IA]]  
Mapa de estudo: [[MOC_ESTUDO_PEDROCORE]]

## Veredito

```text
ERA 1 — PASS
Operational Intelligence Foundation

ERA 2 — PASS
Motor de Risco de Execução por IA

ERA 3 — FOUNDATION PASS / TRAINING DEFERRED
```

Este é o checkpoint documental corrente. Fechamentos anteriores continuam
válidos como evidência histórica de suas próprias frentes, mas não substituem
este retrato consolidado.

## Limite da fonte da verdade

O fechamento foi confrontado nesta ordem: código, testes/evidências, schemas e
migrations, configuração, documentação canônica, vault e material de estudos.
O que é futuro permanece marcado como `PLANNED`; fundação implementada não é
apresentada como dataset pronto ou modelo treinado.

## Era 1 — Operational Intelligence Foundation

### Report Intelligence V2

[[REPORT_INTELLIGENCE_FOUNDATION]] implementa um envelope versionado
`schema_version=2.0`, payloads tipados para qualidade de interação, evidência de
QA, análise de risco e outcome de execução, além de provenance e correlation
IDs. O adapter V1 mantém compatibilidade e preserva metadata, evidence,
findings, sinais e referências disponíveis. O `producer` é validado contra a
identidade autenticada pelo boundary de `caller_identity`; versão desconhecida
e identidade divergente falham de forma explícita.

Relatórios técnicos produzem sinais determinísticos. Eles não treinam IA.

### Operational Persistence

[[REPORT_MEMORY]] define repositories `InMemory`, `LocalJson` e `PostgreSQL` sob
o mesmo contrato. PostgreSQL é opt-in, usa URL própria, migrations aditivas e
falha sem fallback silencioso. Retenção, idempotência, reconnect, paginação,
deleção e isolamento por `project_id` fazem parte do boundary operacional.

As migrations atuais separam reports, Interaction Outcomes, Operational Memory,
FTS e Training Candidates. Persistência implementada não significa que o
ambiente da auditoria estava configurado ou que existam candidatos reais.

### Interaction Outcomes

[[INTERACTION_OUTCOMES]] registra outcome, feedback, evidência mínima e
provenance sem armazenar prompt, resposta ou conversa brutos. Assinaturas são
pseudônimas, não anônimas. Feedback é observacional e não altera prompt,
provider, policy ou autorização.

### Operational Memory

[[OPERATIONAL_MEMORY]] transforma referências operacionais válidas em Learning
Candidates e, sob `operational-memory-v1`, em Operational Patterns explicáveis.
Cada padrão preserva evidências, confidence, contradições e histórico de
lifecycle:

```text
DETECTED → ACTIVE → MITIGATED → RESOLVED
```

Promoção exige evidência suficiente; contradição reduz confidence sem apagar o
histórico. `MITIGATED` e `RESOLVED` exigem evidência posterior apropriada e não
reativam silenciosamente.

### Retrieval V1

[[RETRIEVAL_V1]] faz recuperação estruturada, bounded e isolada por projeto. O
ranking determinístico combina correspondência lexical, task type, confidence,
volume de evidências, recência e lifecycle. Em PostgreSQL, a migration
`0004_operational_memory_retrieval.sql` mantém `TSVECTOR` e índice GIN para FTS;
em memória, a busca lexical segue o mesmo contrato.

O resultado é limitado a cinco projeções e 2.000 caracteres, possui trilha de
observabilidade e não usa embeddings nem vector DB.

### Safe Reuse

[[SAFE_REUSE_FOUNDATION]] separa:

```text
DIRECT_REUSE
TEMPLATE_REUSE
KNOWLEDGE_REUSE
ANTI_PATTERN
NO_REUSE
```

`DIRECT_REUSE` não é atalho de execução: `provider_bypass=false` permanece
invariável. Não existe cache cego de respostas, persistência de resposta pronta,
alteração automática de prompt ou execução automática.

## Era 2 — Motor de Risco de Execução por IA

### Arquitetura

```text
Prompt
  ↓
Intent
  ↓
Context
  ↓
Risk Analysis
  ↓
Historical Evidence
  ↓
Blast Radius
  ↓
Scenario Simulation
  ↓
Execution Contract
  ↓
Risk Gate
  ↓
Execution Evidence
  ↓
QA
  ↓
Execution Outcome
  ↓
Operational Memory
```

O [[RISK_ENGINE_FOUNDATION|Risk Engine]] é um subsistema governante e
analítico. Ele não é Agent, executor, segundo QA ou segunda memória.

### Foundation e análise de risco

O pipeline inicial aplica Intent Analysis, Context Resolution, Prompt Quality,
Ambiguity Detection e Scope Analysis. A análise pré-execução combina regras
determinísticas versionadas, catálogo semântico local sem provider e evidência
histórica recuperada da Operational Memory.

As dimensões permanecem independentes e explicáveis:

```text
scope_risk
data_risk
security_risk
migration_risk
regression_risk
operational_risk
```

Cada score preserva severity e reason codes; não é reduzido a um número opaco.

### Blast Radius e Scenario Simulation

O blast radius considera arquivos, módulos, banco, usuários, permissões,
ambientes, integrações externas e security boundaries.

A simulação é `analytical_dry_run`, não destrutiva e mantém
`target_operation_executed=false`. Os cenários são:

- success;
- partial failure;
- scope deviation;
- dependency failure;
- rollback requirement;
- security impact.

### Execution Contract e gates

[[EXECUTION_CONTRACT_RISK_GATES]] materializa a decisão em contrato imutável e
verificável. O contrato contém HMAC-SHA256, versões de policy, expiração,
`context_signature`, allowed/forbidden scope, allowed/forbidden files, comandos
permitidos, operações proibidas, testes obrigatórios, backup/review e controles
de risco.

```text
PASS
PASS_WITH_WARNINGS
REVIEW_REQUIRED
BLOCK
```

Review/override humano produz registro assinado e auditável. `BLOCK` não possui
override silencioso; manipulação, expiração, conflito de permissão ou contexto
divergente fecham o gate.

### Pós-execução

[[POST_EXECUTION_QA]] compara intenção × execução e risco previsto × risco
ocorrido. QA continua sendo o produtor de evidência: o endpoint recebe testes,
diffs e resultados produzidos externamente, valida contra o contrato e gera
Execution Outcome V2. Nenhum segundo QA foi criado e o Risk Engine não executa
comandos, testes, migrations ou scanners.

### Historical Risk Intelligence

[[HISTORICAL_RISK_INTELLIGENCE]] consulta Operational Memory com policy version
explícita e compara quatro estratégias:

- `deterministic_only`;
- `semantic_only`;
- `history_only`;
- `hybrid`.

O benchmark mede TP, FP, TN, FN, precision, recall, severe false negatives,
erro de calibração e abstention/review rate. Abstenção vira revisão, não acerto;
false negative severo recebe maior peso. Policies incompatíveis nunca são
agregadas silenciosamente e amostras abaixo de 30 não são generalizáveis.

## Era 3 — Training Foundation

Status: **FOUNDATION PASS / TRAINING DEFERRED**.

[[DATASET_FOUNDATION]] define `TrainingExampleCandidate` e separa:

```text
Operational Data ≠ Training Candidate ≠ Canonical Training Example
```

As fontes tipadas são Interaction Outcome, Operational Pattern, Report
Intelligence V2, QA Evidence, Risk Analysis, Execution Outcome e Human
Feedback. `automatic_collection=false`: não existe varredura autônoma das
fontes.

### Etapa 13A — Candidate Acquisition Foundation

[[TRAINING_CANDIDATE_LIFECYCLE]] está implementada com o fluxo:

```text
Operational Evidence
  ↓
Selector
  ↓
Eligibility
  ↓
Privacy
  ↓
Provenance
  ↓
Explicit Authorization
  ↓
TrainingExampleCandidate
  ↓
Candidate Store
  ↓
Readiness Audit
```

Purposes:

```text
GENERATIVE_SFT
PREFERENCE
RISK
EVALUATION_ONLY
```

Lifecycle:

```text
PROPOSED
REVIEW_REQUIRED
AUTHORIZED
EXCLUDED
CONSUMED
REVOKED
```

`REVOKED` é terminal nesta etapa. `CONSUMED` existe como integração interna
reservada ao futuro dataset e não possui endpoint público de consumo.

### Privacidade e autorização

O gate bloqueia secrets, tokens, API keys, `.env`, credenciais, PII
desnecessária, dados financeiros identificáveis, paths pessoais irrelevantes e
conversa bruta quando desnecessária. Rejeições persistem hashes e códigos de
finding, não o valor sensível.

```text
feedback positivo/negativo ≠ autorização para treinamento
```

Autorização neural é explícita, purpose-bound, project-bound, criada no servidor
por capability administrativa registrada e revogável. `EVALUATION_ONLY` não
autoriza uso neural.

### Estado real do dataset

[[DATASET_READINESS_AUDIT]] registra:

```text
Training Candidates reais autorizados = 0
DATASET READINESS = DATASET_NOT_READY

Canonical Dataset = NÃO CRIADO
Train/Validation/Test = NÃO CRIADOS
Hugging Face = NÃO INICIADO
Fine-Tuning = NÃO INICIADO
Modelo próprio = NÃO EXISTE
Local Provider treinado = NÃO EXISTE
```

Este é o comportamento correto do gate: a fundação passou, mas não há dados
reais suficientes nem autorização para avançar.

## Aprendizado operacional, fine-tuning e treino do zero

### Operational Learning — implementado

Aprende operacionalmente por memória, evidências, outcomes, patterns,
retrieval, feedback e policies. Produz contexto e decisão explicáveis, sem
alterar pesos neurais.

### Fine-Tuning — futuro, PLANNED

Adapta parâmetros de um modelo pré-treinado usando dataset canônico e uma stack
como Hugging Face + PEFT/LoRA/SFT. Não começou.

### Training from Scratch — fora da estratégia atual

Cria um modelo base desde pesos iniciais e exige escala de dados, compute e
governança muito superiores. Não faz parte do roadmap vigente.

## Arquitetura final do ecossistema

```text
                    PEDROCORE
          inteligência / memória / contexto
                       │
        ┌──────────────┼──────────────┐
        │              │              │
    Providers     Operational      Reports
                    Memory
        │              │
        └──────────────┼──────────────┐
                       │              │
                   Risk Engine        QA
                    governa         evidencia
                       │              │
                       └──────┬───────┘
                              │
                           Outcome
                              │
                              ▼
                          PedroCore
```

Futuro, somente como roadmap:

```text
PedroCore
    ├── Gemini
    ├── OpenAI
    ├── outros providers
    └── Local Model
           ↓
      Hugging Face fine-tuned
```

O adapter/contrato `local_model` existente não equivale a Local Provider
treinado. Não há modelo PedroCore fine-tuned instalado ou homologado.

## Roadmap futuro — PLANNED

```text
TrainingExampleCandidates reais
  ↓
Readiness PASS
  ↓
Canonical Dataset V1
  ↓
Sanitization
  ↓
Deduplication
  ↓
Quality Gate
  ↓
Train / Validation / Test
  ↓
Hardware Audit
  ↓
License Audit
  ↓
Base Model Benchmark
  ↓
Hugging Face
  ↓
PEFT / LoRA / SFT
  ↓
Fine-Tuning
  ↓
Base × Fine-Tuned
  ↓
Acceptance Gate
  ↓
Packaging
  ↓
futura integração LocalModelProvider
```

Nenhum passo desta cadeia foi iniciado além da Candidate Acquisition
Foundation e do Readiness Audit que retornou `DATASET_NOT_READY`.

## Evidência e dívida técnica conhecida

Último checkpoint backend disponível no mesmo HEAD da Etapa 13A:

```text
924 passed, 7 skipped, 2 warnings
Ruff global: PASS
Pyright no escopo da Era 3: 0 errors, 0 warnings
```

O número `911 passed` citado no briefing foi superado pela validação mais recente
de 20/08/2026; a documentação usa `924 passed` por prevalência da evidência mais
nova. Esta execução documental não repetiu a suíte.

Dívida preservada, sem correção nesta frente:

- warnings de depreciação existentes;
- Strix bloqueado por pré-requisitos locais (`STRIX_BLOCKED_BY_LOCAL_PREREQUISITES`);
- resíduos humanos preexistentes no frontend;
- whitespace preexistente em `apps/web/src/styles/global.css`.

## Triple review

### Review A — código × documentação

Os itens marcados como implementados possuem módulos, schemas, repositories,
routers, migrations e testes correspondentes. Persistência configurável não foi
confundida com dados reais existentes.

### Review B — consistência

Este checkpoint é a referência comum para o vault, a documentação canônica do
repositório e `C:\Projetos\Estudos\PedroCore`. Notas antigas permanecem como
histórico de seu checkpoint e apontam para este fechamento quando necessário.

### Review C — estado futuro

Hugging Face, Fine-Tuning, Canonical Dataset, splits e Local Provider treinado
estão exclusivamente como `PLANNED`, `NÃO INICIADO` ou `NÃO EXISTE`.

## Navegação

- [[MOC_PEDROCORE_IA]]
- [[MOC_ESTUDO_PEDROCORE]]
- [[MOC_TESTES]]
- [[REPORT_INTELLIGENCE_FOUNDATION]]
- [[OPERATIONAL_MEMORY]]
- [[RETRIEVAL_V1]]
- [[SAFE_REUSE_FOUNDATION]]
- [[RISK_ENGINE_FOUNDATION]]
- [[HISTORICAL_RISK_INTELLIGENCE]]
- [[DATASET_FOUNDATION]]
- [[TRAINING_CANDIDATE_LIFECYCLE]]
- [[DATASET_READINESS_AUDIT]]
