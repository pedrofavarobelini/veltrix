# Veltrix Universal Contracts V1 — Referência

Referência de integração dos cinco contratos universais.
Decisão: [[ADR_PEDROCORE_UNIVERSAL_CONTRACTS_V1]].
Contexto de planos: [[PEDROCORE_CONTROL_PLANE_MIGRATION_MAP]].

## 1. Princípio

```text
PROJETO
   ↓  fato observado + capacidade declarada + evidência verificável
Universal Contract
   ↓
Veltrix  →  validação  →  Operational Source
                                  ↓
              eligibility / privacy / provenance / authorization
                                  ↓
                          Training Candidate
```

O consumidor nunca monta um `TrainingExampleCandidate`. O caminho curto não
existe porque ele é exatamente o risco.

## 2. Os cinco contratos

| Contrato | Versão | Módulo |
|---|---|---|
| Project Capability Manifest | `pedrocore-capability-manifest/v1` | `universal_contracts/capability_manifest.py` |
| Quality Evidence (QEC) | `pedrocore-quality-evidence/v1` | `universal_contracts/quality_evidence.py` |
| Execution Outcome | `pedrocore-execution-outcome/v1` | `universal_contracts/execution_outcome.py` |
| Learning Source | `pedrocore-learning-source/v1` | `universal_contracts/learning_source.py` |
| Integration Envelope | `pedrocore-integration/v1` | `universal_contracts/envelope.py` |

## 3. Envelope de integração

```json
{
  "envelope_version": "pedrocore-integration/v1",
  "event_id": "evt-2026-08-29-001",
  "payload_type": "quality_evidence",
  "project_id": "meu-projeto",
  "producer_id": "meu-projeto-ci",
  "correlation_id": "corr-abc",
  "idempotency_key": "idem-abc",
  "submitted_at": "2026-08-29T12:00:00+00:00",
  "payload": { "...": "contrato correspondente ao payload_type" }
}
```

`project_id` e `producer_id` são **conferidos** contra a credencial registrada,
resolvida server-side. Divergência é recusa — o payload declara, a credencial
decide.

O payload é selecionado **estritamente** pelo `payload_type` declarado. Um
payload que "parece" evidência de qualidade mas foi declarado como fonte de
aprendizado é recusado: adivinhar o tipo é como uma governança de aprendizado
passa a aceitar o que nunca declarou.

## 4. Capabilities e traits

| Capability | Significado |
|---|---|
| `assistant` | consome o assistente conversacional |
| `quality_evidence` | produz evidência de QA (QEC V1) |
| `execution_outcome` | produz resultado de execução |
| `report_intelligence` | produz relatório estruturado |
| `interaction_outcome` | produz sinal de aceitação/rejeição |
| `learning_source` | produz fonte operacional de aprendizado |
| `risk_analysis` | produz análise de risco pré-execução |
| `artifact_reference` | referencia artefatos por payload |

| Trait | Efeito no core |
|---|---|
| `idempotent_submission` | habilita deduplicação governada na orquestração |
| `externally_owned` | acrescenta a regra de segurança read-only ao prompt |
| `requires_correlation` | exige correlação explícita |

Capability desconhecida é **recusada**, não ignorada. Aceitar em silêncio faria
um consumidor acreditar que negociou algo que o servidor nunca entendeu.

O manifesto **não** concede autorização de treinamento. Declarar
`learning_source` significa "sei produzir fonte", não "estou autorizado a
treinar". Não existe campo de autorização no manifesto, e um teste verifica
essa ausência.

## 5. Fronteira de autoridade

O consumidor pode dizer o que observou. Não pode dizer o que isso vale.

**Recusado** (`CONTRACT_AUTHORITY_VIOLATION`, em qualquer profundidade e em
qualquer grafia):

```text
eligibility · eligible · authorization · authorized · allows_neural_training
privacy_classification · training_candidate · candidate_id · lifecycle
dataset_readiness · readiness · dataset_membership · canonical_dataset
quality_score · trust_score · confidence_score
automatic_collection · automatic_collection_performed
```

**Aceito** — fato do produtor, com vocabulário próprio:

```text
observed_* · reported_* · producer_asserted_* · self_reported_*
```

`producer_asserted_outcome` é uma alegação; `eligibility` é uma sentença. A
diferença está no nome, e o nome é verificado.

## 6. Códigos de recusa

| Código | Quando |
|---|---|
| `CONTRACT_VERSION_UNKNOWN` | versão que o servidor não conhece |
| `CONTRACT_AUTHORITY_VIOLATION` | tentativa de emitir julgamento reservado |
| `CONTRACT_PAYLOAD_INVALID` | forma inválida |
| `CONTRACT_PROJECT_BINDING_MISMATCH` | `project_id` diverge da credencial |
| `CONTRACT_PRODUCER_BINDING_MISMATCH` | `producer_id` diverge da credencial |
| `CONTRACT_MANIFEST_MISSING` | projeto sem manifesto registrado |
| `CONTRACT_CAPABILITY_NOT_DECLARED` | capability exigida não declarada |
| `CONTRACT_CAPABILITY_VERSION_UNSUPPORTED` | manifesto não cobre a versão |

Mensagens de erro **nunca ecoam o valor rejeitado** — devolver o valor ao log
entregaria de volta exatamente o dado que o contrato acabou de recusar.

## 7. Versionamento

| Situação | Comportamento |
|---|---|
| `SUPPORTED` | processada normalmente |
| `DEPRECATED` | processada **com aviso** — deprecação avisa, não derruba |
| `UNKNOWN` | **recusada** (fail-closed), nunca adivinhada |

Mudança **aditiva** (campo opcional com default) não muda a versão.
Mudança **breaking** (campo obrigatório novo, remoção, mudança de tipo ou de
semântica) exige `.../v2`, com a v1 mantida até haver migration path
comprovado. Nunca se altera a v1 no lugar.

## 8. Migração dos acoplamentos de projeto

Quatro pontos no core genérico, todos migrados. Os dois últimos não constavam
do relatório da Era 1 e foram descobertos na auditoria desta Era.

| # | Antes | Depois |
|---|---|---|
| C1 | `orchestration/service.py:382` — `caller.project_id == "elyra"` | `has_trait(..., IDEMPOTENT_SUBMISSION)` |
| C2 | `prompt_builder/service.py:25` — `project_id == "finguard"` | `has_trait(..., EXTERNALLY_OWNED)` |
| C3 | `artifact_reader/service.py:137` — `"finguard" in path` | `protected_resource_markers()` |
| C4 | `exploration/playwright_adapter.py:81` — `"finguard" in url` | `protected_resource_markers()` |

Ocorrências **classificadas como legítimas** e mantidas: `project_context`
(registro de consumidores), `provider_authorization` e `shadow_routing`
(tabelas declarativas), módulos `elyra_*` (Consumer Capabilities — a fronteira
onde regra de projeto é correta), sentinelas genéricas `UNKNOWN_PROJECT_ID` e o
filtro de query de `observability`.

### Mudança intencional de comportamento — campo a campo

A regra `"O {display_name} é um projeto externo e somente leitura; não altere
nada nele."` passou a ser aplicada por trait em vez de por nome:

| Projeto | Antes | Depois | Nota |
|---|---|---|---|
| `finguard` | regra aplicada | regra aplicada | **texto byte a byte idêntico** |
| `finguard-local` | **omitida** | aplicada | bug latente: `== "finguard"` nunca casava |
| `structa` | omitida | aplicada | correção de modelo: sempre foi externo |
| `elyra` | omitida | aplicada | correção de modelo: sempre foi externo |
| `pedrocore` | omitida | omitida | não é externo |
| desconhecido | omitida | omitida | sem manifesto, sem trait |

Mensagens de bloqueio de C3/C4 deixaram de nomear o FinGuard: um aviso que
nomeia um consumidor específico revela a terceiros quais sistemas o Veltrix
conhece. O comportamento de bloqueio é idêntico.

## 9. Cobertura de teste

`tests/test_universal_contracts.py` — **55 testes**, todos PASS:

- Manifest (12): versão, capability desconhecida, versão de contrato
  desconhecida, duplicação, projeto inválido, capability ausente,
  compatibilidade, ausência de autorização de treino, consistência do registro;
- QEC (7): válida, contagens inconsistentes, `passed` com falha, contradição
  global, timezone, ausência de score autoritativo, score enviado pelo cliente;
- Execution Outcome (7): válido, resultado inválido, timestamps impossíveis,
  falha sem diagnóstico, projeto divergente, producer divergente, correlação;
- Learning Source (10): válida sem virar candidato, provenance mínima, policy
  version vazia de sentido, Training Candidate pronto, coleta automática,
  eligibility declarada, autorização fabricada, conteúdo bruto, consentimento
  obrigatório, texto livre em `derived_features`;
- Envelope (8): versão suportada, desconhecida, tipo contraditório, manifesto
  ausente, payload não-objeto, timezone, campo desconhecido, não-eco de valor;
- Autoridade (5): profundidade, grafias, prefixo de alegação, vocabulário,
  varredura só de nomes;
- Migração (4): ausência de comparação por nome no core, trait de idempotência,
  trait de propriedade externa, marcadores protegidos.

### Verificação por mutação

O guarda anticoupling não foi assumido. `project_id == "finguard"` foi
**reintroduzido deliberadamente** no prompt builder:

```text
FAILED tests/test_universal_contracts.py::test_core_modules_no_longer_branch_on_project_names
```

O arquivo foi restaurado em seguida. Um guarda que passa mas não reprova a
regressão que existe para impedir é decoração.
