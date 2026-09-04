# Veltrix — Roteiro Claude + Obsidian

Atualizado em: 03/09/2026 · **ESTUDO ATUAL**

Como usar um agente para estudar este vault sem que ele confunda história com
presente.

---

## A regra que evita 90% dos erros

Este vault preserva história de propósito. Muitos documentos são **verdadeiros
sobre a data em que foram escritos** e falsos sobre hoje. Um agente que lê tudo
como se fosse estado atual vai afirmar que a suíte tem 296 testes, que o
projeto se chama PedroCore e que a publicação ainda é futura.

Diga isto antes de qualquer pergunta:

```text
Vou te enviar documentos do Veltrix. O vault preserva história deliberadamente.
Antes de afirmar qualquer coisa como estado atual, verifique:

1. o fechamento canônico é
   Veltrix/19-encerramento-final/VELTRIX_FINAL_FUNCTIONAL_GATE.md;
2. o estado corrente está no TOPO de Veltrix/09_STATUS_ATUAL.md;
3. qualquer seção rotulada SNAPSHOT, CHECKPOINT HISTÓRICO ou SUPERSEDED é
   história, não presente;
4. contagem de testes, HEAD de Git e "resultado atual" com data anterior a
   03/09/2026 são snapshots;
5. `pedrocore` minúsculo é identificador técnico preservado, não erro de
   branding.

Separe sempre: implementado · fundação · adiado · nunca iniciado.
```

## Ordem de leitura para o agente

```text
1. Veltrix/MOC_VELTRIX.md ............................ entrada do grafo
2. Veltrix/19-encerramento-final/VELTRIX_FINAL_FUNCTIONAL_GATE.md
3. Veltrix/15-estudo-pedrocore/PEDROCORE_RESUMO_EXECUTIVO.md
4. Veltrix/15-estudo-pedrocore/VELTRIX_LINHA_DO_TEMPO.md
5. Veltrix/17-veltrix/VELTRIX_FINAL_STATE.md
6. Veltrix/15-estudo-pedrocore/VELTRIX_RISK_ENGINE_ESTUDO.md
7. Veltrix/20-control-plane/PEDROCORE_CONTROL_PLANE_FINAL_STATE.md
8. Veltrix/15-estudo-pedrocore/PEDROCORE_FLUXO_COMPLETO.md
9. Veltrix/16-training-data/DATASET_READINESS_AUDIT.md
```

## Como pedir revisão factual

```text
Revise estes documentos procurando inconsistências factuais. Foque em: modelo
treinado, fine-tuning, dataset pronto, provider real chamado, local_model com
transport, publicação pendente, e qualquer número apresentado como atual.
Aponte a data de cada afirmação.
```

## Como pedir explicação por seções

```text
Explique este documento por seções. Para cada uma diga: objetivo, decisão
técnica tomada, risco que ela evita, e como eu explicaria isso em entrevista.
```

## Como transformar em notas Obsidian

1. Uma nota por conceito: `Runtime Plane`, `Learning Plane`, `Risk Engine`,
   `Execution Contract`, `Blast Radius`, `Project Registry`,
   `Universal Contracts`, `Evidence Platform`, `Safe Mode`, `Fallback`.
2. Em cada nota, quatro campos: **É** · **Não é** · **Estado atual** ·
   **Risco se confundido**.
3. Linkar para os hubs: `[[MOC_VELTRIX]]`, `[[MOC_ARQUITETURA]]`,
   `[[MOC_SEGURANCA]]`, `[[MOC_TESTES]]`.
4. Marcar como adiado tudo que depender de segundo provider homologado,
   transport local real, RAG ou dataset canônico.

## Hubs do vault

- [[../MOC_VELTRIX]] — entrada
- [[../MOC_ARQUITETURA]] — camadas, endpoints, módulos
- [[../MOC_SEGURANCA]] — safe mode, policy, limites
- [[../MOC_TESTES]] — resultado corrente e snapshots
- [[../MOC_FECHAMENTOS]] — canônico atual e fechamentos históricos
- [[../MOC_VERSOES_STATUS]] — os três eixos de versão
- [[../MOC_ESTUDO_PEDROCORE]] — este study pack

## Perguntas boas para revisar decisões

- Qual decisão impede provider real acidental?
- Qual decisão torna `BLOCK` intransponível em vez de apenas calculado?
- Qual decisão separou identidade de capacidade no Project Registry?
- Por que a submissão de risco virou contrato próprio em vez de campo no
  envelope?
- Qual decisão impede que dado operacional vire candidato de treino sozinho?
- Por que o fallback é por boundary e não global?
- Qual decisão preservou seis contratos congelados durante o rename?

## Como se preparar para entrevista

- "O Veltrix é um control plane de IA: governa identidade, autorização,
  provider, risco e evidência entre agentes e execução."
- "Ele não executa nada, e isso é regra com teste negativo, não promessa."
- "A separação entre o plano que responde agora e o que aprende depois é
  verificada por teste, não por convenção."
- "O motor de risco emite um contrato assinado; quem executa é outro."
- "Não há modelo treinado: a fundação de dataset existe, a população
  autorizada é zero, e o readiness correto é `DATASET_NOT_READY`."
- "O último bug que corrigi foi a interface mentindo sobre qual IA respondeu."

## Checklist de honestidade

- Não dizer que houve fine-tuning ou que existe modelo próprio.
- Não dizer que `local_model` roda um LLM real hoje.
- Não dizer que o dataset está pronto.
- Não dizer que o Risk Engine executa operações.
- Não dizer que Report Memory é RAG.
- Não dizer que a publicação é futura — ela aconteceu.
- Não apresentar snapshot de checkpoint como estado atual.
- Não tratar `pedrocore` minúsculo como branding esquecido.

## Links relacionados

- [[../MOC_ESTUDO_PEDROCORE]]
- [[PEDROCORE_ROTEIRO_NOTEBOOKLM]]
- [[PEDROCORE_GLOSSARIO]]
- [[PEDROCORE_FLUXO_COMPLETO]]
