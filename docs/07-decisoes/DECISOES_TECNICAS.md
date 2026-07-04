# PedroCore IA — Decisões Técnicas

## Decisão 001 — Não treinar IA do zero

O projeto cria uma camada/orquestrador de IA, não um modelo próprio.

## Decisão 002 — Backend em Python

Python foi mantido por alinhamento com IA e aprendizado do usuário.

## Decisão 003 — Frontend em React + TypeScript

A interface continua simples, moderna e fácil de testar.

## Decisão 004 — V2 não será Gemini-only

A V2 entrega estrutura multi-provider completa inicial.

## Decisão 005 — Fallback obrigatório

Se qualquer provider real falhar, a resposta cai para MockProvider. Isso evita quebrar a interface.

## Decisão 006 — Chaves fora do código

Todas as API keys ficam somente no `.env`, nunca no GitHub ou no frontend.

## Decisão 007 — PedroCore IA como orquestrador central de IA do ecossistema Pedro

O PedroCore deixa de ser documentado apenas como chat pessoal e passa a ser a camada central de orquestração de IA para os projetos do ecossistema Pedro: recebe mensagem/contexto/tipo de tarefa, escolhe estratégia, seleciona provider/modelo e devolve resposta padronizada.

## Decisão 008 — Sistemas externos devem consumir IA preferencialmente via PedroCore

A direção estratégica é que outros sistemas do ecossistema Pedro consumam capacidades de IA através do PedroCore, em vez de integrarem provedores diretamente. Essa integração ainda não está implementada; é objetivo futuro.

## Decisão 009 — FinGuard é projeto externo e não deve ser alterado pelo PedroCore

O FinGuard permanece um repositório e sistema independentes. O PedroCore não altera código, dados, configuração ou documentação do FinGuard.

## Decisão 010 — QA Automation do FinGuard permanece dentro do FinGuard

A validação técnica (API, backend, frontend, rotas, banco de teste, Prisma, Playwright, smoke tests, E2E, relatórios e evidências) é e continua sendo um subsistema interno do FinGuard. O PedroCore não reimplementa nem substitui essa validação.

## Decisão 011 — IA exploratória/visual do QA será caso de uso futuro do PedroCore

Apenas a parte de IA exploratória/visual/inteligente do QA Automation do FinGuard foi delegada ao PedroCore, como caso de uso futuro (QA Intelligence). Não implementado nesta etapa.

## Decisão 012 — PedroCore não calcula números financeiros oficiais de sistemas externos

O PedroCore pode, no futuro, explicar, resumir e sugerir a partir de artefatos e dados lidos, mas nunca substitui os cálculos financeiros oficiais de sistemas como o FinGuard.

## Decisão 013 — Providers reais exigem controle explícito para evitar chamadas acidentais

A ausência de chave de API não pode ser o único mecanismo de proteção contra chamadas reais acidentais. Providers reais devem ter, no planejamento técnico futuro, um controle explícito (ex.: flag de ambiente ou confirmação) antes de serem acionados, especialmente em fluxos automatizados ou testes.

## Decisão 014 — Fallback Mock não pode validar tarefas críticas silenciosamente

O fallback automático para `MockProvider` é aceitável para preservar a experiência de chat, mas não pode ser usado, no futuro, para "validar" silenciosamente tarefas críticas de sistemas externos (ex.: análises de QA). Qualquer consumidor crítico deve checar explicitamente `fallback_used` antes de considerar uma resposta como real.

## Decisão 015 — Frontend/design ficam congelados durante a reformulação arquitetural

Durante a frente `PEDROCORE-REPLAN-01` (consolidação documental, planejamento técnico e arquitetura-alvo), nenhuma mudança de frontend, layout, tema, identidade visual ou componente é realizada. O frontend permanece na V5.1.9 até que a reformulação documental/arquitetural seja concluída.

## Decisão 016 — Contratos técnicos devem ser documentados antes da implementação

Qualquer contrato de entrada/saída, tipo de tarefa ou resposta estruturada do PedroCore deve ser especificado em documentação (`docs/10-contratos/`) antes de virar código. Isso reduz retrabalho e garante que decisões de segurança e escopo (ex.: limites com o FinGuard) sejam fixadas antes da implementação.

## Decisão 017 — Sistemas externos devem enviar `origin_system` e `task_type` em contratos futuros

Todo contrato futuro de orquestração exige, no mínimo, `origin_system` (quem está chamando) e `task_type` (o que está sendo pedido), para permitir roteamento, auditoria e aplicação de regras específicas por tipo de tarefa.

## Decisão 018 — Respostas críticas devem ter formato estruturado

Tarefas classificadas como críticas (ex.: `qa_report_analysis`, `qa_failure_diagnosis`, `release_gate_review`, `visual_qa_analysis`) devem exigir `response_format: "structured"`, nunca apenas texto livre, para permitir que o sistema de origem processe a resposta de forma confiável.

## Decisão 019 — Artefatos externos devem ser recebidos inicialmente por payload, não por leitura automática de pastas

Nesta fase de planejamento, qualquer artefato (relatório, log, documento) só é considerado recebido pelo PedroCore se enviado no corpo da requisição (`artifacts[].content`). Leitura automática de diretórios ou arquivos de outros projetos (incluindo o FinGuard) é explicitamente fora de escopo até uma decisão arquitetural futura e específica.

## Decisão 020 — Tarefas críticas não podem depender silenciosamente de fallback Mock

Para tarefas críticas, uma resposta gerada via fallback (`MockProvider`) nunca deve ser apresentada como análise real. `fallback_used: true` nessas tarefas deve gerar warning forte e, dependendo do desenho futuro, bloquear a conclusão da tarefa (`status: "blocked"`), em vez de devolver um resultado simulado como se fosse confiável.

## Decisão 021 — QA Intelligence será planejada como caso de uso do PedroCore, não como substituição do QA Automation

A futura QA Intelligence do PedroCore (delegada de `QA-AUTOMATION-01G`) é um caso de uso de análise exploratória/visual assistida por IA, complementar ao QA Automation do FinGuard — nunca uma substituição da validação técnica (API, backend, frontend, rotas, banco de teste, Prisma, Playwright, smoke tests, E2E) que continua sendo responsabilidade do próprio FinGuard.

## Decisão 022 — Task Router será responsável por classificar tarefas antes de chamar providers

Toda solicitação de orquestração deve ser classificada por `task_type`/`origin_system` antes de qualquer chamada a provider. O Task Router é o módulo planejado para essa responsabilidade; providers não devem decidir estratégia de tarefa.

## Decisão 023 — Prompt Builder será responsável por montar prompts; providers apenas executam chamadas

A montagem do prompt final (combinando `system_prompt`, `task_type`, contexto de projeto, artefatos e formato de resposta esperado) é responsabilidade do Prompt Builder planejado, não dos providers individuais. Providers executam a chamada ao modelo com o prompt já pronto.

## Decisão 024 — Project Context será a camada conceitual de configuração por sistema externo

Cada sistema externo (ex.: FinGuard) é representado, na arquitetura-alvo, por um Project Context com metadados e limites próprios (tarefas permitidas, somente leitura, proibição de executar comandos ou escrever arquivos), sem acoplamento direto ao código do sistema externo.

## Decisão 025 — `/api/chat` deve permanecer compatível durante a evolução arquitetural

Qualquer novo endpoint de orquestração deve coexistir com `POST /api/chat`, sem quebrar o uso conversacional atual nem exigir mudança no frontend existente.

## Decisão 026 — Artifact Reader futuro deve ser somente leitura e não pode executar comandos em projetos externos

Quando implementado, o Artifact Reader nunca escreve, nunca comita e nunca executa comandos em projetos externos (incluindo o FinGuard). Nesta fase, artefatos só são recebidos via payload, nunca por leitura automática de pasta/repositório.

## Decisão 027 — Audit/logs devem ser planejados antes de integrações reais com sistemas externos

Os campos de auditoria (origem, tarefa, provider, fallback, erro, latência, timestamp, criticidade) devem estar definidos e implementados antes de qualquer integração real com sistemas externos, para garantir rastreabilidade desde o primeiro uso em produção. Nenhum dado sensível ou chave de API deve ser armazenado em log.

## Decisão 028 — QA Intelligence será camada de análise, não executor de testes

QA Intelligence interpreta artefatos e relatórios já produzidos por processos de QA externos e devolve diagnóstico estruturado. Ela nunca executa testes, scripts, migrations, seed/reset ou qualquer comando dentro de um sistema externo, incluindo o FinGuard.

## Decisão 029 — Relatórios QA Markdown devem ser aceitos inicialmente como texto/payload

Como os relatórios de QA do FinGuard hoje são Markdown livre, o PedroCore deve planejar a extração de informações por interpretação textual tolerante a variação, sem depender inicialmente de um schema JSON estruturado do lado do sistema externo. JSON estruturado pode ser uma evolução futura, não um pré-requisito.

## Decisão 030 — Fallback Mock em tarefa crítica de QA deve bloquear ou reduzir confiança

Uma resposta de QA gerada via fallback (`MockProvider`) nunca pode ser tratada como análise real. Em tarefas críticas (`qa_report_analysis`, `qa_failure_diagnosis`, `release_gate_review`, `visual_qa_analysis`), `fallback_used: true` deve resultar em `status: "warning"` ou `"blocked"` e `confidence` baixo, nunca em `can_advance: true`.

## Decisão 031 — `can_advance` é recomendação assistida, não autorização automática

A decisão de avançar uma frente de trabalho (ex.: para release) permanece sempre humana. O campo `can_advance` de QA Intelligence é uma sugestão baseada em evidências analisadas, nunca uma aprovação vinculante ou uma ação de release disparada automaticamente.

## Decisão 032 — Análise visual/exploratória deve ser planejada separadamente antes de qualquer automação

`visual_qa_analysis` e qualquer exploração visual autônoma (navegação, cliques, ações automáticas) dependem de uma fase própria de planejamento, posterior à maturação da base textual/estruturada de QA Intelligence. Nenhuma automação visual é implementada ou planejada em detalhe nesta etapa.

## Decisão 033 — QA Intelligence não pode alterar projetos externos nem aplicar correções automaticamente

QA Intelligence nunca altera arquivos, nunca faz commit, nunca aplica `suggested_fixes` automaticamente e nunca executa `suggested_commands`. Toda ação corretiva permanece de responsabilidade do sistema de origem ou de um humano.

## Decisão 034 — PEDROCORE-REPLAN-01 fecha apenas documentação e arquitetura, não implementação

O fechamento da frente `PEDROCORE-REPLAN-01` (etapa `01E`) consolida visão, contratos, arquitetura-alvo e planejamento de QA Intelligence em documentação. Nenhum código foi implementado durante toda a frente; a implementação é escopo de uma fase futura e separada.

## Decisão 035 — Documentação legada/duplicada não será removida sem frente específica de saneamento

Documentos antigos e duplicados identificados em `docs/` (ex.: pares `0X_NOME.md`/`0X-nome/`) permanecem no repositório após o fechamento de `PEDROCORE-REPLAN-01`. A remoção/consolidação desses documentos exige uma frente própria de saneamento documental, não incluída no escopo desta reformulação.

## Decisão 036 — Primeira implementação pós-replan deve preservar compatibilidade de `/api/chat`

Qualquer implementação futura decorrente desta reformulação (ex.: `PEDROCORE-IMPLEMENT-01`) deve manter `POST /api/chat` funcionando exatamente como hoje, sem exigir mudança no frontend existente.

## Decisão 037 — Implementação de Task Router deve ser incremental e testável com Mock antes de provider real

Ao implementar o Task Router, a primeira versão deve ser validável com `MockProvider`, permitindo testar o roteamento por `task_type` sem custo ou risco de chamada real, antes de habilitar providers reais nesse fluxo.

## Decisão 038 — Integração real com sistemas externos só deve ocorrer após contratos, autenticação e audit/log mínimos

Nenhuma integração real (ex.: recebendo chamadas do FinGuard) deve ser habilitada antes de existirem, no mínimo: o contrato de orquestração implementado, um mecanismo de autenticação entre sistemas e um audit/log básico registrando as chamadas.

## Decisão 039 — Task Router inicial deve começar como camada interna do /api/chat antes de novo endpoint público

A primeira implementação do Task Router deve operar dentro do fluxo já existente de `POST /api/chat`, preservando compatibilidade com clientes atuais e permitindo validação segura com Mock antes da criação de qualquer endpoint novo de orquestração.

## Decisão 040 — Warnings de fallback crítico devem ser expostos na resposta antes de qualquer bloqueio automático

Na primeira implementação, o fallback Mock em tarefa crítica não bloqueia a resposta — apenas adiciona um warning explícito em `task_warnings`. Bloqueio automático (ex.: `status: "blocked"`) é uma evolução futura, a ser decidida somente depois que sistemas externos reais consumirem e validarem esses warnings.
