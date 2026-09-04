# Veltrix — Risk Engine (estudo)

Atualizado em: 03/09/2026 · **ESTUDO ATUAL**

Este documento existe porque o Risk Engine é o maior subsistema do Veltrix e a
documentação técnica dele é densa demais para servir de primeira leitura. Aqui
está o suficiente para **entender**; a referência completa está em
[[../15-risk-engine/RISK_ENGINE_V2_BASELINE]].

---

## 1. O problema que ele resolve

Uma IA propõe uma operação: rodar uma migration, apagar registros, alterar um
schema, subir um deploy. Antes de alguém executar, três perguntas precisam de
resposta:

- **O que essa operação realmente faz?** (a intenção é ambígua?)
- **Até onde ela alcança?** (o que quebra se der errado?)
- **Isso pode prosseguir?** (e sob quais restrições?)

O Risk Engine responde as três. **E não executa nada.**

Essa é a decisão de projeto mais importante dele: analisar e executar são
responsabilidades separadas. O Veltrix continua com inteligência, contexto e
memória; o QA continua com evidência; o Agent continua com execução; o Risk
Engine só analisa e governa risco.

## 2. O pipeline

```text
RiskRequest
  → Intent .................. o que a operação pretende fazer
  → Resolved Context ........ qual projeto, qual ambiente, quais fatos
  → Prompt Quality .......... o pedido está bem formado?
  → Ambiguity ............... há mais de uma leitura possível?
  → Scope ................... o que está dentro e fora do alvo
  → Signals ................. cada regra acionada vira evidência rastreável
  → Findings ................ os achados, com origem
  → Seis dimensões .......... dados · segurança · migração ·
                              escopo · regressão · operação
  → Blast radius ............ alcance, com unidade
  → Scenarios ............... o que pode dar errado, dado ESTE payload
  → GATE .................... ALLOW | REVIEW | BLOCK
  → Execution Contract ...... restrições verificáveis, assinadas
       ⇣
  ═══ A EXECUÇÃO ACONTECE FORA DO VELTRIX ═══
       ⇣
  → Post-Execution QA ....... resultado produzido × contrato autorizado
  → Execution Outcome V2
  → Operational Memory
  → Historical Risk Intelligence
```

### Por que seis dimensões e não um número

Um score único é opaco: "risco 7" não diz se o perigo é perder dado ou quebrar
uma regressão. Seis dimensões independentes preservam a informação que importa
para decidir. `project_id` continua sendo fronteira de autorização.

### Por que o contrato é assinado

O Execution Contract transforma a análise em restrições **verificáveis**. HMAC
cobre todos os campos, ele tem prazo de validade, e um override humano
autorizado é registrado — não apagado. Depois da execução, o pós-execução
compara o que aconteceu com o que havia sido autorizado.

## 3. V1 → V2: os cinco problemas

O V1 funcionava. O V2 nasceu de uma auditoria honesta que listou cinco defeitos
objetivos e os fechou um a um, sem enfraquecer nenhuma invariante e sem tocar
nos contratos congelados.

| | Problema | Por que era problema | Fechado em |
|---|---|---|---|
| **P1** | A persistência do risco não era do risco | o domínio Risk dependia de armazenamento de outro domínio | **R2** (store próprio) + **R2.1** (Historical Risk passou a consumir esse store) |
| **P2** | "Simulação" era enumeração fixa | os cenários não olhavam o payload — eram sempre os mesmos | **R5** (Scenario Simulation V2) |
| **P3** | Blast radius não tinha unidade | um número sem unidade não significa nada | **R3** (métrica, campo aditivo) |
| **P4** | O gate era calculado, mas não intransponível por construção | nada *provava* que não havia caminho de bypass | **R1** (testes negativos de gate e bypass) |
| **P5** | O Risk Engine não usava os Universal Contracts | a submissão de risco não tinha contrato próprio | **R4** (contrato `pedrocore-risk-request/v1`) |

### Duas lições do processo que valem mais que o resultado

**R1 veio primeiro de propósito.** Ele não muda comportamento nenhum — só
acrescenta testes negativos. Provar que a proteção existe antes de mexer em
qualquer coisa é o que torna o resto seguro.

**R2 sozinho não fechou P1.** Criar o store próprio parecia suficiente, mas o
serviço histórico continuava lendo de outro lugar. A auditoria pegou isso, e o
R2.1 fechou o problema ponta a ponta. É o tipo de meia-correção que passa
despercebida em quase todo projeto.

### O que o V2 deliberadamente **não** fez

Não transformou o Risk Engine em executor, não alterou os contratos V1
congelados (a submissão entrou como contrato **próprio**, em vez de mudar o
envelope de integração) e não enfraqueceu nenhuma invariante.

## 4. Risk Console

A interface do motor: **TUI** e **CLI** (`veltrix risk`; `pedrocore` continua
como alias), mais a rota HTTP do contrato universal.

Três estados exclusivos de tela — **entrada**, **revisão de contexto**,
**resultado**. No resultado a ordem é:

```text
gate → resumo da operação → principais riscos → por quê → o que fazer
```

com toda a evidência preservada em seis abas, uma renderizada por vez.

O problema que isso resolveu: formulário, gate, dimensões, alcance, cenários,
histórico e detalhes técnicos competiam pela mesma primeira viewport. Nenhum
estava errado; juntos, nenhum era legível. **A resposta foi ordem, não
remoção.**

E há um teste de paridade que roda a mesma requisição confirmada e compara
gate, dimensões, alcance, cenários, achados e recomendações: **layout não pode
mudar decisão, e isso é provado, não prometido.**

## 5. Project Registry

O seletor de projeto lia a lista do **Capability Manifest**. Isso amarrava duas
coisas sem relação: *existir* e *saber fazer*. Um usuário com projeto próprio
não conseguia analisá-lo, porque não havia manifesto escrito no repositório.

O Project Registry separou **identidade** de **capacidade**:

- um projeto criado pelo usuário aparece, é selecionado, chega ao `RiskRequest`
  e é analisado;
- o que ele **não** ganha é permissão — sem manifesto, os fatos ausentes ficam
  `UNKNOWN`;
- a guarda de análise passou a exigir *projeto registrado e ativo* em vez de
  *capability `risk_analysis`*: guarda de **identidade**, não de capacidade.

Persistência com Protocol + InMemory + LocalJson + PostgreSQL, migration
aditiva `0012`, seis projetos-semente. E um teste que lê o AST à procura de
`if project_id == "<nome>"`, para que a lista de projetos iniciais nunca vire
uma lista de casos especiais.

Não existe sincronização com GitHub; `repository_url` é metadado.

## 6. Como isso conversa com o resto do Veltrix

```text
Runtime Plane ──► Risk Engine ──► Execution Contract
                        │
                        └──► (execução externa) ──► Post-Execution QA
                                                         │
                                    Evidence Platform ◄───┘
                                            │
                                    Learning Plane
                                    (Operational Memory,
                                     Historical Risk)
```

O Historical Risk fecha o ciclo sem duplicar armazenamento: os padrões vêm da
Operational Memory, e uma entrada só participa quando a policy é conhecida,
compatível e solicitada. **Versões diferentes nunca são agregadas em silêncio.**

## 7. Cinco perguntas para testar se você entendeu

1. Se o gate é `BLOCK`, o que impede alguém de executar mesmo assim?
2. Por que a submissão de risco virou um contrato próprio em vez de um campo no
   envelope de integração?
3. O que o R2.1 corrigiu que o R2 tinha deixado pela metade?
4. Um projeto sem Capability Manifest pode ser analisado? E pode receber
   permissão?
5. Quem executa a operação depois que o contrato é emitido?

*(Respostas: §3 P4 · §3 P5 · §3 · §5 · §1.)*

## Referência completa

- [[../15-risk-engine/RISK_ENGINE_V2_BASELINE]] — baseline, P1–P5, R0–R5
- [[../15-risk-engine/RISK_CONSOLE]] — guia de uso do console
- [[../15-risk-engine/PROJECT_REGISTRY]] — catálogo de projetos
- [[../15-risk-engine/RISK_ENGINE_FOUNDATION]] — fundação V1
- [[../15-risk-engine/PRE_EXECUTION_RISK_V1]] — pipeline híbrido
- [[../15-risk-engine/EXECUTION_CONTRACT_RISK_GATES]] — contrato e gates
- [[../15-risk-engine/POST_EXECUTION_QA]] — pós-execução
- [[../15-risk-engine/HISTORICAL_RISK_INTELLIGENCE]] — inteligência histórica

## Links relacionados

- [[../MOC_ESTUDO_PEDROCORE]]
- [[PEDROCORE_RESUMO_EXECUTIVO]]
- [[PEDROCORE_MAPA_MENTAL]]
- [[VELTRIX_LINHA_DO_TEMPO]]
