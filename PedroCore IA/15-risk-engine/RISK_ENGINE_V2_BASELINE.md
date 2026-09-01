# Risk Engine V2 — Baseline e Encerramento (R0 a R5)

Mapa da frente: [[MOC_ARQUITETURA]].
Contratos V1: [[10-contratos/CONTRATO_RISK_ENGINE_FOUNDATION]],
[[10-contratos/CONTRATO_PRE_EXECUTION_RISK_V1]],
[[10-contratos/CONTRATO_HISTORICAL_RISK]].
Guia de uso do console: [[RISK_CONSOLE]].
Documentação V1: [[RISK_ENGINE_FOUNDATION]], [[PRE_EXECUTION_RISK_V1]],
[[EXECUTION_CONTRACT_RISK_GATES]], [[POST_EXECUTION_QA]],
[[HISTORICAL_RISK_INTELLIGENCE]].

## 0. Por que este documento existe, e o que ele NÃO é

A auditoria que antecedeu esta frente procurou, no workspace e na documentação,
uma especificação de Risk Engine V2. **Não existe.** Zero ocorrências de
"Risk Engine V2" em qualquer documento do vault, e nenhum plano incremental
registrado.

Isso muda a natureza da entrega. Sem especificação aprovada, escrever código de
V2 seria **inventar requisito** — e requisito inventado por quem implementa é
exatamente o que a governança deste projeto existe para impedir em outras
camadas. A primeira entrega do V2 é, portanto, esta fundação: o retrato
verificado do V1, os problemas objetivos, os invariantes que não podem cair e
os pontos de extensão.

**Nada do V1 foi alterado por esta frente.** Este documento é leitura e decisão.

## 1. Baseline V1 — o que existe, verificado no código

`apps/api/app/modules/risk_engine/` — **2.504 linhas**, 14 arquivos,
**52 testes** distribuídos em 5 suítes. Oito rotas públicas sob `/api/risk/`.

| Capability V1 | Arquivo | Estado | Decisão V2 |
|---|---|---|---|
| Análise determinística (foundation) | `service.py`, `rules.py`, `analyzers.py` | **COMPLETE** — 7 testes | **REUSE** |
| Análise pré-execução | `pre_execution_service.py` / `_schemas.py` | **COMPLETE** — 18 testes | **REUSE** |
| Blast radius | `pre_execution_service.py::_blast_radius` | **COMPLETE** | **ADAPT** |
| Scenario simulation (dry-run analítico) | `pre_execution_service.py::_simulations` | **COMPLETE** — `mode="analytical_dry_run"` | **ADAPT** |
| Execution Contract | `execution_contract_service.py` / `_schemas.py` | **COMPLETE** — 11 testes | **REUSE** |
| Assinatura HMAC-SHA256 | `execution_contract_service.py::_hmac` | **COMPLETE** — chave ≥32 chars obrigatória | **REUSE** |
| Gates | `execution_contract_schemas.py::RiskGate` | **COMPLETE** — PASS / PASS_WITH_WARNINGS / REVIEW_REQUIRED / BLOCK | **REUSE** |
| Human review / override | `execution_contract_service.py` | **COMPLETE** — `HumanReviewRecord` | **REUSE** |
| Pós-execução (QA/outcomes) | `post_execution_service.py` / `_schemas.py` | **COMPLETE** — 10 testes | **REUSE** |
| Inteligência histórica | `historical_service.py` / `_schemas.py` | **COMPLETE** — 6 testes | **ADAPT** |
| Análise híbrida / semântica | `historical_service.py` — modos `deterministic_only`, `semantic_only`, `hybrid` | **COMPLETE** | **ADAPT** |
| Benchmark histórico | `historical_service.py` | **COMPLETE** | **REUSE** |

Nenhuma capability listada no briefing está `MISSING`. **O V1 está completo em
relação ao que ele mesmo prometeu.**

### Dependências reais

```text
risk_engine → artifacts · caller_identity · contracts · operational_memory
              qa_analysis · qa_response · report_intelligence · report_memory
              retrieval

risk_engine ← app/main.py   (somente)
```

O Risk Engine **consome** memória operacional, retrieval e QA, e **não é
consumido** por nenhum outro módulo — apenas exposto por rota. Isso é
relevante para o V2: mudar seu contrato interno não quebra outros módulos,
mas mudar seu contrato HTTP quebra consumidores externos.

## 2. Problemas objetivos observados no V1

Estes são achados de leitura de código, não hipóteses de roadmap.

### P1 — Persistência do risco não é do risco  ✅ FECHADO no R2.1

O Risk Engine não tem repositório próprio. Ele depende de `report_memory` e
`operational_memory` para persistir e recuperar histórico. Consequência prática:
com `PEDROCORE_REPORT_MEMORY_PERSISTENCE=off`, a inteligência histórica não tem
onde ler, e um `BLOCK` baseado em histórico se comporta de forma diferente
conforme uma variável que não é dele.

### P2 — Simulação é enumeração fixa, não simulação  ✅ FECHADO no R5

`_simulations` devolvia seis cenários fixos, emitidos sempre — relevantes ou
não — com severidade derivada de flags. É honesto no nome do campo
(`mode="analytical_dry_run"`), mas o nome "Scenario Simulation" sugere mais do
que o mecanismo entrega. Um V2 precisa decidir entre elevar o mecanismo ou
rebaixar o nome — manter a assimetria é o pior dos dois.

### P3 — Blast radius não tem unidade  ✅ FECHADO no R3

`BlastRadius` descreve alcance de forma qualitativa. Sem métrica comparável,
duas análises não podem ser ordenadas por gravidade, e o histórico não pode
aprender "isto foi pior do que aquilo".

### P4 — Gate é calculado, mas não é intransponível por construção  ✅ FECHADO no R1

Os gates existem e são testados. O que não existe é uma prova estrutural de que
um `BLOCK` não pode ser contornado por um caminho alternativo — hoje isso é
garantido por revisão, não por teste dedicado de bypass. A Era 3 já mostrou
neste projeto que "ninguém tentou ainda" e "é impossível" são coisas
diferentes.

### P5 — O Risk Engine não usa os Universal Contracts  ✅ FECHADO no R4

Ele nasceu antes deles. Recebe `RiskRequest` próprio, enquanto QEC, Execution
Outcome e Learning Source já têm envelope, fronteira de autoridade e
congelamento de schema. Um consumidor externo que queira submeter risco hoje
usa um contrato que não passa pela verificação de autoridade.

## 3. Invariantes que o V2 não pode enfraquecer

Estes vêm do V1 e da arquitetura do Control Plane, e valem como restrição de
projeto:

- **fail-closed** — ausência, ambiguidade ou erro nunca resultam em permissão;
- **isolamento de projeto** — chave, não filtro de aplicação;
- **caller identity** — resolvida no servidor; o payload declara, a credencial
  decide;
- **contrato assinado** — HMAC-SHA256 com chave de ≥32 caracteres, obrigatória;
- **escopo e expiração** — um contrato vale para o que declarou e pelo tempo
  que declarou;
- **evidência** — decisão sem evidência registrada não é auditável;
- **gate não decorativo** — `BLOCK` precisa ser tecnicamente impossível de
  contornar pelo fluxo normal, e **nunca** por campo enviado pelo consumidor.

## 4. Contratos preservados

Os oito endpoints `/api/risk/*` são contrato público e estão em uso. Qualquer
alteração deve ser classificada antes:

| Classe | Exige |
|---|---|
| **ADDITIVE** | campo opcional com default; valor novo em enum aberto |
| **BREAKING** | campo obrigatório novo, remoção, mudança de tipo ou semântica → **v2 do endpoint**, com a v1 mantida até haver migration path |

Os contratos Universal V1 (`pedrocore-*/v1`) estão **congelados por fingerprint
de schema** em `tests/test_contract_freeze.py`. Se o V2 do Risk Engine passar a
usá-los, isso é adição de um contrato novo — não alteração dos existentes.

## 5. Pontos de extensão identificados

Onde o V2 pode crescer sem reescrever o V1:

1. **Repositório próprio de risco** (resolve P1) — seguindo o padrão já
   estabelecido: `Protocol` + InMemory + PostgreSQL + migration aditiva, com
   fail-closed quando desabilitado.
2. **Métrica de blast radius** (resolve P3) — campo aditivo, opcional,
   coexistindo com a descrição qualitativa.
3. **Envelope universal para submissão de risco** (resolve P5) — capability
   `risk_analysis` já existe no `ProjectCapabilityManifest`, e um contrato
   `pedrocore-risk-request/v1` entraria como **adição**, com o `RiskRequest`
   atual preservado.
4. **Testes de bypass de gate** (resolve P4) — não exige código novo de
   produção; exige testes negativos que hoje não existem.

## 6. Estratégia de migração proposta

Incremental, cada etapa verificável isoladamente e sem breaking change:

```text
R0  baseline verificado                         ← ESTE DOCUMENTO ✅
R1  testes negativos de gate e bypass           (sem mudar produção) ✅
R2  repositório próprio + migration aditiva     (store) ✅
R2.1 Historical Risk consome o store           (fecha P1) ✅
R3  metrica de blast radius                    (fecha P3) ✅
R4  contrato universal de risco                (fecha P5) ✅
R5  Scenario Simulation V2                     (fecha P2) ✅
R3  métrica de blast radius, campo aditivo      (resolve P3)
R4  contrato universal de risco, rota aditiva   (resolve P5)
R5  decisão sobre Scenario Simulation           (resolve P2 — elevar ou renomear)
```

**R1 é deliberadamente primeiro.** Ele não muda comportamento e aumenta a
confiança em tudo que vem depois: antes de mexer no motor de risco, é preciso
provar que o motor atual recusa o que promete recusar.

## 7. Riscos desta frente

| Risco | Mitigação |
|---|---|
| Reescrever V1 sem necessidade | matriz da §1 classifica 8 de 12 capabilities como REUSE |
| Quebrar consumidor de `/api/risk/*` | toda mudança classificada ADDITIVE/BREAKING antes |
| Enfraquecer gate ao refatorar | R1 antes de tudo: testes negativos primeiro |
| Escopo infinito | P2 e P5 são decisões, não implementações pendentes |

## 8. Rollback

Nenhuma etapa deste plano remove código. R2 a R4 são aditivos e desligáveis por
configuração; R1 é teste. O rollback de qualquer etapa é `git revert` do commit
correspondente, sem migração de dados reversa — as migrations propostas são
aditivas e não destrutivas.

## 9. O que NÃO entra no Risk Engine V2

Classificado `DEFERRED`, para não confundir roadmap com escopo:

- segundo provider real; treinamento real; fine-tuning;
- população artificial de dataset;
- Consumer SDK; Control Center; Model Registry completo;
- plataforma de SLO; Disaster Recovery amplo.

Nenhum deles é necessário para as etapas R1–R5.

## 10. Stage R2 — persistência própria (P1 resolvido)

### O que passou a existir

```text
risk_engine/
├── persistence_schemas.py    RiskAnalysisRecord · RiskOutcomeRecord · RiskHistorySlice
├── repository.py             RiskRepository (Protocol) · InMemory · PostgreSQL
└── persistence_service.py    projeção domínio → registro
migrations/0009_risk_history.sql
```

### Modelo de dados — projeção, não cópia

`PreExecutionRiskAnalysis` e `PostExecutionOutcome` são objetos ricos e carregam
o raciocínio do motor, onde texto vindo do consumidor pode estar. O que se
persiste é **o fato**: identificadores, versão de política, severidade
agregada, dimensões numéricas, códigos de motivo, desvio de escopo, gate,
status e tempo.

**A privacidade é a ausência de campo.** Não existe `request_text`, `prompt`,
`command`, `diff` ou `payload` no registro. Um campo que não existe não vaza,
não precisa ser sanitizado e não é esquecido na revisão. `reason_codes` tem
limite de tamanho por entrada, para que uma lista de códigos não vire, na
prática, um campo de texto livre.

A severidade agregada é derivada como a **pior dimensão**, não a média: uma
dimensão `CRITICAL` diluída entre cinco `INFO` viraria `LOW`, e o histórico
passaria a mentir sobre o que o motor tinha visto.

### Modos de persistência

Chave **própria**, `PEDROCORE_RISK_PERSISTENCE` — e essa independência é o
ponto da Stage:

| modo | implementação | comportamento |
|---|---|---|
| `off` (default) | nenhuma | desabilitado; `require_*` levanta |
| `memory` | `InMemoryRiskRepository` | efêmero por escolha explícita |
| `postgresql` | `PostgreSQLRiskRepository` | exige `PEDROCORE_RISK_DATABASE_URL` |

**Sem fallback silencioso.** URL ausente levanta; banco indisponível levanta. Um
histórico que silenciosamente vira efêmero faria um `BLOCK` baseado em
histórico mudar de comportamento sem ninguém perceber — e a decisão de risco é
exatamente onde isso não pode acontecer.

A URL é própria e **não** reaproveita a de outro domínio: reusá-la em silêncio
recriaria o acoplamento que a Stage desfez, num lugar mais difícil de ver.

### Isolamento de projeto

`get(project_id, record_id)` — o projeto está na **chave**, não em um `if`
posterior. O desenho alternativo já teria carregado o dado do outro projeto
antes de decidir, e bastaria esquecer o `if` uma vez. No PostgreSQL isso é
`PRIMARY KEY (project_id, analysis_id)`.

O mesmo id em dois projetos são dois registros distintos, não colisão.

### Idempotência e conflito

| Situação | Resultado |
|---|---|
| mesmo id, mesmo fingerprint | `False` — replay reconhecido, no-op |
| mesmo id, fingerprint diferente | `RiskRecordConflictError` |

Replay idêntico é ruído esperado; mesmo id com conteúdo diferente é sinal de
bug ou adulteração. Sobrescrever apagaria o registro original sem que ninguém
soubesse, então são tratados de forma oposta.

### Relação com Report Memory e Operational Memory

```text
POST EXECUTION
    ├── Risk Repository      fonte de verdade do domínio Risk
    ├── Report Memory        projeção operacional/relatório
    └── Operational Memory   padrão operacional aprendido
```

Nada foi removido. As integrações existentes continuam recebendo o que sempre
receberam; elas deixam de ser a **única** origem. As responsabilidades não
foram fundidas — `execution_outcome_report`, `qa` e `operational_memory` ficam
fora do registro de risco justamente porque já têm dono, e duplicá-los criaria
duas versões da mesma verdade.

### Modos de falha

| Situação | Comportamento |
|---|---|
| persistência `off` | não grava, não levanta; igual ao anterior à Stage |
| modo inválido | `RiskRepositoryConfigurationError` |
| `postgresql` sem URL | `RiskRepositoryConfigurationError` |
| banco indisponível | `RiskRepositoryError` — nunca memória |
| falha ao gravar durante análise | **a análise continua**; registrar é efeito colateral, e um motor que para de analisar porque o banco caiu seria pior que um motor sem histórico |

### Rollback

Migration `0009` é aditiva e não destrutiva; duas tabelas novas, nenhuma
alteração em `0001`–`0008`. Com `PEDROCORE_RISK_PERSISTENCE=off` — o default —
o comportamento é idêntico ao anterior à Stage. Rollback de código é
`git revert` do commit, sem migração reversa de dados.

### Verificação

```text
25 testes em memória · 5 opt-in PostgreSQL (skip sem banco de teste)
mutação: ignorar project_id       → 1 teste reprovou
mutação: fallback para memória    → 2 testes reprovaram
OpenAPI                            39 paths, 163 schemas — idêntico
contract freeze                    intacto
```

O teste `test_risk_history_survives_report_memory_being_off` prova que o
**store** é independente. Isso não era suficiente — ver §12.

## 12. Stage R2.1 — Historical Risk conectado ao store (P1 realmente fechado)

### A lacuna que a auditoria encontrou

O R2 criou o repositório e provou que **ele** funciona com Report Memory
desligada. Mas o `HistoricalRiskService` continuava reconstruindo
`risk_policy_version` — um fato do domínio Risk — lendo metadata de Report
Memory:

```python
report = report_memory_service.get_report(project_id, evidence.source_id)
policy = report.metadata.get("risk_policy_version")
```

Com Report Memory desligada, a política simplesmente não era resolvida.
**O gate do R2 mediu a camada errada:** provou independência do store e
declarou independência do domínio. As duas coisas não são a mesma.

Registro honesto do que aconteceu:

```text
R2    criou o store próprio                    correto, mas parcial
R2.1  conectou o serviço histórico ao store    P1 fechado ponta a ponta
```

### A correlação usada

Verificada no fluxo pós-execução, não suposta — `report_id=outcome_id` em
`post_execution_service.py:200` e `source_id=report.report_id` em `:260`:

```text
evidence.source_id == report_id == outcome_id
    → RiskOutcomeRecord.risk_analysis_id
    → RiskAnalysisRecord.analysis_policy_version
```

### Precedência de resolução

| Situação | Fonte |
|---|---|
| persistência `off` | Report Memory — caminho V1 **intocado** |
| ligada, registro existe | **domínio Risk** |
| ligada, registro ausente | Report Memory — **legado**, dado anterior ao R2 |
| ligada, repositório indisponível | **levanta** — nunca cai para o legado |

O fallback legado existe porque registros gravados antes do R2 não estão no
store próprio, e apagá-los do caminho de leitura seria perder história real. A
origem de cada resolução é marcada internamente (`POLICY_SOURCE_RISK_DOMAIN` /
`POLICY_SOURCE_LEGACY_REPORT`) sem tocar no schema público.

**Falha de repositório configurado não vira fallback.** Devolver "sem
histórico" faria a consulta parecer segura quando ela apenas não conseguiu ler
— e é sobre esse número que uma decisão de risco se apoia.

### API

`RiskRepositoryError` passou a ser convertido em erro operacional sanitizado,
com código próprio `RISK_HISTORY_PERSISTENCE_UNAVAILABLE` — distinto do de
Operational Memory, porque são dois stores e colapsá-los esconderia qual caiu.
Nenhum detalhe de banco atravessa a fronteira da API.

### Verificação

```text
9 testes novos  serviço usa o domínio Risk · Report Memory não é consultada
                quando o domínio responde · V1 intocado com persistência off
                · legado resolve · nada é inventado · fail-closed · sem
                vazamento de internals · endpoint sanitizado · código distinto

mutação  ignorar o Risk Repository        → 4 testes reprovaram
         falha do repo vira fallback      → 2 testes reprovaram
```

## 14. Stage R3 — métrica de blast radius (P3 fechado)

`BlastRadius` descrevia alcance qualitativamente. Sem número comparável, duas
análises não podiam ser ordenadas e o histórico não aprendia "isto atingiu mais
do que aquilo".

`BlastRadiusMetric` mede **alcance, não perigo**:

| campo | o que é |
|---|---|
| `boundary_breadth` | quantas das 8 fronteiras foram tocadas |
| `item_extent` | quantos itens distintos, somados |
| `boundary_counts` | a conta aberta, conferível item a item |
| `metric_version` | permite evoluir sem reinterpretar números antigos |

**Sem pesos arbitrários.** Não há "banco vale 3, arquivo vale 1" — pesar
fronteiras exigiria uma teoria sobre qual é pior, e essa teoria seria inventada
aqui. Quem quiser ponderar faz depois, com política própria, e a métrica crua
continua disponível para conferir.

**Separada da severidade, por construção.** Alterar 40 arquivos de teste tem
alcance maior e perigo menor que alterar um arquivo de credencial. Um número
que misturasse as duas não responderia nenhuma das duas perguntas. `magnitude`
foi preservada e coexiste. A métrica **não entra no cálculo do gate**.

Propriedades garantidas por teste: determinística, invariante a ordem,
invariante a duplicata, monotônica em itens e em fronteiras, e com o agregado
sempre decorrendo do detalhe.

**Persistência aditiva.** Migration `0010` acrescenta quatro colunas
*nullable* a `pedrocore_risk_analyses`; a `0009` não foi tocada. Registro
gravado antes do R3 fica com métrica `NULL` — forçar um número neles inventaria
um alcance que ninguém mediu. Uma `CHECK` garante que as colunas são
consistentes entre si ou todas ausentes.

**A métrica ficou fora do fingerprint de propósito.** Ela é derivada de dados
já presentes na análise, então não acrescenta identidade — e incluí-la faria a
mesma análise, reprojetada após o R3, colidir com o registro gravado antes
dele. Continuidade vale mais que simetria.

## 15. Stage R4 — contrato universal de risco (P5 fechado)

O Risk Engine nasceu antes dos Universal Contracts: recebia submissão por um
caminho que não passava pela fronteira de autoridade.

`pedrocore-risk-request/v1` fecha isso. O consumidor declara **fato** —
operação, alvos, ambiente, permissões, contexto — e **não** declara veredito.
`gate`, `safe`, `approved`, `risk_level`, `risk_severity`, `override`, `bypass`
e `force` entraram no vocabulário reservado da fronteira de autoridade, e um
payload que os traga é recusado inteiro, em qualquer profundidade.

### Por que contrato próprio e não payload do envelope

A opção natural seria acrescentar `risk_request` a `IntegrationPayloadType`.
Isso mudaria o JSON Schema de `PedroCoreIntegrationEnvelopeV1` e, com ele, um
fingerprint congelado.

A política trata "valor novo em enum" como aditivo que *pode* atualizar o
fingerprint com justificativa. Mas o envelope é o contrato mais central dos
cinco, e alterá-lo para acomodar um domínio ainda em evolução trocaria
estabilidade permanente por conveniência temporária.

**Os cinco fingerprints V1 ficam byte a byte intactos.** O contrato novo nasce
congelado, e reutiliza a mesma maquinaria — registro de versões, fronteira de
autoridade, vínculo de identidade, verificação de capability. É um contrato
universal a mais, não um caminho paralelo com regras próprias.

`to_risk_request_payload()` adapta para o `RiskRequest` V1 que o motor já
entende, com `producer` e `project_id` vindos da credencial autenticada. **O
motor não mudou:** o contrato novo é uma porta nova para a mesma sala.

## 16. Stage R5 — Scenario Simulation V2 (P2 fechado)

Antes: seis cenários fixos, emitidos sempre, relevantes ou não. Cenário
irrelevante emitido para completar lista treina quem lê a ignorar a lista
inteira.

Agora os seis base continuam (valem para qualquer operação mutante) e os
condicionais aparecem **só quando o fato correspondente existe**:

| cenário | condição |
|---|---|
| `data_corruption` | operação destrutiva ou alteração de schema |
| `migration_failure` | migração declarada |
| `test_failure` | testes exigidos declarados |
| `external_service_failure` | integração externa declarada |

Cada cenário passou a explicar **como agir**, não só quão grave é:
`preconditions`, `affected_scope`, `containment`, `rollback_requirement`,
`verification`, `residual_risk` e `confidence`.

`residual_risk` é separado de `severity` porque o que sobra depois da contenção
não é o impacto bruto. `confidence` é explícito porque cenário derivado de
regra determinística vale mais que cenário derivado de heurística, e
apresentá-los com o mesmo peso esconderia a diferença.

**Nada executa.** `mode` continua `analytical_dry_run` e
`target_operation_executed` continua `False`. Nenhum provider é chamado — o
caminho determinístico é suficiente, e IA pode ajudar na interpretação em uma
Era futura sem virar dependência.

## 17. Auditoria final do motor

### Gates

`PASS` · `PASS_WITH_WARNINGS` · `REVIEW_REQUIRED` · `BLOCK`, com
`reason_codes` sempre presentes — decisão sem motivo não é auditável.

**Severidade de risco ≠ gate de execução.** A severidade descreve o que se
observou; o gate decide o que pode acontecer. `BLOCK` vem de escopo proibido,
permissão ausente, operação desconhecida ou segredo em produção — nunca de um
campo enviado pelo consumidor, e nunca da métrica de alcance.

### Execution Contract

Assinatura HMAC-SHA256 com chave obrigatória de ≥32 caracteres; vínculo de
projeto, ambiente, agente, escopo permitido e proibido; expiração. Testado
contra adulteração de gate, ampliação de escopo pós-assinatura, expiração,
reuso para outra operação, travessia de projeto, chave ausente, chave fraca e
chave trocada.

**Revisão humana decide sobre risco, não conserta integridade.** Um revisor
legítimo que aprove contrato adulterado recebe `BLOCK` com
`INVALID_CONTRACT_CANNOT_BE_OVERRIDDEN` — aceitar transformaria a revisão no
bypass que a assinatura existia para impedir. O gate original nunca é apagado.

### Pós-execução e histórico

`predicted` × `observed` fica no repositório próprio do Risk. Report Memory e
Operational Memory continuam recebendo o que sempre receberam. **O Risk Engine
não cria Training Candidate** — promoção pertence ao Learning Plane.

## 18. Roadmap aprovado — NÃO implementado nesta frente

Registrado para que fique claro o que existe e o que não existe:

```text
Consumer SDK · Policy Engine · Control Center · Evaluation Plane V2
Model Registry / Promotion · Shadow Mode
Quality/Cost/Latency Routing · Prompt Registry
Unified Audit Trail / Correlation · SLO / Operational Health
Compatibility Matrix · Disaster Recovery
```

### Possible Future Evolutions — apenas estudo

```text
MCP + A2A Gateway · Just-in-Time Capability Leases
Proof of Execution · Decision Replay / Time Travel
Counterfactual Risk Lab · OpenTelemetry GenAI
```

Tecnologias relacionadas a acompanhar: CycloneDX/AI-BOM, Sigstore/in-toto.

**Nada disso foi implementado.** Nenhum código desta frente os antecipa.

## 19. Próximo encerramento — rename

```text
NEXT MAJOR CLOSEOUT: product rename to Veltrix
```

Não executado aqui. A nomenclatura técnica atual (`PEDROCORE_*`,
`pedrocore_*`) foi **preservada** deliberadamente, inclusive nos contratos e
identificadores criados nesta frente — introduzir `VELTRIX_*` isolado agora
criaria duas convenções convivendo sem estratégia.

O rename precisará mapear, sem busca-e-troca cega: branding, UI, README e
docs, repositório, pacotes, variáveis de ambiente, identificadores de contrato,
identificadores de banco e compatibilidade com o legado. Identificador de
contrato e nome de coluna são especialmente delicados: trocá-los quebra
consumidor e exige migration com alias.

## 20. Estado final

```text
STAGE R0     PASS — baseline verificado
STAGE R1     PASS — testes negativos de gate (19)
STAGE R2     PASS — persistência própria (store)
STAGE R2.1   PASS — Historical Risk conectado ao store
STAGE R3     PASS — métrica de blast radius (18 testes)
STAGE R4     PASS — contrato universal de risco (26 testes com R5)
STAGE R5     PASS — Scenario Simulation V2

P1 CLOSED · P2 CLOSED · P3 CLOSED · P4 CLOSED · P5 CLOSED

migrations   0009 (R2) · 0010 (R3), ambas aditivas
contratos    5 fingerprints V1 intactos + 1 novo congelado
OpenAPI      39 paths · 2 schemas estendidos, só campos opcionais
```

## 21. Fechamento de produto — console, CLI e porta HTTP

O motor estava fechado (R0–R5) e mesmo assim não era usável por um humano:
para analisar um prompt era preciso subir `uvicorn`, montar um JSON e falar
HTTP. Esta etapa fecha essa distância, sem tocar no motor.

### Risk Console

TUI em Textual, no mesmo processo do core — guia completo em [[RISK_CONSOLE]].

Textual foi escolhido sobre as alternativas por motivos concretos: Electron
traria um runtime inteiro para desenhar painéis de texto; uma segunda SPA React
duplicaria um front que já existe e está congelado; um servidor web separado
acrescentaria porta, credencial e um modo de falha novo entre o usuário e uma
análise que roda em milissegundos.

O console **não decide**. Não há nele nenhuma regra que produza gate,
severidade ou aprovação:

```text
Console -> Risk Service -> Policy/Gate -> resultado -> Console
```

Em `BLOCK`, `EMITIR CONTRATO` e `COPIAR PROMPT APROVADO` ficam indisponíveis —
e a recusa está no **serviço**, não no botão. Provado por mutação: removida a
guarda em `issue_contract`, o teste correspondente reprova.

O vínculo prompt↔análise usa a mesma assinatura que sela o contrato,
normalizada quanto ao `request_id`. Editar qualquer campo invalida a aprovação
anterior até uma nova análise.

### CLI

`argparse`, da biblioteca padrão. `click` até já estava instalado, de carona no
uvicorn — mas depender de dependência transitiva é depender de um acidente.

`BLOCK` tem código de saída próprio (`4`) para que um pipeline reaja a
"bloqueado" sem interpretar texto.

Um defeito real foi encontrado e corrigido aqui: `--json` redirecionado saía no
codepage do console (cp1252 no Windows) e produzia bytes que não eram UTF-8
válidos. A saída passou a ser forçada para UTF-8.

### R4 — porta operacional

`POST /api/risk/universal/analyze` fecha a dívida registrada no fechamento
anterior: o contrato universal existia validado e testado, mas sem rota — uma
promessa que só valia dentro da suíte.

O `contract` viaja como objeto **cru** de propósito. Tipado, o `extra="forbid"`
recusaria um campo `gate` como erro de FORMA, e o integrador corrigiria o tipo
sem descobrir que o problema era ter tentado decidir o próprio veredito.

Autoridade e capability respondem `403`; versão e forma respondem `422`.
Misturar os dois faria alguém procurar erro de digitação onde havia falta de
permissão.

### Fronteiras respeitadas

A UI React principal **não foi alterada**. O motor **não mudou**. O rename
global continua fora desta frente — a marca ficou centralizada em
`app/modules/risk_console/branding.py`.

`risk_console` foi declarado no **Runtime Plane**, e não como Consumer
Capability: ele não pertence a nenhum consumidor, atende qualquer projeto que
declare `risk_analysis`. O teste de fronteira arquitetural pegou o módulo novo
sem plano declarado — que é exatamente para isso que ele existe.
