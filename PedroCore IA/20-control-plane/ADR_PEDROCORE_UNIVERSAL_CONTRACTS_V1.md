# ADR — PedroCore Universal Contracts V1

- **Identificador:** `ADR-PEDROCORE-UNIVERSAL-CONTRACTS-01`
- **Data:** 29/08/2026
- **Status:** Aceita
- **Escopo:** Era 3 (contratos universais de integração)
- **Decisão anterior:** [[ADR_PEDROCORE_AI_RUNTIME_LEARNING_CONTROL_PLANE]]
- **Evidência de base:** [[PEDROCORE_CURRENT_ARCHITECTURE_BASELINE]]
- **Referência de contratos:** [[PEDROCORE_UNIVERSAL_CONTRACTS_REFERENCE]]

## Contexto

A Era 2 separou Runtime Plane e Learning Plane e tornou a fronteira executável.
O que ficou de fora foi a outra fronteira: a que separa **o PedroCore dos seus
consumidores**.

Hoje cada consumidor entra por um contrato próprio. `elyra-textual/v1`,
`elyra-multimodal/v1`, `elyra-learning/v1` — todos bons, todos fail-closed, e
todos específicos. O quarto consumidor exigiria um quarto conjunto, e o núcleo
genérico continuaria aprendendo nomes.

E o núcleo já aprendia nomes. A auditoria desta Era encontrou **quatro** pontos
de acoplamento no core genérico, dois a mais do que a Era 1 havia reportado.

## Problema

**O core decide por nome.** `caller.project_id == "elyra"` na orquestração,
`project_id == "finguard"` no prompt builder, e — descobertos agora —
`"finguard" in path` no leitor de artefatos e `"finguard" in url` no adaptador
Playwright. Habilitar um comportamento para um consumidor novo exige editar o
motor, incluindo um arquivo de 2.900 linhas no coração do Runtime Plane.

**Não existe vocabulário comum de integração.** Cada contrato reinventa quem
produziu, para qual projeto, sob qual correlação. Três contratos divergem em
três direções, e a divergência só aparece quando alguém tenta correlacioná-los.

**Não existe fronteira de autoridade declarada.** Nada, hoje, impede
estruturalmente que um payload futuro traga `eligibility: eligible` ou
`authorized: true`. Os contratos específicos protegem seus próprios campos, mas
a proteção é caso a caso — e um contrato novo nasce desprotegido por padrão.

Este último é o risco sério. Se um payload puder decidir elegibilidade,
qualquer integrador com credencial passa a ser dono da governança de
aprendizado do PedroCore, e o Learning Plane inteiro vale o que vale a boa-fé
do integrador mais fraco.

## Decisão

### 1. Cinco contratos universais V1

| Contrato | Versão | Papel |
|---|---|---|
| Project Capability Manifest | `pedrocore-capability-manifest/v1` | o que o consumidor declara saber fazer |
| Quality Evidence (QEC) | `pedrocore-quality-evidence/v1` | fato observável de QA |
| Execution Outcome | `pedrocore-execution-outcome/v1` | resultado de execução |
| Learning Source | `pedrocore-learning-source/v1` | fonte operacional candidata |
| Integration Envelope | `pedrocore-integration/v1` | envelope comum dos três acima |

Nenhum depende semanticamente de FinGuard, Structa, Elyra, RIVVO ou de qualquer
consumidor. O teste de migração falha se algum voltar a depender.

### 2. O envelope é comum porque a duplicação seria real

Os três contratos de evento respondem às mesmas perguntas antes de qualquer
coisa específica: quem produziu, para qual projeto, sob qual correlação, com
qual identidade de evento. O envelope existe para que essas respostas não
divirjam entre contratos — não por simetria.

O padrão não foi inventado: `IntelligenceReportEnvelopeV2` já resolveu
exatamente este problema no próprio repositório, com o mesmo desenho de payload
selecionado estritamente pelo tipo declarado. A Era 3 reaplica o padrão
comprovado e **não toca** naquele envelope, que continua público e intacto.

Não é um god object: o envelope carrega identidade e correlação e delega todo o
significado ao payload. Ele não sabe o que é uma suíte de teste.

### 3. Fronteira de autoridade estrutural

`authority.py` mantém a lista de nomes que representam **julgamento do
servidor**: elegibilidade, autorização, classificação final de privacidade,
identidade e ciclo de vida de Training Candidate, prontidão, pertinência a
dataset, score autoritativo e o próprio interruptor de coleta automática.

A varredura é **recursiva** — esconder `eligibility` em
`metadata.extra.nested` não pode ser mais eficaz do que enviá-lo no topo — e
**normalizada**, porque `trainingCandidate`, `training_candidate` e
`training-candidate` são a mesma tentativa.

A defesa é **recusar a requisição inteira**, não ignorar o campo. Campo
ignorado em silêncio ensina o integrador que ele funciona, e a próxima versão
dele passa a depender disso.

Fato do produtor continua bem-vindo, com outro vocabulário: `observed_*`,
`reported_*`, `producer_asserted_*`. O contrato aceita a observação e recusa a
sentença.

### 4. A ordem da validação é parte da decisão

```text
1. versão do envelope
2. fronteira de autoridade      ← antes da forma, deliberadamente
3. forma do payload (Pydantic)
4. vínculo de identidade
5. capability declarada
```

A autoridade vem **antes** da forma porque um payload que tenta decidir
elegibilidade deve ser recusado *por tentar*, e não por estar malformado. Se a
forma viesse primeiro, um payload que erra um tipo E tenta escalar autoridade
seria reportado apenas como erro de tipo — e o integrador corrigiria o tipo sem
nunca saber que a escalada era o problema real.

### 5. Nome de projeto vive no registro, nunca no motor

A regra não é "nome de projeto é proibido" — seria impossível, o PedroCore
precisa saber quem são seus consumidores. A regra é **onde** o nome pode
aparecer.

`project_context/manifests.py` é o registro: uma tabela de dados onde adicionar
um consumidor é adicionar uma linha. O motor pergunta `manifest.has_trait(...)`
e `manifest.declares(...)` e nunca sabe com quem está falando.

Diferença prática: habilitar deduplicação idempotente para um consumidor novo
exigia editar `orchestration/service.py`; agora exige um trait a mais em uma
linha da tabela.

### 6. Contratos, não rotas

A Era 3 entrega os contratos e a validação executável. Ela **não** expõe
endpoint novo: o OpenAPI permanece byte a byte idêntico ao da Era 2. Wire-up de
ingestão pertence à Era 4 — Evidence Platform. Entregar rota antes de contrato
seria inverter exatamente o princípio desta Era.

## Dataset Ownership — reafirmado

O Learning Source Contract é a decisão mais delicada da Era, e a sua garantia é
uma ausência: não existem os campos `eligibility`, `authorized`, `candidate_id`,
`lifecycle`, `training_purpose`, `quality_score` nem `readiness`. Um teste
verifica essa ausência, para que acrescentá-los exija uma conversa antes do
merge — e não uma descoberta depois de um dataset.

Submeter uma fonte **não** concede elegibilidade, autorização, status de
candidato, pertinência a dataset, prontidão nem status canônico. Toda promoção
continua no Learning Plane, que reavalia por conta própria a cada candidato.
Uma fonte aceita hoje pode ser recusada amanhã porque a política mudou — e isso
é correto.

`derived_content_only` é `Literal[True]`: um tipo que faz o Pydantic recusar
`False` antes de qualquer regra de negócio. Conteúdo bruto — transcrição,
diário, mídia, log integral — não entra por este contrato em circunstância
alguma.

`automatic_collection` permanece `Literal[False]` no Learning Plane, intocado.

## Consequências

### Positivas

- Um consumidor novo integra por declaração, sem editar o motor.
- A escalada de autoridade passou de "ninguém tentou ainda" a "recusada e
  testada em seis cenários distintos".
- `finguard-local` passou a receber a regra de segurança que a comparação por
  igualdade nunca lhe entregou — um bug latente corrigido pelo modelo novo.
- A denylist de recursos protegidos ficou declarativa e agregada: um consumidor
  novo com recurso próprio protege-o por registro, não por `if`.
- As mensagens de bloqueio deixaram de nomear consumidores, o que evitava
  revelar a terceiros quais sistemas o PedroCore conhece.

### Negativas e custos aceitos

- Mais um módulo (`universal_contracts`, 7 arquivos) e mais uma tabela para
  manter em sincronia com `project_context._PROJECTS`. As duas descrevem o
  mesmo consumidor por ângulos diferentes; unificá-las é trabalho de Era futura.
- A lista de nomes reservados é heurística por vocabulário. Ela pega as
  tentativas óbvias e as variações de grafia; não pega um campo deliberadamente
  camuflado com nome inocente. A defesa contra isso é `extra="forbid"`, que já
  recusa qualquer campo não declarado.
- Contratos sem endpoint são valor diferido: eles só rendem quando a Era 4 os
  conectar.

### Mudança intencional de comportamento

Uma, listada campo a campo em [[PEDROCORE_UNIVERSAL_CONTRACTS_REFERENCE]]: a
regra de segurança "projeto externo e somente leitura" passou a ser aplicada a
**todo** consumidor com o trait `EXTERNALLY_OWNED`, e não apenas ao FinGuard.
O texto entregue ao FinGuard é idêntico ao anterior; `finguard-local`, `structa`
e `elyra` passam a recebê-lo. É correção de modelo, não expansão de escopo — os
quatro sempre foram externos e read-only.

## Compatibilidade

**OpenAPI idêntico byte a byte** (37 paths, 156 schemas). Zero breaking change.
Nenhuma rota, schema público, migration, constraint ou índice foi alterado.
Nenhum consumidor precisa mudar coisa alguma.

Contratos existentes (`elyra-textual/v1`, `elyra-multimodal/v1`,
`elyra-learning/v1`) permanecem intactos e continuam sendo o caminho em
produção. Os universais coexistem; a migração dos específicos para os
universais é decisão de Era futura, com migration path próprio.

## Riscos

| Risco | Probabilidade | Mitigação |
|---|---|---|
| Registro de manifests divergir de `_PROJECTS` | **Média** | teste de consistência interna; unificação em Era futura |
| Campo de autoridade camuflado com nome inocente | Baixa | `extra="forbid"` recusa campo não declarado |
| Contratos ficarem sem uso se a Era 4 atrasar | Média | são pequenos e testados; o custo de espera é baixo |
| `EXTERNALLY_OWNED` alterar prompts de forma indesejada | Baixa | verificado projeto a projeto; texto do FinGuard inalterado |

## Alternativas rejeitadas

**Um contrato por consumidor, como hoje.**
Rejeitada. É o que produziu quatro pontos de acoplamento no core e três
contratos que divergem no mesmo vocabulário. Não escala e já não escalou.

**Deixar o consumidor enviar `TrainingExampleCandidate` pronto.**
Rejeitada, e é a rejeição central da Era. Seria simples e transferiria a
governança de aprendizado para quem integra.

**Aceitar `quality_score` do produtor.**
Rejeitada. O número passaria a valer a boa-fé de quem o enviou, e duas suítes
muito diferentes produziriam o mesmo 100. QEC transporta fatos; o julgamento é
derivado pelo PedroCore, que pode mudar de opinião sem pedir nada ao produtor.

**Ignorar campos reservados em silêncio.**
Rejeitada. Ensina o integrador que o campo funciona.

**Migrar os contratos específicos da Elyra para os universais agora.**
Rejeitada nesta Era. Eles estão em produção e testados; migrá-los exige
migration path próprio e pertence a uma Era com esse objetivo.

**Expor endpoints de ingestão junto com os contratos.**
Rejeitada. É Era 4. Entregar rota antes de contrato inverteria o princípio
desta Era.
