# Veltrix — Resumo Executivo

Atualizado em: 03/09/2026 · **ESTUDO ATUAL**

Fechamento canônico: [[../19-encerramento-final/VELTRIX_FINAL_FUNCTIONAL_GATE]].
Estado arquitetural: [[../17-veltrix/VELTRIX_FINAL_STATE]].

---

## 1. O que o Veltrix é

**Veltrix — AI Runtime & Learning Control Plane.**

Ele fica entre um agente de IA e a execução, e responde três perguntas antes de
qualquer coisa acontecer:

```text
AI interpreta.      Policy decide.
Risk prevê.         Execution prova.
Evidence registra.  Learning governa.
```

Não executa comando, não escreve arquivo, não deleta nada. Analisa, decide,
governa e registra. A recusa a executar é regra do Policy Engine com teste
negativo, não promessa de documentação.

**Ele não é um modelo treinado.** Não há fine-tuning, autoaprendizado, RAG
vetorial nem modelo próprio.

## 2. Por que existe

Sem ele, cada projeto do ecossistema integraria direto com Gemini, OpenAI,
Claude — duplicando chaves, política de custo, fallback, tratamento de erro e
auditoria. Com ele, existe **uma** camada que resolve identidade, autorização,
provider, modelo e prompt, e devolve resposta padronizada.

## 3. Os dois planos

A fronteira arquitetural central, declarada na Era 2 e **verificada por teste**
(um import de topo do Runtime para o Learning reprova a suíte):

| Plano | Pergunta | O que contém |
|---|---|---|
| **Runtime Plane** | *responder agora* | chat, orchestration, providers, policy, risk |
| **Learning Plane** | *aprender depois* | operational intelligence, memória, dataset, training foundation |

Entre eles passam **evidência e contratos**, nunca chamadas diretas.

## 4. Risk Engine

Subsistema delimitado: **analisa e governa risco, nunca executa**.

```text
RiskRequest → Intent → Contexto resolvido → Prompt Quality → Ambiguidade
→ Escopo → Sinais → Findings → Gate → Execution Contract
→ (execução acontece FORA) → Post-Execution QA → Historical Intelligence
```

O **V2** fechou cinco problemas objetivos do V1, cada um com evidência:
persistência própria do domínio (P1), simulação relevante ao payload (P2),
métrica de alcance com unidade (P3), bypass de gate provado impossível por
teste (P4) e contrato universal de submissão (P5).

Tem interface própria: **Risk Console** (TUI), CLI (`veltrix risk`) e rota HTTP
do contrato universal. O **Project Registry** é o catálogo de projetos que ele
conhece — identidade, não capacidade.

Estudo dedicado: [[VELTRIX_RISK_ENGINE_ESTUDO]].

## 5. Control Plane

Eras 1–10, todas PASS. Baseline arquitetural, separação dos dois planos,
Universal Contracts V1, Evidence Platform, Learning Governance V2, resiliência
de integração, Dataset Control Plane, Evaluation/Training Foundation e Contract
Freeze.

Sobre isso vieram **doze evoluções de plataforma**: Consumer SDK, Policy
Engine, Control Center, Evaluation Plane V2, Model Registry com promoção por
evidência, Shadow Mode, roteamento explicável, registry versionado de prompts,
trilha de auditoria com correlação, SLO com estado explícito, matriz de
compatibilidade e Disaster Recovery com restauração **provada** contra
PostgreSQL real.

Estado arquitetural: **`CONTROL_PLANE_READY`**.

## 6. Evidence Platform

Ingestão fail-closed com validação de contrato. É por onde fato verificado
atravessa do Runtime para o Learning. Sem evidência válida, nada entra no
Learning Plane — e evidência não vira automaticamente candidato de treino.

## 7. Providers

Seis estados, e confundi-los é o erro mais comum:

| Estado | Significa | Hoje |
|---|---|---|
| conhecido | está no catálogo | mock, gemini, openai, claude, deepseek, grok, local_qa, local_model |
| configurado | tem credencial no ambiente | **gemini** |
| homologado | aprovado para uso real | **gemini** |
| autorizado | passou pela matriz identidade+projeto+papel+ambiente | por regra explícita |
| executável | implementado + configurado + homologado | **gemini** |
| executado | o adapter foi chamado **e respondeu** | por requisição |

A arquitetura multi-provider está concluída; a **operação** multi-provider não,
porque só um provider está homologado. Isso é decisão de homologação, não
pendência técnica.

## 8. Safety e governança

- `allow_real_provider=false` por padrão (safe mode);
- `allow_local_model=false`, `context_from_memory=false`, Report Memory e
  Artifact Reader default-off;
- Policy Engine recusa execução, escrita, deleção, deploy e push;
- release gate só confia em `local_qa` com evidência textual limpa;
- guard de testes impede que a suíte padrão alcance provider real ou rede;
- contratos V1 congelados por fingerprint de schema.

## 9. Learning / Dataset — o que existe e o que não existe

| Camada | Estado |
|---|---|
| Operational Intelligence, Memory, Retrieval V1, Safe Reuse | **implementado** |
| Report Intelligence, Report Memory | **implementado**, default-off |
| Dataset Foundation, Candidate Lifecycle | **implementado** |
| Candidate Acquisition Foundation | **implementada** |
| Candidatos reais autorizados | **0** |
| Readiness | **`DATASET_NOT_READY`** |
| Canonical Dataset, splits, Hugging Face, fine-tuning, PEFT/LoRA/SFT, modelo próprio | **não iniciados** |

`CONTROL_PLANE_READY` **não** significa `DATASET_READY`. Governança pronta não
fabrica população: são coisas independentes, e o resultado correto hoje é
`DATASET_NOT_READY`.

## 10. Integrações

Consumers registrados: **FinGuard**, **Elyra**, **Structa** — cada um com
identidade própria, menor privilégio e contrato próprio. O Veltrix não lê nem
altera o repositório de nenhum deles.

## 11. Estado atual

```text
Produto / UI              V5.2.0
API / backend             0.2.0
Tags Git                  v2.0.0 … v7.0.0  (linha independente)
Superfície HTTP           43 paths
Migrations                0001–0012, todas aditivas

VELTRIX FINALIZATION      = PASS
VELTRIX FUNCTIONAL FREEZE = ACTIVE
GITHUB PUBLICATION        = CONFIRMED   (Apache-2.0, público)
HUMAN_VISUAL_ACCEPTANCE   = PASS
HUMAN_RUNTIME_ACCEPTANCE  = PASS
```

O último defeito funcional foi corrigido no **Final Functional Gate**: no chat
interativo, uma falha do provider real deixou de ser disfarçada de resposta do
Mock. A semântica final do fallback está em [[PEDROCORE_FLUXO_COMPLETO]].

## 12. Freeze

A manutenção comum está **encerrada**. Reabrir exige responder *sim* a:

> Esta mudança aumenta uma capacidade real do Veltrix, ou é necessária para ele
> operar como núcleo de outro sistema?

Trocar texto, rearranjar card, refatorar por preferência ou redesenhar UI
**não** reabrem o projeto.

## Links relacionados

- [[../MOC_ESTUDO_PEDROCORE]] — Study Pack completo e sequência recomendada
- [[../MOC_VELTRIX]] — entrada do vault
- [[VELTRIX_LINHA_DO_TEMPO]] — como o projeto chegou até aqui
- [[VELTRIX_RISK_ENGINE_ESTUDO]] — o maior subsistema
- [[PEDROCORE_MAPA_MENTAL]] — a mesma coisa em árvore
- [[../19-encerramento-final/VELTRIX_FINAL_FUNCTIONAL_GATE]] — fechamento canônico
