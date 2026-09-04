# Veltrix — Mapa Mental

Atualizado em: 03/09/2026 · **ESTUDO ATUAL**

Árvore para memorizar a forma do sistema. O detalhe vive em
[[PEDROCORE_RESUMO_EXECUTIVO]] e [[PEDROCORE_FLUXO_COMPLETO]].

---

## A árvore

```text
VELTRIX — AI Runtime & Learning Control Plane
│
├── RUNTIME PLANE ......................... responder agora
│   ├── Chat / Orchestration
│   │   ├── POST /api/chat ............... compatibilidade + chat da UI
│   │   ├── POST /api/orchestrate ........ pipeline central dos consumers
│   │   ├── Task Router .................. task_type → criticidade, estilo
│   │   ├── Project Context .............. origin_system → limites do projeto
│   │   ├── Prompt Builder ............... prompt enriquecido
│   │   └── Audit ........................ metadados de cada requisição
│   ├── Providers
│   │   ├── Provider Catalog ............. o que existe e em que estado
│   │   ├── Caller Identity .............. quem chamou, com que força
│   │   ├── Provider Authorization ....... matriz fail-closed
│   │   ├── Provider Binding ............. provider + modelo como unidade
│   │   ├── Shadow / Enforced Routing .... escolha determinística
│   │   ├── Health / Circuit Breaker ..... default-off
│   │   └── Fallback ..................... por boundary, não global
│   ├── Policy
│   │   ├── Policy Enforcement ........... bloqueia antes do provider
│   │   └── Policy Engine ................ invariantes executáveis
│   └── Risk .............................. entrada do Risk Engine
│
├── RISK ENGINE ........................... analisa e governa; NUNCA executa
│   ├── Pre-execution .................... intent, contexto, ambiguidade, escopo
│   ├── Seis dimensões ................... dados, segurança, migração,
│   │                                       escopo, regressão, operação
│   ├── Blast radius ..................... alcance com unidade (P3)
│   ├── Scenarios ........................ simulação relevante ao payload (P2)
│   ├── Gates ............................ ALLOW / REVIEW / BLOCK
│   ├── Execution Contract ............... HMAC, validade, override humano
│   ├── Post-execution QA ................ compara resultado × contrato
│   ├── Historical Intelligence .......... padrões sobre Operational Memory
│   ├── Risk Console ..................... TUI/CLI, três estados de tela
│   └── Project Registry ................. catálogo de projetos = identidade
│
├── EVIDENCE PLATFORM ..................... fail-closed; ponte entre os planos
│
├── LEARNING PLANE ........................ aprender depois
│   ├── Operational Intelligence ......... sinais de relatórios técnicos
│   ├── Operational Memory / Retrieval V1  padrões, evidências, FTS sem embeddings
│   ├── Safe Reuse ....................... reuso sem bypass de provider
│   ├── Report Memory .................... default-off; NÃO é treinamento
│   ├── Dataset Foundation ............... dado operacional ≠ candidato
│   ├── Candidate Acquisition ............ implementada; 0 candidatos autorizados
│   └── Training Foundation .............. fundação; DATASET_NOT_READY
│
├── CONTROL PLANE ......................... Eras 1–10, todas PASS
│   ├── Universal Contracts V1 ........... 5 contratos + envelope, congelados
│   ├── Model Registry ................... promoção por evidência
│   ├── Evaluation Plane V2
│   ├── Shadow Mode / Routing Intelligence
│   ├── Consumer SDK · Control Center
│   ├── SLO · Compatibility Matrix
│   └── Disaster Recovery ................ restauração PROVADA
│
├── PROVIDERS ............................. seis estados distintos
│   ├── mock ............................. interno, sem rede, fallback seguro
│   ├── local_qa ......................... determinístico; único que libera gate
│   ├── local_model ...................... opt-in, default-off, sem transport
│   ├── gemini ........................... ÚNICO real homologado
│   └── openai · claude · deepseek · grok  conhecidos, não homologados
│
├── CONSUMERS ............................. identidade própria, menor privilégio
│   ├── FinGuard · Elyra · Structa
│   └── o Veltrix nunca lê nem altera o repositório deles
│
└── GOVERNANCE / SAFETY
    ├── Safe mode ........................ allow_real_provider=false por padrão
    ├── Opt-ins default-off .............. local_model, memória, reader
    ├── Contract freeze .................. fingerprint de schema
    ├── Guard de testes .................. suíte padrão nunca alcança rede
    └── Functional Freeze ................ manutenção comum encerrada
```

## Sete coisas que a árvore não mostra e você precisa saber

1. **A fronteira entre os planos é testada.** Um import de topo do Runtime para
   o Learning reprova a suíte. Não é convenção, é regra executável.
2. **O Risk Engine não executa.** Ele emite um contrato assinado; quem executa é
   o Agent, fora do Veltrix. Depois compara o resultado com o contrato.
3. **`CONTROL_PLANE_READY` ≠ `DATASET_READY`.** Governança pronta não fabrica
   população. Hoje: 0 candidatos reais autorizados.
4. **Provider "selecionado" não é "executado".** São seis estados diferentes.
5. **Fallback é por boundary.** Consumer integrado mantém o Mock seguro; o chat
   interativo com IA real escolhida mostra a falha.
6. **`local_qa` ≠ `local_model`.** O primeiro é heurística determinística e é o
   único que libera release gate; o segundo é um LLM local que não existe ainda.
7. **`pedrocore` minúsculo não é erro.** É identificador técnico preservado de
   propósito. `PedroCore` maiúsculo, esse sim, virou `Veltrix`.

## Links relacionados

- [[../MOC_ESTUDO_PEDROCORE]]
- [[PEDROCORE_RESUMO_EXECUTIVO]]
- [[PEDROCORE_FLUXO_COMPLETO]]
- [[VELTRIX_RISK_ENGINE_ESTUDO]]
- [[../MOC_ARQUITETURA]]
- [[../MOC_SEGURANCA]]
