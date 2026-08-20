# Contrato — Safe Reuse Foundation

## Decisão, não cache

`POST /api/safe-reuse/evaluate` classifica um candidato como
`DIRECT_REUSE`, `TEMPLATE_REUSE`, `KNOWLEDGE_REUSE`, `ANTI_PATTERN` ou
`NO_REUSE`. A resposta sempre declara:

- `provider_bypass=false`;
- `reusable_response_returned=false`.

Nesta Era, nem mesmo `DIRECT_REUSE` retorna resposta cacheada ou evita a
execução normal do provider. A decisão é somente informação para um consumidor
autenticado.

## Fingerprints

Os fingerprints usam somente assinaturas `sha256:` e metadados delimitados:

- `input_signature`: identidade canônica da entrada;
- `context_signature`: identidade do contexto relevante;
- `data_signature`: versão/estado dos dados relevantes;
- escopos de projeto, usuário e família;
- permissions e environment;
- `temporal_state_signature`: janela/estado temporal aplicável;
- `policy_version` e `dependency_version`.

As assinaturas servem para comparar equivalência; não provam autorização e não
substituem a identidade técnica vinculada ao projeto.

## Invalidação

Direct reuse exige igualdade de todas as dimensões. Template e knowledge reuse
podem variar input/context/data porque não reutilizam uma resposta, mas exigem
igualdade de escopo, permissões, ambiente, estado temporal, policy e
dependências. Toda modalidade exige validação completa e não expirada.

Knowledge e anti-pattern resolvem o `memory_id` na Operational Memory existente
do mesmo projeto. Não há segunda memória. Memória ausente, inativa ou de tipo
incompatível resulta em `NO_REUSE`.

Na dúvida, o contrato falha de modo conservador com reason codes explícitos.
