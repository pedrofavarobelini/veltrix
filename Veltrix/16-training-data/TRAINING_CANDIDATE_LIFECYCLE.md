# Training Candidate Lifecycle e Policy

Estado: **IMPLEMENTED** — Era 3, Etapa 13A.

## Limite arquitetural

O fluxo mantém três stores conceitualmente distintos:

`Operational Evidence → Candidate Store → futuro Canonical Dataset`

O primeiro permanece autoritativo para os fatos operacionais. O Candidate
Store registra decisões, autorização e lineage. O Canonical Dataset não existe
nesta etapa. Nenhuma chamada de provider, Hugging Face ou training é realizada.

## Seleção explícita

Os sete selectors reutilizam os domínios existentes:

| Source | Store operacional consultado | Purpose permitido |
|---|---|---|
| Interaction Outcome | Interaction Outcomes | Generative SFT, Preference, Evaluation |
| Operational Pattern | Operational Memory | Generative SFT, Risk, Evaluation |
| Report Intelligence V2 | Report Memory | Generative SFT, Evaluation |
| QA Evidence | Report Memory (`qa_evidence`) | Generative SFT, Evaluation |
| Risk Analysis | Report Memory (`risk_analysis`) | Risk, Evaluation |
| Execution Outcome | Report Memory (`execution_outcome`) | Risk, Evaluation |
| Human Feedback | Interaction Outcomes | Preference, Evaluation |

O request público informa somente `producer`, projeto, source type, source ID e
purpose. Identidade, projeto e producer são validados contra a credencial. O
backend resolve o registro existente e produz provenance verificada; campos
forjados adicionais são rejeitados por `extra=forbid`.

## Eligibility

`training-acquisition-v1` possui duas fases:

1. pre-screen de source/purpose, provenance, outcome, quality e privacy;
2. decisão final incluindo autorização neural verificável.

O pre-screen pode gerar `PROPOSED`, `REVIEW_REQUIRED` ou `EXCLUDED`. Uma proposta
sem autorização permanece `NOT_ELIGIBLE_FOR_TRAINING`. A decisão final é
`ELIGIBLE`, `NOT_ELIGIBLE` ou `REQUIRES_REVIEW`; dúvida e inconsistência fecham
o gate.

Human review pode liberar somente sinais de qualidade fracos. Ela não corrige
provenance ausente, source/outcome desconhecido, privacy rejection, purpose
incompatível ou autorização ausente.

## Autorização

A API nunca aceita `training_authorized`, `authorized_by`, `authorized_at`,
`authorized_project`, `training_purpose` ou policy version. Um caller registrado,
com papel `technical_tool`, e listado em `PEDROCORE_TRAINING_DATA_ADMIN_IDS`
constrói a autorização no servidor. O modo local não registrado não pode
receber essa capability. Ela registra:

- projeto e scope autorizados;
- purpose isolado (`GENERATIVE_SFT`, `PREFERENCE`, `RISK` ou `EVALUATION_ONLY`);
- policy e authorization source;
- credential ID do autorizador e timestamp server-side;
- classificação do conteúdo.

O scope deve coincidir exatamente com o `task_type` derivado da fonte; não pode
ser ampliado pelo request administrativo.

`EVALUATION_ONLY` não concede autorização para uso neural. Feedback positivo ou
negativo é somente sinal de qualidade/preferência e nunca autoriza treinamento.

## Privacy e provenance

O privacy gate examina features, target, referências e metadados derivados.
Secrets, credenciais, `.env`, PII, dados financeiros pessoais, paths pessoais e
campos de conversa bruta são rejeitados. O registro de rejeição contém apenas
hashes e findings (`code`, `category`, `field_path`), sem eco do valor.

Cada candidato aceito preserva candidate ID, source type/ID, project ID, run e
conversation IDs quando permitidos, evidence refs, outcome, policy, signature e
timestamps. Conteúdo bruto não é copiado para manter lineage.

## Candidate Store

A migração `0005_training_candidates.sql` adiciona o store ao mesmo PostgreSQL
usado pela persistência operacional. `memory` existe somente para dev/test;
`local_json` é rejeitado e nenhum candidate/dataset é versionado no Git.

O store suporta create idempotente, query/count/filter por projeto, review,
exclude, authorize e revoke. A chave e o fingerprint impedem promoção duplicada
da mesma fonte/purpose. Updates usam lifecycle esperado para evitar transição
concorrente silenciosa.

## Lifecycle

| Estado | Significado | Próximas transições |
|---|---|---|
| `PROPOSED` | seguro no pre-screen, ainda sem autorização | authorize, exclude |
| `REVIEW_REQUIRED` | qualidade/contradição exige humano | review→proposed, exclude |
| `AUTHORIZED` | elegível e autorizado para um purpose | exclude, revoke, futuro consume |
| `EXCLUDED` | fora de escopo/qualidade/policy | terminal nesta etapa |
| `CONSUMED` | reservado ao futuro dataset, com dataset lineage | revoke |
| `REVOKED` | autorização retirada | terminal; reautorização bloqueada |

`CONSUMED` possui integração interna testada, mas não endpoint público antes do
Canonical Dataset. Revogação preserva dataset IDs para auditoria futura; não
implementa unlearning neural.

## Readiness V2

`dataset-readiness-v2` mede volume, diversidade de source/task/purpose, outcomes
conhecidos, QA, provenance verificada, duplicação e contradições. O volume mínimo
vem de `PEDROCORE_DATASET_READINESS_MIN_AUTHORIZED`; ausente, o resultado é
fail-closed com `READINESS_VOLUME_POLICY_NOT_CONFIGURED`. Contagem isolada nunca
produz `DATASET_READY`.

## API administrativa

- `POST /api/training-candidates/select` — seleção técnica explícita;
- `POST /api/training-candidates/{id}/authorize|review|exclude|revoke` — capability admin;
- `GET /api/training-candidates/{project}` — query/filter admin e project-bound;
- `GET /api/training-candidates/{project}/readiness` — auditoria V2 admin.

## Estado da Era 3

- **IMPLEMENTED:** Candidate Acquisition Foundation;
- **BLOCKED:** Canonical Dataset V1, aguardando readiness real;
- **NOT STARTED:** Hugging Face, Fine-Tuning e Local Provider treinado.

## Navegação

- [[DATASET_FOUNDATION]]
- [[DATASET_READINESS_AUDIT]]
- [[CONTRATO_TRAINING_DATA_CANDIDATE]]
