# Contrato — Training Example Candidate

Estado: **IMPLEMENTED** — Dataset Foundation V1 + Candidate Acquisition V1.

`TrainingExampleCandidate` é uma projeção derivada e autorizada de evidência
real. Não é conversa bruta, não é dataset canônico e não inicia treinamento.

## Fontes mapeadas

- Interaction Outcome;
- Operational Pattern;
- Report Intelligence V2;
- QA Evidence;
- Risk Analysis;
- Execution Outcome;
- Human Feedback explícito.

Cada fonte tem `automatic_collection=false`. Um selector explícito resolve a
entidade no store operacional do próprio projeto e deriva somente features
estruturadas. O contrato exige projeto, schema,
policy, outcome observado, assinatura do conteúdo, instante e verificação da
evidência. Provenance desconhecida, não verificada ou de outro projeto bloqueia
o candidato.

## Privacidade e consentimento

O candidate precisa de autorização explícita para uso neural e informa a
classificação do conteúdo. Secrets, credenciais, `.env`, PII desnecessária,
dados financeiros pessoais, paths pessoais, conteúdo restrito e campos de
conversa bruta são rejeitados. Findings registram somente código, categoria e
campo; o valor detectado não volta na resposta.

Conteúdo confidencial só pode prosseguir quando a autorização também aprova
explicitamente essa classificação. A autorização verificável registra projeto,
scope, purpose, policy, source, ator e instante; 👍/👎 não preenche nenhum desses
campos.

O Candidate Store persiste lifecycle e lineage no mesmo PostgreSQL operacional.
Um `TrainingExampleCandidate` materializado existe somente em `AUTHORIZED` ou
`CONSUMED`; propostas ainda não são candidatas elegíveis para treinamento.

## Navegação

- [[DATASET_FOUNDATION]]
- [[HISTORICAL_RISK_INTELLIGENCE]]
- [[TRAINING_CANDIDATE_LIFECYCLE]]
