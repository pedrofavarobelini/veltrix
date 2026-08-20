# Safe Reuse Foundation

Safe Reuse V1 separa cinco intenções:

- `DIRECT_REUSE`: equivalência forte, ainda sem bypass;
- `TEMPLATE_REUSE`: estrutura validada, nunca resposta pronta;
- `KNOWLEDGE_REUSE`: referência ativa da Operational Memory;
- `ANTI_PATTERN`: aviso explícito derivado da mesma Operational Memory;
- `NO_REUSE`: fallback obrigatório diante de dúvida ou invalidação.

O subsistema não persiste respostas, não cria cache, não chama providers, não
modifica prompt e não executa ações. A autenticação técnica e o isolamento por
projeto são herdados do mesmo boundary usado por Reports, Outcomes, Operational
Memory e Retrieval.

## Garantia da Era 1

Um candidato `DIRECT_REUSE` continua a percorrer a execução normal porque
`provider_bypass` é literal e invariavelmente `false`. Evoluções capazes de
evitar provider exigem uma etapa futura, autorização própria e novos gates de
segurança.

## Navegação

- [[CONTRATO_SAFE_REUSE]]
- [[RETRIEVAL_V1]]
