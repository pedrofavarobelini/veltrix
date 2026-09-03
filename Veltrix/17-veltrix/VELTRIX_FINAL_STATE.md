# Veltrix — estado final

Mapa: [[MOC_VELTRIX]].
Migração do nome: [[17-veltrix/MIGRACAO_PEDROCORE_VELTRIX]].
Plataforma: [[16-plataforma/PLATFORM_EVOLUTION_FINAL_STATE]].
Motor de risco: [[15-risk-engine/RISK_ENGINE_V2_BASELINE]].
Console: [[15-risk-engine/RISK_CONSOLE]].

**Veltrix — AI Runtime & Learning Control Plane.**

Este documento descreve o que o sistema **é**, verificado no código. Onde
existe apenas fundação, está escrito fundação.

## 1. O que o Veltrix faz

Ele fica entre um agente de IA e a execução, e responde três perguntas antes
de qualquer coisa acontecer:

```text
AI interpreta.      Policy decide.
Risk prevê.         Execution prova.
Evidence registra.  Learning governa.
```

Não executa comando, não escreve arquivo, não deleta nada. Analisa, decide,
governa e registra — e a recusa a executar é regra do Policy Engine com teste
negativo, não promessa de documentação.

## 2. Arquitetura

```text
                       VELTRIX (modular monolith)
                                │
          ┌─────────────────────┴─────────────────────┐
     RUNTIME PLANE                              LEARNING PLANE
     responder agora ──── evidência/contratos ───► aprender depois
```

Planos declarados em `app/architecture/planes.py` e verificados por teste que
lê a AST: módulo novo sem plano declarado **reprova**. Aconteceu três vezes
nesta série de frentes, e é exatamente para isso que o teste existe.

Invariantes executáveis, não princípios documentados:

```text
Operational Data != Training Candidate != Canonical Training Example
automatic_collection = false
execução nunca delegada ao core
```

As três são regras do Policy Engine com teste negativo próprio.

## 3. Camadas

| camada | o que entrega |
|---|---|
| Universal Contracts V1 | 6 contratos congelados por fingerprint |
| Risk Engine V2 | análise pré-execução, gates, contrato assinado |
| Risk Console | TUI e CLI em PT-BR sobre o mesmo core |
| Risk Intake / Auto Context | resolve contexto e propõe; nunca autoriza |
| Consumer SDK | cliente oficial tipado e neutro |
| Policy Engine | decisão transversal versionada e explicável |
| Evaluation Plane V2 | avaliação como evidência reproduzível |
| Model Registry | ciclo de vida com promoção por evidência |
| Shadow Mode | observação paralela sem efeito |
| Routing Intelligence | eliminação antes de ordenação |
| Asset Registry | prompts e configs versionados |
| Audit / Correlation | trilha por `correlation_id`, ponteiro nunca conteúdo |
| SLO / Health | `UNKNOWN` sem medição, nunca `HEALTHY` |
| Compatibility Matrix | resposta calculada, sem tabela por projeto |
| Disaster Recovery | restauração **provada**, não presumida |
| Evidence Platform | evidência verificável e durável |
| Dataset Control Plane | prontidão declarada, nunca fabricada |

## 4. Durabilidade — o que sobrevive a um restart

Auditado store a store no fechamento final, e classificado com honestidade.

### `DURABLE` — PostgreSQL

```text
persistência operacional · memória operacional · retrieval
histórico de risco (0009, 0010)
registro de modelos e transições      ┐
versões de assets governados          ├─ migration 0011
registros de avaliação                ┘
evidence records · dataset registry · outbox
```

As três últimas ganharam persistência **neste fechamento**. O motivo é
concreto: a promoção de modelo exige evidência de avaliação. Se a avaliação
some no restart, o registry passa a recusar promoções legítimas — ou alguém
promove de novo sem saber que já promoveu.

Duas invariantes foram para o **banco**, além do Pydantic:

- modelo `APPROVED`/`PROMOTED` sem `evaluation_ids` → `CHECK` recusa;
- duas versões `ACTIVE` do mesmo asset → índice único parcial recusa.

A guarda existe nos dois lugares porque um dump reconstruído entra pelo banco,
não pelo schema da aplicação.

### `EPHEMERAL_BY_DESIGN` — memória, por escolha

```text
trilha de correlação · comparações de shadow
janela de SLI · avaliações de política
```

Não é esquecimento. A trilha aponta para evidência que já é durável; uma
comparação de shadow pode ser reobservada; uma janela de SLI de antes do
restart descreveria um processo que não existe mais; e uma avaliação de
política é determinística — guardá-la seria guardar o que se recalcula.

Está declarado em `EPHEMERAL_BY_DESIGN`, com o motivo de cada uma, e há teste
que exige que o motivo seja explicativo.

## 5. Disaster Recovery — o que o ensaio real encontrou

O DR de memória provava o comparador. O ensaio contra PostgreSQL provou o
banco — e encontrou uma falha silenciosa que nenhuma comparação de dicionários
teria mostrado:

> O runner de migrations é idempotente e mantém um livro-razão. Se as tabelas
> somem mas o livro-razão sobrevive, rodar o runner de novo **não recria
> nada**. O operador vê "migrações aplicadas: 0", conclui que está tudo certo,
> e o banco continua sem as tabelas.

Falha silenciosa, no pior momento possível.

A correção virou procedimento: `disaster_recovery/postgres.py` esquece as
migrations indicadas no livro-razão e reexecuta o runner — nessa ordem, e sem
tocar nas migrations cujas tabelas nunca foram perdidas. Apagar o livro-razão
inteiro reexecutaria migrations que não precisavam, e recuperação não é hora
de descobrir a exceção.

Ciclo provado em banco descartável:

```text
backup → DROP das tabelas → rebuild_schema → reinserir → verificar
```

Divergência em **qualquer** store reprova a restauração inteira: restauração
parcial silenciosa é sistema incompleto se comportando como completo.

## 5b. Auto Context — resolver não é autorizar

Configurações Avançadas deixaram de ser obrigatórias: o prompt é resolvido em
uma proposta com origem e confiança por campo, revisada por um humano antes da
análise. Guia em [[15-risk-engine/RISK_CONSOLE]].

Duas frases governam a camada:

```text
auto context               !=  authorization
context confirmation       !=  execution approval
```

A permissão efetiva é a interseção de **pedida ∩ executor ∩ projeto ∩
política**. Pedir `git.push` não concede push; capacidade negada vira conflito
visível e não entra na requisição. Sem alvo identificado, nenhuma permissão é
proposta — ambiguidade bloqueia em vez de virar autorização ampla.

`POLICY_DERIVED` é separado de `INFERRED` porque "a regra disse" e "você disse"
não podem se confundir. Confiança é categórica: o método não sustenta
percentual, e número decorativo é pior que categoria honesta.

O caminho é inteiramente determinístico e funciona sem IA.

## 6. Identidade

`Veltrix` é o nome do produto. Os identificadores técnicos foram preservados
de propósito — contratos, tabelas, `project_id`, e os aliases legados de
comando, variável e cabeçalho. O raciocínio completo, com o que quebrou
durante o rename e como foi consertado, está em
[[17-veltrix/MIGRACAO_PEDROCORE_VELTRIX]].

## 7. Como usar

```bash
cd apps/api
uv sync

veltrix risk                    # Risk Console (TUI)
veltrix control-center          # retrato operacional
veltrix risk analyze p.txt --json
```

Códigos de saída da CLI: `0` análise concluída · `2` erro de entrada ·
`3` erro operacional · `4` gate `BLOCK`.

Persistência de plataforma (opcional, `off` por padrão):

```bash
export VELTRIX_PLATFORM_PERSISTENCE=postgresql
export VELTRIX_PLATFORM_DATABASE_URL="postgresql://..."
```

## 8. Checkpoints verificados

Checkpoint deste fechamento (30/08/2026):

```text
backend (PostgreSQL real)   1789 passed ·  8 skipped · 0 failed
backend (paridade CI)       1750 passed · 47 skipped · 0 failed
ruff                        PASS
frontend                     117 passed · typecheck PASS · build PASS
grafo documental             íntegro · zero órfãos · zero links quebrados
contract freeze              6 fingerprints V1 intactos
migrations                   0001–0011, nenhuma histórica editada
```

Depois deste fechamento vieram o Risk Console em três estados e o Project
Registry, que trouxeram a **migration aditiva 0012** e mais testes. Checkpoint
da publicação pública (03/09/2026):

```text
backend (PostgreSQL real)   2073 passed ·  8 skipped · 0 failed
backend (paridade CI)       2019 passed · 62 skipped · 0 failed
ruff · typecheck · build    PASS
frontend                     117 passed
grafo documental             íntegro
contract freeze              6 fingerprints V1 intactos
migrations                   0001–0012, nenhuma histórica editada
```

Os skips são PostgreSQL sem banco de teste e opt-ins de provider real. Nenhum
virou PASS.

## 9. Fora de escopo, e não iniciado

```text
ReplayDock · migração dos consumidores · fine-tuning · treinamento real
dataset artificial
```

> **Publicação pública: concluída em 03/09/2026.** O repositório saiu de
> privado e vive em `github.com/pedrofavarobelini/veltrix` sob Apache-2.0.
> O aceite visual final é **`HUMAN_VISUAL_ACCEPTANCE = PASS`**.
> Deixou de ser item fora de escopo — está registrado aqui porque este
> documento descreve o estado real, e o estado real mudou.

As oito evoluções futuras — MCP+A2A, Capability Leases, Proof of Execution,
Decision Replay, Counterfactual Lab, OpenTelemetry GenAI, AI-BOM, Sigstore —
seguem documentadas em [[16-plataforma/PLATFORM_EVOLUTION_FINAL_STATE]] com
problema, integração, benefício, custo e motivo do adiamento. **Nenhuma foi
implementada.**

## 10. O que este projeto ensinou

Registrado porque o valor de um sistema fechado é o que ele deixa como método.

**Medir a camada certa.** O erro mais caro da série foi provar que o *store*
era independente e declarar que o *domínio* era. A auditoria pegou. A correção
não foi mais teste — foi olhar para a função e perguntar qual objeto ela
realmente chama.

**A prova precisa poder reprovar.** Verificação por mutação em cada guarda
crítica: quebrar de propósito, ver o teste falhar, restaurar. Um teste que
passa com a guarda removida não é teste.

**Ensaiar de verdade acha o que a simulação esconde.** O DR de memória estava
correto e era insuficiente. O ensaio real encontrou a falha silenciosa do
livro-razão em cinco minutos.

**Search/replace cego cobra.** O rename atingiu docstrings que viram JSON
Schema e um literal de cabeçalho legado. Custou seis fingerprints e 373
testes. O corte por caixa — produto em maiúscula, identificador em minúscula —
foi o que tornou o resto seguro.

**Fail-closed em toda decisão que importa.** Banco indisponível não vira
memória. Regra quebrada não vira permissão. Atributo ausente não vira sim.
Indicador sem medição não vira saudável. Configuração ambígua não vira escolha.

---

## 11. Última frente funcional: UX final e Project Registry

Depois do fechamento acima, duas coisas ficaram claras no uso real.

**A tela tinha informação demais ao mesmo tempo.** Formulário, gate, dimensões,
alcance, cenários, histórico, contexto e detalhes técnicos competiam pela mesma
primeira viewport. Nenhuma delas estava errada; juntas, nenhuma era legível.

A resposta foi ordem, não remoção: três estados exclusivos — entrada, revisão,
resultado — e, no resultado, uma visão primária curta (gate → resumo → riscos →
por quê → o que fazer) com toda a evidência preservada em seis abas, uma
renderizada por vez.

**O seletor de projeto era refém do código-fonte.** A lista vinha do Capability
Manifest, então só aparecia quem tinha manifesto escrito no repositório — e um
usuário com projeto próprio não tinha como analisá-lo.

O Project Registry separou identidade de capacidade. Um projeto criado pelo
usuário é cidadão de primeira classe: aparece, é selecionado, chega ao
`RiskRequest` e é analisado. O que ele não ganha é permissão — sem manifesto,
os fatos ausentes ficam `UNKNOWN`, e a interseção executor ∩ projeto ∩ política
continua sendo a única fonte de permissão efetiva.

Detalhes em [[RISK_CONSOLE]] e [[PROJECT_REGISTRY]].

### O que esta frente acrescentou ao método

**Layout não pode mudar decisão — e isso precisa ser provado, não prometido.**
Um teste de paridade roda a mesma requisição confirmada e compara gate,
dimensões, alcance, cenários, achados e recomendações. Ele também ensinou a
comparar os campos certos: `finding_id` e `signal_ids` são gerados por análise,
e compará-los mediria a aleatoriedade do `uuid4`, não a estabilidade da
decisão.

**Seed é configuração; comportamento por nome é regra.** A diferença é fácil de
apagar sem perceber. O teste que lê o AST à procura de
`if project_id == "<nome>"` existe para que a lista de projetos iniciais nunca
vire uma lista de casos especiais.

**Uma guarda que atrapalha o usuário certo geralmente está respondendo à
pergunta errada.** Exigir manifesto para analisar parecia segurança e era
acoplamento. A guarda correta era de identidade: projeto desconhecido ou
arquivado é recusado; projeto sem manifesto é analisado com `UNKNOWN` onde não
há fato.
