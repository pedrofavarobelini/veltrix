# Retrieval V1

## Objetivo

Recuperar padrões úteis da Operational Memory de forma limitada, explicável e
isolada. A consulta segue:

`Context → Query estruturada → Candidates → Ranking → Selected Memories`

## Relevância

O ranking `retrieval-v1` é determinístico:

- 35% correspondência lexical;
- 20% task type;
- 15% confiança do padrão;
- 10% volume de evidências, saturado em três amostras;
- 10% recência;
- 10% lifecycle.

Pertencer ao mesmo projeto é uma fronteira de autorização, não um sinal de
relevância. Por isso, uma consulta sobre dívida técnica não seleciona memória
de autenticação sem correspondência lexical.

## Limites de segurança

- nenhum embedding ou banco vetorial;
- nenhuma execução de provider;
- nenhuma mutação ou promoção de memória;
- nenhuma inserção automática no Prompt Builder;
- no máximo cinco projeções e 2.000 caracteres;
- lifecycle resolvido e anti-pattern exigem solicitação explícita;
- falha de persistência fecha a consulta com erro operacional sanitizado.

O consumidor decide se e como usa a projeção. Nesta etapa o PedroCore somente
expõe a recuperação segura e auditável.
