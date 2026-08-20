# Contrato — Retrieval V1

## Fronteira

`POST /api/operational-memory/retrieve` é uma consulta técnica autenticada,
isolada por projeto e somente leitura. Ela não altera Operational Memory, não
executa provider e não injeta conteúdo no Prompt Builder.

## Entrada

- `producer` deve corresponder à credencial técnica autenticada;
- `project_id` deve corresponder ao projeto autenticado;
- `keywords` são termos estruturados e limitados, não um prompt bruto;
- filtros opcionais: `task_type`, tipos de padrão, lifecycle, confiança,
  evidência e recência;
- no máximo cinco resultados e 2.000 caracteres de contexto projetado.

Campos desconhecidos são rejeitados. `raw_query`, prompt, resposta, segredo e
payload livre não fazem parte deste contrato.

## Seleção

A policy `retrieval-v1` combina correspondência lexical, task type, confiança,
evidência, recência e lifecycle. O padrão é consultar apenas `ACTIVE` e
`MITIGATED`; `ANTI_PATTERN` exige opt-in explícito. Filtros e limites produzem
reason codes rastreáveis.

PostgreSQL usa FTS `simple` e índice GIN. Os modos de teste locais mantêm a
mesma semântica com tokenização determinística. Não há embeddings ou vector DB.

## Saída e observabilidade

A resposta contém somente uma projeção limitada: IDs, tipo, lifecycle,
task type, resumo já sanitizado, confiança, contagem de evidências, score,
policy e timestamp. Evidências completas e memória integral não são retornadas.

Quando a observabilidade local existente está habilitada, são registrados
query ID, candidate IDs, scores, selected IDs, rejection reasons e policy.
Keywords, resumo e conteúdo de memória não são registrados.
