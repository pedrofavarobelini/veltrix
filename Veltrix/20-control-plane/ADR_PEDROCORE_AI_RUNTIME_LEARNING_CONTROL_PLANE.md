# ADR — Veltrix AI Runtime & Learning Control Plane

- **Identificador:** `ADR-PEDROCORE-CONTROL-PLANE-01`
- **Data:** 29/08/2026
- **Status:** Aceita
- **Escopo:** Eras 1 e 2 (baseline, auditoria e separação lógica)
- **Evidência de base:** [[PEDROCORE_CURRENT_ARCHITECTURE_BASELINE]]
- **Plano de execução:** [[PEDROCORE_CONTROL_PLANE_MIGRATION_MAP]]
- **Decisões técnicas anteriores:** [[07_DECISOES_TECNICAS]]

## Contexto

O Veltrix cresceu como um modular monolith FastAPI com 40 módulos e cerca de
25.500 linhas de Python em `apps/api/app/modules/`. A suíte passa integral
(1085 testes) e o lint está limpo. O sistema é saudável — o problema não é
qualidade de código.

O problema é que o Veltrix acumulou **duas responsabilidades de natureza
diferente** e não declarou em lugar nenhum que elas são diferentes:

1. **Responder agora.** Receber uma requisição, escolher provider, aplicar
   política, orquestrar, avaliar risco, responder, auditar. É síncrona,
   sensível a latência, e sua indisponibilidade é imediatamente visível.

2. **Aprender depois.** Coletar evidência governada da operação, avaliar
   elegibilidade, privacidade, proveniência e autorização, manter o ciclo de
   vida do candidato e medir prontidão de dataset. É assíncrona por natureza,
   insensível a latência, e sua indisponibilidade deveria ser invisível para
   quem só quer uma resposta.

Ambas existem e ambas estão implementadas. O que não existe é a **fronteira**.

## Problema

Sem fronteira declarada, três coisas ruins acontecem — e uma delas já aconteceu:

**A direção da dependência não é vigiada.** `orchestration/service.py` importa
`training_data.acquisition` no topo do módulo. O uso é estreito e legítimo
(atende a submissão governada de candidato, que chega pelo mesmo endpoint de
orquestração), mas o import de topo significa que uma falha de importação no
Learning Plane derruba a importação do Runtime Plane inteiro. O invariante
"se o aprendizado falhar, o assistente continua respondendo" vale hoje em
tempo de execução e **não** vale em tempo de importação.

**"Qual plano é este módulo?" não tem resposta verificável.** É uma pergunta
respondida por intuição sobre o nome da pasta. Um módulo novo pode nascer
ambíguo sem que nada reclame.

**Documentação de fronteira apodrece silenciosamente.** A auditoria da Era 1
encontrou quatro drifts, incluindo um `MOC_ARQUITETURA` que lista 8 endpoints
quando o código expõe 37. Uma fronteira que existe apenas em Markdown tem
exatamente essa expectativa de vida.

## Decisão

### 1. O Veltrix passa a ter dois planos declarados

```text
                       PEDROCORE
                           │
        ┌──────────────────┴──────────────────┐
        │                                     │
   Runtime Plane                        Learning Plane
   (responder agora)                    (aprender depois)
        │                                     │
        │      structured operational         │
        └──────── sources / evidence ────────►│
                  (contratos estáveis)
```

**Runtime Plane** — Orchestration, Providers, Assistant, Retrieval,
Operational Memory, Report Intelligence, Interaction Outcomes, Risk Engine,
Execution Contracts, Safe Reuse.

**Learning Plane** — Sources, Training Candidate Acquisition, Eligibility,
Privacy, Provenance, Authorization, Candidate Lifecycle, Dataset Foundation,
Dataset Readiness.

Além dos dois planos, dois agrupamentos de apoio são declarados explicitamente
porque fingir que não existem seria pior do que nomeá-los:

**Shared Kernel** — `caller_identity`, `contracts`, `audit`, `observability`,
`project_context`, `real_features`, `docs_graph`. Consumido pelos dois planos;
não pertence a nenhum.

**Consumer Capabilities** — `elyra_textual`, `elyra_multimodal`,
`elyra_learning`. Adaptadores de contrato por consumidor externo. São a
fronteira onde regra específica de projeto é legítima, precisamente para que
ela **não** fique no core genérico.

### 2. Continua sendo um modular monolith

Um processo, um `pyproject.toml`, um `app.main`. **Nenhum microsserviço.**
Nenhuma fila, nenhuma mensageria, nenhum novo deployable. A separação é
lógica e verificada, não física e distribuída.

### 3. A fronteira é código executável, não prosa

A separação vira um módulo de declaração (`app/architecture/planes.py`) e um
conjunto de testes de arquitetura. Concretamente:

- todo módulo sob `app/modules/` pertence a exatamente um agrupamento
  declarado — um módulo novo não declarado **quebra o build**;
- o Learning Plane pode importar contratos do Runtime Plane (direção correta);
- o Runtime Plane **não** importa o Learning Plane, com exceções nominais,
  justificadas e enumeradas uma a uma;
- o Assistant continua respondendo com o Candidate Store indisponível.

A escolha de fazer disto um teste e não um documento é a decisão central desta
ADR. Documentação descreve a intenção; teste **preserva** a intenção.

### 4. Nenhum arquivo é movido fisicamente nesta Era

Mover 40 módulos para `app/runtime/` e `app/learning/` reescreveria imports em
centenas de arquivos, arriscaria 1085 testes verdes e não melhoraria nem
boundaries nem dependências — só a aparência da árvore de diretórios. A regra
de reorganização adotada é: **mudança física só quando ela melhora fronteira,
dependência, clareza, manutenção ou teste.** Aqui, não melhora.

A pertinência a plano é declarada em dados. Se um movimento físico se
justificar em uma Era futura, a declaração já estará pronta para guiá-lo.

## Dataset Ownership

**A Dataset Foundation é responsabilidade exclusiva do Veltrix.**

Projetos externos — FinGuard, Structa, Elyra e quaisquer futuros — produzem
**fontes e evidências**. Eles não produzem dataset, não classificam
elegibilidade, não decidem propósito de treinamento e não avaliam prontidão.

O que isto significa em mecanismo, não em intenção:

- o esquema de candidato, a política de elegibilidade, o scanner de
  privacidade, o ciclo de vida e a política de readiness vivem **somente** em
  `app/modules/training_data/`;
- o Veltrix **não alcança a base de dados de nenhum consumidor**. Para
  origens submetidas de fora (hoje, `elyra_report_snapshot`), não existe e não
  deve existir adapter interno de coleta — a origem está registrada em
  `EXTERNALLY_SUBMITTED_SOURCE_TYPES` e só entra quando um consumer autorizado
  a submete explicitamente, já minimizada, sanitizada, com proveniência e
  fingerprint;
- `automatic_collection` é `Literal[False]`. Não é uma flag desligada: é um
  tipo que faz o Pydantic **rejeitar** o valor `True`. Ligar coleta automática
  exige alterar o tipo no código-fonte e passar por revisão — nunca uma
  variável de ambiente, nunca um payload;
- a matriz `_PURPOSES_BY_SOURCE` decide quais propósitos cada origem admite.
  Ampliar o alcance de uma origem é mudança de política com ADR, não mudança
  de request;
- `minimum_authorized_candidates` sem configuração explícita mantém
  `DATASET_NOT_READY` via `READINESS_VOLUME_POLICY_NOT_CONFIGURED`. Prontidão
  nunca é inferida por contagem isolada.

## Consequências

### Positivas

- A pergunta "a que plano isto pertence?" passa a ter resposta verificável em
  máquina, para todo módulo presente e futuro.
- A regressão arquitetural mais provável — alguém adicionar um import
  Runtime → Learning por conveniência — passa a falhar no CI em vez de ser
  descoberta meses depois.
- O invariante de disponibilidade do Assistant deixa de ser uma promessa e
  passa a ser um teste.
- As próximas Eras (QEC, Project Capability Manifest, Dataset Registry,
  Canonical Dataset, treinamento) ganham um alvo estrutural definido em vez de
  precisarem inventá-lo sob pressão.
- O acoplamento de projeto existente fica localizado com precisão de linha, em
  vez de disperso e desconhecido.

### Negativas e custos aceitos

- A árvore de diretórios continua plana: `app/modules/` com 40 entradas não
  *parece* dois planos. Quem procurar a fronteira nas pastas não a encontra —
  ela está em `app/architecture/planes.py`.
- Um módulo novo agora exige um passo a mais: declarar seu plano. É atrito
  deliberado.
- A lista de exceções nominais é dívida visível. Isto é intencional: uma
  exceção enumerada e comentada é auditável; uma exceção implícita não é.

### Neutras

- Zero alteração de contrato público. Os 37 paths permanecem idênticos em
  path, método, schema e código de erro.
- Zero alteração de banco, migration, constraint ou índice.
- Zero alteração de comportamento em runtime.

## Compatibilidade

**Todas as APIs públicas existentes são preservadas, byte a byte.** Não houve
mudança de contrato, portanto não houve necessidade de camada de
compatibilidade nem de caminho de migração para consumidores.

FinGuard, Structa e Elyra não precisam de nenhuma alteração. Nenhuma
credencial, matriz de autorização, task type ou capability foi tocada.

## Riscos

| Risco | Probabilidade | Mitigação |
|---|---|---|
| A lista de exceções cresce até esvaziar a regra | Média | Cada exceção exige justificativa no próprio código; a lista é curta e revisável de relance |
| A declaração de planos diverge da realidade | Baixa | O teste falha se um módulo existir sem declaração ou for declarado duas vezes |
| Fronteira lógica ser lida como permissão para acoplar mais | Baixa | Direção de dependência é testada, não recomendada |
| Acoplamento de projeto (P2) permanecer indefinidamente | **Média** | Registrado como dívida com localização exata; correção pertence à Era do Project Capability Manifest |

O último é o risco real desta ADR. `caller.project_id == "elyra"` e
`project_id == "finguard"` continuam no core genérico ao fim desta Era. A
decisão de não os corrigir agora é deliberada — a migração dos consumidores
está fora de escopo e alterá-los sem o mecanismo substituto criaria risco de
regressão sem entregar a estrutura correta.

## Alternativas rejeitadas

**Mover fisicamente para `app/runtime/` e `app/learning/`.**
Rejeitada. Reescreveria imports em centenas de arquivos e colocaria 1085
testes verdes em risco para produzir uma árvore de diretórios mais bonita. A
fronteira que importa é a de dependência, e essa se resolve por declaração e
teste. Movimento físico continua disponível para uma Era futura, já guiado
pela declaração.

**Extrair o Learning Plane para um serviço separado.**
Rejeitada, e explicitamente proibida no escopo. Introduziria rede, contrato
de transporte, autenticação entre serviços, observabilidade distribuída e um
segundo deployable — todo o custo de microsserviço para resolver um problema
que é de *direção de import*.

**Documentar a fronteira e confiar na revisão de código.**
Rejeitada. É exatamente o mecanismo que produziu os quatro drifts encontrados
na Era 1, incluindo um documento de arquitetura que descreve 8 endpoints
quando existem 37. Regra que não executa não é regra.

**Corrigir o acoplamento de projeto (P2) agora.**
Rejeitada nesta Era. Migração de FinGuard, Structa e Elyra e o Project
Capability Manifest estão explicitamente fora de escopo. Corrigir o sintoma
sem o mecanismo substituto — política por contrato/configuração — trocaria um
acoplamento conhecido e testado por um acoplamento novo e não testado.

**Remover o import Runtime → Learning eliminando a funcionalidade.**
Rejeitada. A submissão governada de candidato é capacidade real e coberta por
testes. A correção correta é tornar a dependência tardia e tolerante, não
apagar a funcionalidade.
