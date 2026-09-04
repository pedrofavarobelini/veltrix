# Veltrix — Glossário

Atualizado em: 03/09/2026 · **ESTUDO ATUAL**

Definições tiradas dos documentos canônicos do vault. Nada aqui é inventado.

---

## Produto e história

**Veltrix** — o produto. *AI Runtime & Learning Control Plane*: fica entre um
agente de IA e a execução, e analisa, decide, governa e registra. Não executa.

**PedroCore** — o nome **anterior** do produto. Hoje aparece em três formas
legítimas: `PedroCore` maiúsculo é história (o produto se chama Veltrix);
`pedrocore` minúsculo é **identificador técnico preservado** (tabelas
`pedrocore_*`, contratos `pedrocore-risk-request/v1`, `project_id="pedrocore"`);
`PEDROCORE_*` é variável de ambiente mantida como alias.

**Functional Freeze** — estado do projeto após o Final Functional Gate. A
manutenção comum está encerrada. Reabrir exige que a mudança aumente uma
capacidade real do Veltrix ou seja necessária para ele operar como núcleo de
outro sistema.

## Arquitetura

**Runtime Plane** — o plano que *responde agora*: chat, orchestration,
providers, policy, risk.

**Learning Plane** — o plano que *aprende depois*: operational intelligence,
memória, dataset, training foundation. A fronteira entre os dois é verificada
por teste: import de topo do Runtime para o Learning reprova a suíte.

**Control Plane** — o conjunto das Eras 1–10 que organizou o sistema nos dois
planos e construiu a plataforma de integração universal sobre eles.

**Evidence Platform** — ingestão fail-closed com validação de contrato. É por
onde fato verificado atravessa do Runtime para o Learning.

**Universal Contract** — um dos cinco contratos V1 congelados (Project
Capability Manifest, Quality Evidence, Execution Outcome, Learning Source e o
envelope de integração). Alterar a forma de qualquer um quebra o build.

**Contract freeze** — congelamento por fingerprint de schema. Mudança aditiva
não muda versão; breaking exige v2 com a v1 mantida; versão desconhecida é
recusada fail-closed.

## Risk Engine

**Risk Engine** — subsistema delimitado que analisa e governa risco de execução
por IA. **Nunca executa.** Emite contrato; quem executa é o Agent, fora.

**Risk Engine V2** — a evolução que fechou cinco problemas objetivos do V1
(P1 persistência própria, P2 simulação real, P3 blast radius com unidade,
P4 bypass de gate impossível, P5 contrato universal), em seis stages R0–R5.

**Risk Console** — a interface do motor: TUI e CLI (`veltrix risk`), com três
estados exclusivos de tela — entrada, revisão de contexto, resultado.

**Project Registry** — catálogo dos projetos que o Veltrix conhece.
**Identidade, não capacidade**: um projeto registrado é analisável; o que ele
não ganha é permissão.

**Gate** — a decisão do motor sobre uma operação. Três valores.

**BLOCK** — o gate mais restritivo: a operação não deve prosseguir. É
**intransponível por construção** — há teste negativo provando que não existe
caminho de bypass (foi exatamente o problema P4).

**Blast radius** — o alcance estimado de uma operação, com unidade explícita.
Antes do R3 era um número sem unidade, portanto sem significado.

**Execution Contract** — o artefato que transforma análise em restrições
verificáveis. HMAC cobre todos os campos, tem validade, e override humano
autorizado é registrado.

**Human Review** — o estado de gate em que a decisão volta para uma pessoa. O
Veltrix não a substitui em nenhum fluxo crítico.

## Providers

**Provider** — serviço ou módulo que gera resposta. Pode ser real, simulado ou
local determinístico.

**Provider real** — provider externo com chamada de rede: Gemini, OpenAI,
Claude, DeepSeek, Grok. Bloqueado por padrão.

**Mock** — provider interno simulado. Sem rede, sem chave, sempre disponível. É
o fallback seguro do pipeline e **nunca** aprova release gate.

**Local QA** (`local_qa`) — pseudo-provider determinístico para análise textual.
Não é LLM, não usa rede. É o **único** provider em que o release gate confia.

**Local Model** (`local_model`) — provider generativo local. Registrado,
opt-in, **default-off e sem transport real**. Não é `local_qa`.

**Binding** — validação de provider **e** modelo como unidade, antes de
qualquer adapter. Combinação incoerente é bloqueada.

**Authorization** — a matriz fail-closed
`identity_strength + project_id + caller_role + environment + provider`.
Default é negar; cada combinação precisa estar registrada explicitamente.

**Os seis estados** — conhecido, configurado, homologado, autorizado,
executável, executado. Ver [[PEDROCORE_FLUXO_COMPLETO]].

**Fallback** — substituição da resposta quando o provider não conclui. Desde o
Final Functional Gate a semântica é **por boundary**: consumers integrados
mantêm o Mock seguro (`allow_mock_fallback=true`, o default); o chat interativo
com IA real escolhida envia `allow_mock_fallback=false` e a falha volta como
falha.

**Safe Mode** — conjunto de bloqueios que evita chamada acidental a provider
real. `allow_real_provider=false` é o padrão.

## Governança e aprendizado

**Policy Engine** — invariantes executáveis, entre elas
`automatic_collection = false`, `Operational Data != Training Candidate` e
"execução nunca delegada ao core".

**Operational Intelligence** — extração de sinais determinísticos de relatórios
técnicos. Sinais, não pesos.

**Operational Memory** — repositório de padrões, evidências, confidence e
lifecycle. Alimenta o Historical Risk.

**Report Memory** — memória técnica controlada, default-off. **Não é
treinamento e não é RAG.**

**Dataset** — no Veltrix, a população candidata governada. Hoje **não existe**
dataset canônico gerado.

**Training Candidate** — um registro que passou por autorização explícita para
poder virar exemplo de treino. Hoje: **zero** autorizados.

**`DATASET_NOT_READY`** — o resultado atual de readiness. **Não é erro**: é a
resposta correta quando não existe população real autorizada e nada foi
fabricado.

**`CONTROL_PLANE_READY`** — o plano de controle está pronto. **Não** implica
`DATASET_READY`.

## Integração

**Consumer** — sistema externo que usa o Veltrix por contrato: FinGuard, Elyra,
Structa. Cada um com identidade própria e menor privilégio.

**Capability** — o que um projeto declara saber fazer, no Capability Manifest.
Distinto de identidade: o Project Registry cuida da segunda.

## Termos que continuam valendo do glossário anterior

**API**, **Backend**, **Orchestrator**, **Task Router**, **Project Context**,
**Policy Enforcement**, **Prompt Builder**, **Report Intelligence**,
**Eval Harness**, **Release Gate**, **Audit**, **Artifact Reader**,
**`context_from_memory`**, **`allow_real_provider`**, **`allow_local_model`**,
**Warning code**, **RAG** (não existe no Veltrix), **Fine-tuning** (não é
feito), **Treinamento** (fora do escopo).

## Links relacionados

- [[../MOC_ESTUDO_PEDROCORE]]
- [[PEDROCORE_FLUXO_COMPLETO]]
- [[PEDROCORE_PERGUNTAS_E_RESPOSTAS]]
- [[../MOC_SEGURANCA]]
- [[../14-intelligence-layer/INTELLIGENCE_LAYER_OVERVIEW]]
