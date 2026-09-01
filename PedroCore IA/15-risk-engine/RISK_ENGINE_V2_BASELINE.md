# Risk Engine V2 — Baseline Arquitetural (Stage R0)

Mapa da frente: [[MOC_ARQUITETURA]].
Contratos V1: [[10-contratos/CONTRATO_RISK_ENGINE_FOUNDATION]],
[[10-contratos/CONTRATO_PRE_EXECUTION_RISK_V1]],
[[10-contratos/CONTRATO_HISTORICAL_RISK]].
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

### P1 — Persistência do risco não é do risco  ✅ RESOLVIDO no R2

O Risk Engine não tem repositório próprio. Ele depende de `report_memory` e
`operational_memory` para persistir e recuperar histórico. Consequência prática:
com `PEDROCORE_REPORT_MEMORY_PERSISTENCE=off`, a inteligência histórica não tem
onde ler, e um `BLOCK` baseado em histórico se comporta de forma diferente
conforme uma variável que não é dele.

### P2 — Simulação é enumeração fixa, não simulação

`_simulations` devolve três cenários fixos (`success`, `partial_failure`,
`worst_case`) com severidade derivada de flags. É honesto no nome do campo
(`mode="analytical_dry_run"`), mas o nome "Scenario Simulation" sugere mais do
que o mecanismo entrega. Um V2 precisa decidir entre elevar o mecanismo ou
rebaixar o nome — manter a assimetria é o pior dos dois.

### P3 — Blast radius não tem unidade

`BlastRadius` descreve alcance de forma qualitativa. Sem métrica comparável,
duas análises não podem ser ordenadas por gravidade, e o histórico não pode
aprender "isto foi pior do que aquilo".

### P4 — Gate é calculado, mas não é intransponível por construção

Os gates existem e são testados. O que não existe é uma prova estrutural de que
um `BLOCK` não pode ser contornado por um caminho alternativo — hoje isso é
garantido por revisão, não por teste dedicado de bypass. A Era 3 já mostrou
neste projeto que "ninguém tentou ainda" e "é impossível" são coisas
diferentes.

### P5 — O Risk Engine não usa os Universal Contracts

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
R2  repositório próprio + migration aditiva     (resolve P1) ✅
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

O teste que fecha P1 é `test_risk_history_survives_report_memory_being_off`:
Report Memory desligada, persistência de risco ligada, história do risco
continua existindo e recuperável.

## 11. Estado

```text
STAGE R0        PASS — baseline verificado
STAGE R1        PASS — testes negativos de gate (19)
STAGE R2        PASS — persistência própria (P1 resolvido)
STAGE R3        PRÓXIMO — métrica de blast radius (P3)
CÓDIGO V1       contratos públicos intocados; integração aditiva
```
