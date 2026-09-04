# Veltrix — Roteiro NotebookLM

Atualizado em: 03/09/2026 · **ESTUDO ATUAL**

> A versão anterior deste roteiro apontava para uma árvore `docs/` que **não
> existe mais** — as 14 fontes estavam quebradas. Os caminhos abaixo foram
> verificados um a um contra o repositório em 03/09/2026.

Caminhos relativos à raiz do repositório.

---

## Fontes recomendadas

Dezenove documentos, escolhidos para cobrir o sistema sem afogar o notebook.
Importar nesta ordem.

### Estado e versionamento

1. `README.md`
2. `VERSION.md`
3. `Veltrix/19-encerramento-final/VELTRIX_FINAL_FUNCTIONAL_GATE.md`
4. `Veltrix/09_STATUS_ATUAL.md`

### Arquitetura

5. `Veltrix/17-veltrix/VELTRIX_FINAL_STATE.md`
6. `Veltrix/20-control-plane/PEDROCORE_CONTROL_PLANE_FINAL_STATE.md`
7. `Veltrix/20-control-plane/PEDROCORE_UNIVERSAL_CONTRACTS_REFERENCE.md`
8. `Veltrix/16-plataforma/PLATFORM_EVOLUTION_FINAL_STATE.md`

### Risk Engine

9. `Veltrix/15-risk-engine/RISK_ENGINE_V2_BASELINE.md`
10. `Veltrix/15-risk-engine/RISK_CONSOLE.md`
11. `Veltrix/15-risk-engine/PROJECT_REGISTRY.md`

### Learning, dataset e providers

12. `Veltrix/16-training-data/DATASET_READINESS_AUDIT.md`
13. `Veltrix/14-intelligence-layer/INTELLIGENCE_LAYER_OVERVIEW.md`

### Segurança e história

14. `Veltrix/MOC_SEGURANCA.md`
15. `Veltrix/17-veltrix/MIGRACAO_PEDROCORE_VELTRIX.md`

### Material de estudo já destilado

16. `Veltrix/15-estudo-pedrocore/PEDROCORE_RESUMO_EXECUTIVO.md`
17. `Veltrix/15-estudo-pedrocore/PEDROCORE_FLUXO_COMPLETO.md`
18. `Veltrix/15-estudo-pedrocore/VELTRIX_RISK_ENGINE_ESTUDO.md`
19. `Veltrix/15-estudo-pedrocore/VELTRIX_LINHA_DO_TEMPO.md`

### Se quiser menos fontes

Um conjunto mínimo de cinco que ainda dá uma visão correta: **1, 3, 5, 9, 16**.

### O que deliberadamente ficou de fora

Fechamentos de frente antigos (`Veltrix/13-fechamento/`), documentos de produto
`V1`–`V5.1.9` e a auditoria de julho. São **históricos corretos**, mas
descrevem estados superados — em um notebook eles competem com o presente e
produzem respostas datadas.

---

## Aviso a dar ao notebook antes de perguntar

```text
Estes documentos descrevem o Veltrix, um control plane de IA. Alguns trechos
são checkpoints datados: quando um texto citar contagem de testes, HEAD de Git
ou "estado atual" com data anterior a 03/09/2026, trate como snapshot
histórico, não como estado corrente. O estado corrente está no Final Functional
Gate e no topo do 09_STATUS_ATUAL.
```

## Perguntas para fazer

- Explique o Veltrix em cinco níveis: criança, estudante, dev júnior, arquiteto
  e recrutador.
- Qual a diferença entre Runtime Plane e Learning Plane, e como ela é garantida?
- O que o Risk Engine faz e o que ele explicitamente não faz?
- O que eram os problemas P1 a P5 e como cada um foi fechado?
- Por que `BLOCK` é descrito como "intransponível por construção"?
- Qual a diferença entre provider conhecido, configurado, homologado,
  autorizado, executável e executado?
- Por que uma falha do Gemini não vira mais resposta do Mock no chat?
- Por que `CONTROL_PLANE_READY` não significa `DATASET_READY`?
- O que mudou e o que **não** mudou no rename PedroCore → Veltrix?
- Por que produto, API e tag Git têm números diferentes?
- Monte a linha do tempo do projeto a partir das fontes.
- Quais riscos permanecem e quais foram formalmente adiados?

## Prompt para podcast

```text
Crie um roteiro de podcast técnico em português explicando o Veltrix como AI
Runtime & Learning Control Plane. Cubra: os dois planos, o Risk Engine que não
executa, os seis estados de provider, a governança de dataset com
DATASET_NOT_READY, e o Final Functional Gate que fez a interface parar de
mentir sobre quem respondeu. Diga explicitamente que não há modelo treinado nem
fine-tuning. Tom honesto, sem marketing.
```

## Prompt para quiz

```text
Crie um quiz de 20 questões de múltipla escolha sobre o Veltrix. Cubra os dois
planos, Risk Engine V1 e V2 (P1–P5), gates e Execution Contract, Risk Console,
Project Registry, Universal Contracts, os seis estados de provider, semântica
do fallback por boundary, DATASET_NOT_READY e Functional Freeze. Inclua
gabarito com explicação curta.
```

## Prompt para resumo executivo

```text
Resuma o Veltrix em uma página para um stakeholder técnico. Separe: o que é, o
que faz, o que explicitamente não faz, estado atual, o que foi formalmente
adiado e riscos remanescentes. Não afirme capacidade de treinamento.
```

## Prompt para revisar arquitetura

```text
Analise a arquitetura do Veltrix a partir das fontes. Explique a fronteira
Runtime/Learning e como ela é verificada, o caminho de uma requisição de chat
até o provider, o pipeline do Risk Engine até o Execution Contract, e os
guardrails de segurança. Liste o que precisaria ser resolvido antes de expor a
API à internet.
```

## Links relacionados

- [[../MOC_ESTUDO_PEDROCORE]]
- [[PEDROCORE_ROTEIRO_CLAUDE_OBSIDIAN]]
- [[PEDROCORE_RESUMO_EXECUTIVO]]
- [[VELTRIX_LINHA_DO_TEMPO]]
