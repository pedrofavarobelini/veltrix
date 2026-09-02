# Platform Evolution — estado final das 12 evoluções

Mapa da frente: [[MOC_ARQUITETURA]].
Motor de risco: [[15-risk-engine/RISK_ENGINE_V2_BASELINE]].
Console: [[15-risk-engine/RISK_CONSOLE]].
Status canônico: [[09_STATUS_ATUAL]].

Este documento registra o que as 12 evoluções **realmente são hoje**, no
código. Onde existe apenas fundação, está escrito fundação — não
`IMPLEMENTED`.

## 0. Como ler esta página

Cada evolução traz a classificação de auditoria que a originou:

| classificação | significado |
|---|---|
| `KEEP` | já existia e continua como estava |
| `EXTEND` | existia e ganhou camada nova por cima |
| `BUILD` | não existia; foi construído nesta frente |

Nenhum subsistema existente foi duplicado. Onde a fundação já respondia bem,
ela foi mantida e consultada, não reescrita.

## 1. As invariantes que nenhuma evolução pode quebrar

```text
Operational Data  !=  Training Candidate  !=  Canonical Training Example
automatic_collection = false

AI interpreta.     Policy decide.
Risk prevê.        Execution prova.
Evidence registra. Learning governa.
```

As três primeiras viraram **regras executáveis** no Policy Engine
(`learning.automatic_collection`, `learning.explicit_consent`,
`execution.never_delegated`) e têm testes negativos próprios. Deixaram de ser
princípios documentados para virar código que recusa.

## 2. E1 — Consumer SDK · `BUILD`

`app/modules/consumer_sdk/`

Cliente oficial, fino e tipado, sobre os contratos que já existiam. Ele
**não** inventa protocolo e **não** decide nada.

Decisões que valem registro:

- **Configuração explícita.** O SDK nunca lê `os.environ`. Ler o ambiente por
  conta própria faria o cliente se comportar diferente em duas máquinas sem o
  código mudar — e isso se descobre em produção.
- **Retry só onde repetir pode dar certo.** Transporte e 5xx; nunca 4xx. Um
  4xx repetido não vira sucesso, vira o mesmo erro três vezes.
- **Idempotência derivada do conteúdo.** A chave é hash do payload canônico,
  não um UUID: um retry precisa levar a *mesma* chave, senão o servidor vê
  dois pedidos diferentes.
- **Erro sanitizado.** Corpo bruto de resposta nunca é propagado — é onde
  string de conexão costuma aparecer, e o consumidor tipicamente loga a
  exceção inteira.
- **Transporte injetável**, o que permite testar o SDK inteiro sem rede e sem
  dublê de biblioteca.

Não migrou consumidor algum. FinGuard, Structa, Elyra, RIVVO e OrlaByte
seguem como estavam — a migração é frente própria.

## 3. E2 — Policy Engine · `EXTEND`

`app/modules/policy_engine/`

`policy_enforcement` continua onde estava. O que nasceu é a camada de decisão
**transversal**, com vocabulário comum: `policy_id`, `policy_version`,
`decision`, `reason_codes`.

- **Não virou rules engine universal.** O gate do Risk e o circuito de
  provider continuam nos seus domínios: mudar de casa não os tornaria mais
  corretos e os tiraria de onde são testados a fundo.
- **O efeito mais restritivo sempre vence**, e a ordem das regras não altera a
  decisão. Política que dependesse da ordem seria política por sorteio.
- **Regra que explode vira `REVIEW_REQUIRED`**, nunca permissão.
- **Nenhuma regra cita projeto por nome** — verificado por teste que analisa a
  AST, ignorando docstrings.

## 4. E3 — Control Center · `BUILD`

`app/modules/control_center/` · `GET /api/control-center/snapshot` ·
`pedrocore control-center`

Agregação **somente leitura** do que cada camada já sabe: projetos e
capabilities, saúde, registries, risco, outbox, avaliações e shadow.

- **Nenhuma operação mutável.** Não há botão que apague, promova ou
  reprocesse — um painel que mutasse estado precisaria de uma superfície de
  autorização própria, que seria uma segunda porta para decisões que já têm
  porta.
- **A agregação vive no servidor.** Se o front juntasse dez chamadas, a regra
  de "o que conta como saudável" acabaria escrita em TypeScript, longe dos
  testes.
- **A chave de assinatura é reportada como presença, nunca como valor.**
- **A UI React não foi tocada.** A visualização é a rota mais o subcomando de
  terminal, coerente com o Risk Console.

## 5. E4 — Evaluation Plane V2 · `EXTEND`

`app/modules/evaluation_plane/`

`evaluation` e `eval_harness` continuam. A camada nova registra a avaliação
como **evidência reproduzível**: sujeito, suite, dataset, ambiente, métricas
com tamanho de amostra, e ponteiros de evidência.

- **`DATASET_NOT_READY` continua válido**, e métricas enviadas sem dataset são
  **descartadas** — aceitar número sobre dataset inexistente é a forma mais
  silenciosa de fabricar evidência.
- **A camada não promove nada.** `promotes_subject` é `Literal[False]` no
  próprio registro, e o serviço não expõe `promote`.
- **`sample_size` viaja junto de cada métrica**: média sobre três casos e
  sobre trezentos não valem o mesmo.

## 6. E5 — Model Registry + Promotion · `BUILD`

`app/modules/model_registry/`

Ciclo de vida explícito: `REGISTERED → CANDIDATE → EVALUATING → APPROVED →
PROMOTED`, com `REJECTED`, `ROLLED_BACK` e `DEPRECATED`.

- **Não existe caminho direto para produção.** A tabela de transições é
  declarada, e um grafo implícito é onde o atalho se esconde.
- **Promoção exige `evaluation_id`.** A guarda vive no serviço *e* no schema,
  porque um registro reconstruído de um dump também precisa passar por ela.
- **Rollback é de primeira classe.** Um registro que só soubesse avançar
  obrigaria a acertar de primeira.

## 7. E6 — Shadow Mode · `BUILD`

`app/modules/shadow_execution/`

`shadow_routing` responde "quem eu escolheria". Isso é decisão de roteamento,
não shadow. O que nasceu é a observação paralela do candidato.

As cinco garantias, cada uma obtida por construção:

| garantia | como |
|---|---|
| não responde ao usuário | resultado sai por outro campo, depois da resposta oficial |
| não executa ação externa | candidato que **declara** efeito é recusado antes de rodar |
| não altera dado | contexto com `persistence_allowed=False` |
| não duplica efeito | roda sobre a **entrada** do primário, nunca sobre a saída |
| respeita orçamento | timeout e budget explícitos, com estado próprio |

Falha do shadow nunca vira falha do usuário: exceção é capturada, o tipo vira
motivo e a mensagem não viaja.

## 8. E7 — Quality / Cost / Latency Routing · `EXTEND`

`app/modules/routing_intelligence/`

`task_router`, `provider_health`, `provider_catalog`, `provider_binding` e
`provider_authorization` continuam decidindo autorização. Esta camada apenas
**ordena quem já passou** por elas.

- **Eliminação antes de ordenação.** Política, capability, homologação,
  circuito e disponibilidade *eliminam*; nota alta não compra permissão.
- **Pesos declarados por estratégia**, somando 1 — verificado por teste. Não
  há peso mágico no meio do código.
- **Custo e latência são invertidos** porque menor é melhor; somar sem
  inverter produziria um número sem significado.
- **Seleção fora do ranking é recusada pelo schema** — seria bypass de
  política.
- **Empate resolvido por id**: decisão de roteamento não pode ser sorteio.

## 9. E8 — Prompt & Configuration Registry · `BUILD`

`app/modules/asset_registry/`

Versiona apenas **asset governado**: system prompt, template, config de
routing/avaliação/risco. Prompt de usuário **não entra** — guardá-lo
transformaria um registry de configuração em repositório de dados alheios.

- **Segredo é recusado na entrada.** Um registry guarda para sempre: um
  segredo que entra fica em todas as versões seguintes.
- **Hash confere o conteúdo.** Sem isso, o campo diria uma coisa e o texto
  seria outra.
- **No máximo uma versão ativa.** Duas seria pior que nenhuma: ninguém saberia
  qual rodou.
- **Nasce em `DRAFT`**: publicar e ativar são decisões diferentes.
- Conteúdo idêntico **não** cria versão nova.

## 10. E9 — Unified Audit Trail / Correlation · `EXTEND`

`app/modules/correlation/`

`audit` e `observability` continuam. O que nasceu é o `correlation_id` que
atravessa as etapas e a trilha de fatos mínimos.

- **Ponteiro, nunca conteúdo.** A trilha guarda `analysis_id`, `contract_id`,
  `evidence_id` — não payload. Copiar o conteúdo de cada etapa dobraria a
  superfície de vazamento para responder a mesma pergunta.
- **Redação na entrada**, e não na saída: a trilha é armazenamento de longa
  duração. Chave proibida e valor com forma de segredo são **recusados**, não
  redigidos em silêncio — quem tentou gravar precisa saber.
- **Correlação derivada é estável entre retries**, para a operação não se
  fragmentar em duas trilhas.
- **Chave composta (`project_id`, `correlation_id`)**: o namespace do outro
  projeto simplesmente não existe.
- **Trilha limitada**: ilimitada seria vazamento de memória com aparência de
  recurso.

## 11. E10 — SLO / Operational Health · `BUILD`

`app/modules/slo/` · `GET /api/health/slo`

Nove indicadores com estado explícito e dois limiares cada.

- **Sem medição, o indicador é `UNKNOWN` — nunca `HEALTHY`.** Um painel verde
  por falta de dado é pior que um painel vazio: produz confiança sem base.
- **Amostra mínima declarada.** Três sucessos não provam disponibilidade.
- **Dois limiares**, e não um: um sistema que só soubesse "bom" e "morto" não
  daria tempo de reagir.
- **Série limitada** por indicador nomeado — sem cardinalidade por requisição,
  usuário ou prompt.

## 12. E11 — Compatibility Matrix · `BUILD`

`app/modules/compatibility/` · `POST /api/compatibility/check`

Responde: *"este consumidor pode usar esta capability com estas versões?"*

- **Nenhuma tabela por projeto.** A resposta é **calculada** perguntando à
  camada dona de cada dimensão. Consumidor novo é atendido por existir no
  manifesto, sem tocar neste módulo — verificado por teste de AST.
- **`UNKNOWN` é resposta de primeira classe.** Não saber é diferente de ser
  incompatível, e as duas coisas exigem ações diferentes: uma manda parar, a
  outra manda descobrir.
- **O pior achado decide**, e a resposta mostra a conta dimensão a dimensão.

## 13. E12 — Disaster Recovery + Restore Verification · `BUILD`

`app/modules/disaster_recovery/`

Backup não é o produto. **Um backup que nunca foi restaurado é uma hipótese.**

- **A destruição faz parte da prova.** Sem destruir, o ensaio passaria mesmo
  com um backup vazio — o estado original ainda estaria lá.
- **Ordem de restauração declarada e conferida.** Identidade primeiro, outbox
  por último: reentregar antes de o destino existir duplicaria efeito. A
  consistência da ordem é verificada por teste, porque uma dependência que
  restaura depois é o pior modo de falha — não aparece até o dia do desastre.
- **Divergência em qualquer store reprova a restauração inteira.** Restauração
  parcial silenciosa é sistema incompleto se comportando como completo.
- **Nenhum dado real no ensaio.** O manifesto declara
  `contains_production_data`.

## 14. Como as 12 se conectam

```text
Consumer SDK  →  Compatibility  →  Policy  →  Runtime / Risk
                                                    ↓
                                                 Routing
                                                    ↓
                                            Providers / Models
                                                    ↓
                                        Audit + Correlation
                                                    ↓
                     Evaluation  →  Model Registry / Promotion
                                                    ↓
                                    Control Center  →  SLO / Health

                    Disaster Recovery protege o estado crítico
```

Não são doze ilhas: a matriz consulta os registries, o Control Center agrega
o SLO e os registries, o routing respeita a política, e a promoção exige a
evidência que a avaliação produziu.

## 15. Estado verificado

```text
backend (PostgreSQL real)   1744 passed ·  8 skipped · 0 failed
backend (paridade CI)       1722 passed · 30 skipped · 0 failed
ruff                        PASS
frontend                     117 passed · typecheck PASS · build PASS
grafo documental             172 documentos · 1007 links · 0 violações
contract freeze              6 fingerprints intactos
OpenAPI                      40 → 43 paths · 166 → 180 schemas · ADITIVO
npm audit --omit=dev         0 vulnerabilidades
```

Nenhum contrato V1 congelado foi alterado. Nenhuma migration histórica foi
editada. Os 30 skips são 22 de PostgreSQL (executados contra banco real neste
fechamento) e 8 de opt-in de provider real.

## 16. Fora do escopo desta frente

Não executado, e registrado como próxima frente:

```text
PedroCore → Veltrix (rename global)
publicação pública do repositório
migração completa dos consumidores
fine-tuning real · dataset artificial · treinamento artificial
```

## 17. Possíveis evoluções futuras — apenas estudo

Nenhuma foi implementada. Cada uma com o que é, o problema que resolve, como
integraria, o benefício e por que foi adiada.

### MCP + A2A Gateway

Porta padronizada para agentes externos conversarem com o PedroCore e entre
si. **Resolve** o acoplamento de cada consumidor a um cliente próprio.
**Integraria** como fachada sobre o Consumer SDK e os Universal Contracts.
**Benefício:** onboarding sem código de integração. **Custo/risco:** amplia a
superfície de autorização para um protocolo que ainda está se estabilizando.
**Adiada porque** o SDK acabou de nascer e uma fachada sobre uma camada
recém-criada congelaria decisões que ainda vão mudar.

### Just-in-Time Capability Leases

Capability concedida por janela curta em vez de declarada permanentemente.
**Resolve** o privilégio que sobra depois que a necessidade passou.
**Integraria** no Capability Manifest e no Policy Engine, como atributo com
validade. **Benefício:** menor superfície permanente. **Custo/risco:** relógio
vira dependência de autorização, e relógio errado passa a ser falha de
segurança. **Adiada porque** exige um modelo de tempo confiável que o core
ainda não tem.

### Proof of Execution

Prova criptográfica de que a execução aconteceu como o contrato previa.
**Resolve** a lacuna entre "o contrato autorizou" e "foi isso que rodou".
**Integraria** no Execution Contract, que já é assinado, mais evidência
pós-execução. **Benefício:** fecha o ciclo `Risk prevê / Execution prova`.
**Custo/risco:** exige cooperação do executor, que é externo ao PedroCore.
**Adiada porque** depende de mudança nos consumidores, que é frente própria.

### Decision Replay / Time Travel

Reexecutar uma decisão passada com as versões daquele momento. **Resolve** a
pergunta "por que o sistema decidiu isso naquele dia". **Integraria** no
Audit Trail mais os registries versionados — as peças já existem.
**Benefício:** auditoria sem arqueologia. **Custo/risco:** exige guardar o
estado de todas as versões consultadas, o que multiplica armazenamento.
**Adiada porque** o Asset Registry e o Policy Engine acabaram de nascer e
ainda não têm histórico suficiente para valer o replay.

### Counterfactual Risk Lab

Perguntar "o que teria acontecido se o gate fosse outro". **Resolve** a
calibração da política de risco sem esperar incidente real. **Integraria** no
Risk Engine mais o histórico já persistido. **Benefício:** ajustar limiar com
base em dado, não em intuição. **Custo/risco:** contrafactual mal calibrado
vira justificativa para afrouxar gate. **Adiada porque** o histórico de risco
ainda é pequeno, e contrafactual sobre amostra pequena é opinião com número.

### OpenTelemetry GenAI

Instrumentação padronizada das convenções semânticas de IA. **Resolve** a
observabilidade proprietária que não conversa com ferramenta de mercado.
**Integraria** na observabilidade existente e no SLO. **Benefício:**
ferramental externo sem adaptador. **Custo/risco:** as convenções GenAI ainda
estão mudando, e adotar cedo é reescrever depois. **Adiada porque** a
especificação não estabilizou.

### AI-BOM / CycloneDX

Inventário assinado de modelos, prompts, datasets e dependências.
**Resolve** "o que exatamente compõe este sistema de IA". **Integraria** com o
Model Registry e o Asset Registry, que já têm hash e proveniência.
**Benefício:** requisito de conformidade que vai chegar. **Custo/risco:**
formato ainda em evolução. **Adiada porque** os registries precisam acumular
conteúdo real antes de valer a pena inventariar.

### Sigstore / in-toto

Assinatura e atestação de proveniência da cadeia de build. **Resolve** a
confiança em artefato construído em pipeline. **Integraria** na CI e no
Evidence Platform. **Benefício:** proveniência verificável de ponta a ponta.
**Custo/risco:** exige gestão de chave e infraestrutura de transparência.
**Adiada porque** o repositório é privado e a cadeia de distribuição ainda não
existe.
