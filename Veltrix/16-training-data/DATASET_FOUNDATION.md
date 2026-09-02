# Dataset Foundation

Estado: **IMPLEMENTED**. Policies: `dataset-foundation-v1` e
`training-acquisition-v1`.

A fundação separa três conceitos:

`Operational Data ≠ Training Candidate ≠ Canonical Training Example`

Operational Memory continua sendo a memória operacional autoritativa. Um
Training Candidate é somente uma projeção derivada, com provenance e
autorização. A Etapa 13A adiciona um Candidate Store no mesmo PostgreSQL
operacional, mas ainda não existe Canonical Dataset, download de modelo,
tokenização ou treinamento.

## Fluxo

`explicit source selection → eligibility pre-screen → privacy/provenance → explicit authorization → eligible candidate → Candidate Store`

Não há varredura das fontes. `automatic_collection=false` permanece invariável.
Sem autorização, uma proposta segura pode ser registrada como `PROPOSED`, mas
continua `NOT_ELIGIBLE_FOR_TRAINING`.

O ID e o fingerprint são determinísticos sobre conteúdo estruturado e
referências, sem depender dos timestamps observacionais. Os selectors consultam
as entidades operacionais existentes por `project_id + source_id`; a API não
aceita features, evidence refs, authorization, candidate ID ou provenance
fornecidos pelo cliente.

## Exclusões fail-closed

- provenance ausente, desconhecida, duplicada ou não verificada;
- projeto divergente;
- uso neural não autorizado;
- conversa/prompt/resposta brutos;
- secrets, credenciais, `.env`, PII e dados financeiros pessoais;
- conteúdo restrito ou confidencial sem aprovação específica;
- payload acima do limite.

Uma rejeição de privacidade persiste apenas hashes de referência, lifecycle e
códigos de finding. O material rejeitado, inclusive `source_id` quando
sensível, não entra no Candidate Store.

## Navegação

- [[CONTRATO_TRAINING_DATA_CANDIDATE]]
- [[HISTORICAL_RISK_INTELLIGENCE]]
- [[DATASET_READINESS_AUDIT]]
- [[TRAINING_CANDIDATE_LIFECYCLE]]
