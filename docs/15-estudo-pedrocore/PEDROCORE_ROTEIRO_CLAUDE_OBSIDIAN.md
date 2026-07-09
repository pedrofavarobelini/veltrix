# PedroCore - Roteiro Claude + Obsidian

Atualizado em: 09/07/2026

## Como estudar com Claude

Use Claude para explicar, comparar e revisar os documentos. Nao peca para ele inventar estado nao documentado.

Prompt inicial:

```text
Vou te enviar documentos do PedroCore IA. Quero que voce estude como um revisor tecnico frio. Separe o que esta implementado, o que e futuro, o que e limite de seguranca e o que seria risco se fosse confundido.
```

## Como pedir revisao

```text
Revise estes documentos e procure inconsistencias factuais. Foque em: modelo treinado, fine-tuning, provider real, local_model, local_qa, Report Memory, FinGuard, release gate e status de testes.
```

## Como pedir mapa mental

```text
Crie um mapa mental hierarquico do PedroCore IA com arquitetura, rotas, modulos, providers, seguranca, memoria, eval harness e integracao futura com FinGuard.
```

## Como pedir explicacao linha por linha

```text
Explique este documento por secoes. Para cada secao, diga: objetivo, decisao tecnica, risco que evita e como eu explicaria isso em entrevista.
```

## Como transformar docs em notas Obsidian

1. Crie uma nota por conceito: `local_qa`, `local_model`, `Report Memory`, `Eval Harness`, `Release Gate`, `Policy Enforcement`.
2. Use links para MOCs: `[[MOC_PEDROCORE_IA]]`, `[[MOC_ARQUITETURA]]`, `[[MOC_TESTES]]`.
3. Em cada nota, inclua "E", "Nao e", "Status atual", "Risco se confundido".
4. Marque como futuro tudo que depender de provider real, transport local, RAG ou integracao real com FinGuard.

## Como usar MOCs

- Comece por [[MOC_PEDROCORE_IA]].
- Para arquitetura, use [[MOC_ARQUITETURA]].
- Para seguranca, use [[MOC_SEGURANCA]].
- Para testes, use [[MOC_TESTES]].
- Para status, use [[MOC_VERSOES_STATUS]].

## Como revisar decisoes tecnicas

Perguntas uteis:

- Qual decisao impede provider real acidental?
- Qual decisao mantem FinGuard como projeto externo?
- Qual decisao separa QA Intelligence de executor de testes?
- Qual decisao impede treinamento/fine-tuning?
- Qual decisao limita release gate a `local_qa`?

## Como se preparar para entrevista

Pratique respostas curtas:

- "PedroCore e um orquestrador seguro de IA, nao um LLM proprio."
- "Eu implementei guardrails: safe mode, policy enforcement, fallback, release gate conservador e eval harness."
- "O projeto separa contexto tecnico de treinamento: relatorios viram sinais, nao pesos."
- "O local_model foi preparado como opt-in, mas sem transport real nesta frente."
- "FinGuard entra como consumidor read-only; integracao real do cliente e frente separada."

## Checklist de honestidade

- Nao dizer que houve fine-tuning.
- Nao dizer que `local_model` roda modelo real hoje.
- Nao dizer que provider real foi usado na auditoria.
- Nao dizer que FinGuard foi alterado ou lido.
- Nao dizer que Report Memory e RAG.
- Nao dizer que release gate e autonomo sem revisao humana.

## Links relacionados

- [[../MOC_ESTUDO_PEDROCORE]]
- [[../MOC_PEDROCORE_IA]]
- [[PEDROCORE_ROTEIRO_NOTEBOOKLM]]
- [[PEDROCORE_GLOSSARIO]]
- [[../MOC_QA_SAFETY_HARDENING]]
