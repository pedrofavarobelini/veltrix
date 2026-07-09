# PedroCore - Roteiro NotebookLM

Atualizado em: 09/07/2026

## Fontes recomendadas

Importar nesta ordem:

1. `README.md`
2. `VERSION.md`
3. `docs/09_STATUS_ATUAL.md`
4. `docs/00_MAPEAMENTO_GERAL_PEDROCORE.md`
5. `docs/13-fechamento/FECHAMENTO_PEDROCORE_ECOSYSTEM_INTELLIGENCE_SUITE_01.md`
6. `docs/13-fechamento/FECHAMENTO_PEDROCORE_MODEL_FOUNDATION_01.md`
7. `docs/10-contratos/CONTRATO_ECOSYSTEM_ASSISTANT.md`
8. `docs/10-contratos/CONTRATO_REPORT_MEMORY.md`
9. `docs/14-intelligence-layer/INTELLIGENCE_LAYER_OVERVIEW.md`
10. `docs/14-intelligence-layer/REPORT_MEMORY.md`
11. `docs/14-intelligence-layer/LOCAL_MODEL_PROVIDER.md`
12. `docs/14-intelligence-layer/EVAL_HARNESS.md`
13. `docs/15-estudo-pedrocore/PEDROCORE_AUDITORIA_STUDY_MAP_01.md`
14. `docs/15-estudo-pedrocore/PEDROCORE_VEREDITO_FINAL.md`

## Ordem de leitura

1. Entender a visao geral.
2. Entender o estado atual.
3. Ler o mapa geral.
4. Ler contratos.
5. Ler memoria/local model/eval harness.
6. Ler auditoria e veredito.

## Perguntas para fazer ao NotebookLM

- Explique o PedroCore em 5 niveis: crianca, estudante, dev junior, arquiteto e recrutador.
- Quais partes estao prontas e quais ainda sao futuras?
- Qual e a diferenca entre `local_qa` e `local_model`?
- Por que Report Memory nao e treinamento?
- Por que provider real fica bloqueado por padrao?
- Como o FinGuard entra no fluxo sem ser alterado?
- Quais sao os riscos restantes?
- Monte uma linha do tempo das frentes recentes.
- Explique o fluxo completo de `/api/orchestrate`.
- Crie perguntas de entrevista sobre este projeto.

## Prompt para podcast

```text
Crie um roteiro de podcast tecnico, em portugues, explicando o PedroCore IA como core/orquestrador seguro de IA. Destaque que ele nao e modelo treinado, nao faz fine-tuning, usa safe mode, tem QA local, memoria tecnica default-off e local_model preparado mas sem transport real. Use tom honesto, sem marketing exagerado.
```

## Prompt para quiz

```text
Crie um quiz com 20 perguntas de multipla escolha sobre o PedroCore IA. Cubra rotas, providers, safe mode, local_qa, local_model, Report Memory, Eval Harness, FinGuard como consumidor read-only e riscos restantes. Inclua gabarito e explicacao curta.
```

## Prompt para resumo executivo

```text
Resuma o PedroCore IA em uma pagina para stakeholder tecnico. Separe: estado atual, o que ja faz, o que nao faz, validacoes realizadas, riscos e proximos passos.
```

## Prompt para revisar arquitetura

```text
Analise a arquitetura do PedroCore IA a partir das fontes. Explique o fluxo interno de /api/orchestrate, identifique guardrails de seguranca e liste riscos que precisariam ser resolvidos antes de uso em producao com consumidores reais.
```
