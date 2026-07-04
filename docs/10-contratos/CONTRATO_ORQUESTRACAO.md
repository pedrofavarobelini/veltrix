# Contrato de Orquestração (Planejado)

> Parte da frente `PEDROCORE-REPLAN-01B`. Este documento especifica o contrato **futuro** de entrada e saída para sistemas externos consumirem o PedroCore IA como orquestrador central. Nada aqui está implementado: não existe endpoint novo, schema Pydantic, service ou roteador de tarefa no código hoje. O único contrato que existe de fato hoje é o descrito na seção "Contrato atual", para referência e contraste.

## Contrato atual (referência — já implementado)

Hoje, `POST /api/chat` aceita:

```json
{
  "message": "texto livre",
  "mode": "tecnico",
  "provider": "mock",
  "model": null,
  "system_prompt": null
}
```

E devolve:

```json
{
  "answer": "texto livre",
  "provider": "mock",
  "model": "mock-v1",
  "mode": "tecnico",
  "requested_provider": "mock",
  "fallback_used": false,
  "error": null
}
```

Isso continua funcionando sem alteração. O contrato de orquestração abaixo é um **novo contrato planejado**, que coexistiria (futuramente) com o atual, não o substitui nesta fase.

---

## 1. Contrato geral de orquestração (planejado)

Exemplo conceitual de requisição futura de um sistema externo para o PedroCore:

```json
{
  "origin_system": "finguard",
  "source": "qa-automation",
  "task_type": "qa_report_analysis",
  "message": "Analise este relatório de QA",
  "context": {
    "project": "FinGuard",
    "environment": "test",
    "module": "personal-finance",
    "route": "/dashboard/pessoal"
  },
  "artifacts": [
    {
      "type": "markdown",
      "name": "qa-report-2026-07-04.md",
      "content": "...texto do relatório..."
    }
  ],
  "provider_preference": "auto",
  "response_format": "structured"
}
```

**Importante:** este é um contrato planejado. Não existe ainda no código do PedroCore. Nenhum endpoint aceita este payload hoje.

## 2. Campos obrigatórios e opcionais

### Obrigatórios

| Campo | Função |
|---|---|
| `origin_system` | Identifica qual sistema do ecossistema Pedro está chamando (ex.: `finguard`, `pedrocore-web`). Necessário para roteamento, auditoria futura e para aplicar regras específicas de contexto/segurança por sistema. |
| `task_type` | Identifica o tipo de tarefa solicitada (ver seção 3). Determina qual estratégia de resposta, qual nível de rigor e se a tarefa é crítica ou não. |
| `message` | Texto da solicitação em si — a pergunta, o pedido de análise ou a instrução principal. |

### Opcionais

| Campo | Função |
|---|---|
| `source` | Subsistema ou módulo específico dentro do `origin_system` (ex.: `qa-automation` dentro do FinGuard). Ajuda a refinar o contexto sem exigir um novo `origin_system`. |
| `context` | Objeto livre com informações do projeto/ambiente/módulo/rota relevantes para a tarefa (ex.: `project`, `environment`, `module`, `route`). Usado pelo futuro Project Context. |
| `artifacts` | Lista de artefatos anexados à solicitação (ver contrato de artefatos, seção 6). |
| `provider_preference` | Preferência de provider/estratégia de roteamento (ver seção 7). |
| `model_preference` | Preferência de modelo específico dentro do provider escolhido, quando aplicável. |
| `response_format` | Indica se a resposta esperada é `"free_text"` (texto livre) ou `"structured"` (resposta estruturada, ver seção 4/5). |
| `priority` | Prioridade da solicitação (ex.: `low`, `normal`, `high`), para uso futuro em filas ou roteamento diferenciado — não implementado. |
| `metadata` | Campo livre para informações adicionais que o sistema de origem queira anexar, sem impacto na lógica de roteamento nesta fase. |

## 3. Tipos de tarefa planejados (`task_type`)

Todos os `task_type` abaixo são **planejados**, para orientar o desenho futuro do Task Router (`PEDROCORE-REPLAN-01C`). Nenhum está implementado.

### `general_chat`
- **Finalidade:** conversa geral, equivalente ao uso atual do chat.
- **Entrada esperada:** `message` livre, sem necessidade de `context` ou `artifacts`.
- **Saída esperada:** texto livre.
- **Pode usar Mock:** sim, sem restrição.
- **Exige provider real:** não.
- **Formato de resposta:** livre.

### `technical_explanation`
- **Finalidade:** explicar conceito técnico, código ou decisão de arquitetura.
- **Entrada esperada:** `message` descrevendo o que precisa ser explicado; `context` opcional para situar o domínio.
- **Saída esperada:** texto livre, podendo incluir trechos de código ilustrativos.
- **Pode usar Mock:** sim, para testes/desenvolvimento.
- **Exige provider real:** não, mas a qualidade da explicação depende de provider real em uso de produção.
- **Formato de resposta:** livre.

### `code_help`
- **Finalidade:** apoio a dúvidas ou sugestões relacionadas a código.
- **Entrada esperada:** `message` com a dúvida; `artifacts` opcionais (ex.: trecho de código como `type: "json"` ou texto simples).
- **Saída esperada:** texto livre com explicação e/ou sugestão de código.
- **Pode usar Mock:** sim, para testes/desenvolvimento.
- **Exige provider real:** não, mas recomendável para uso real.
- **Formato de resposta:** livre.

### `project_context_answer`
- **Finalidade:** responder considerando o contexto de um projeto específico do ecossistema (ex.: dúvida sobre o FinGuard usando `context.project`).
- **Entrada esperada:** `message` + `context` preenchido (`project`, `module`, etc.).
- **Saída esperada:** texto livre, contextualizado.
- **Pode usar Mock:** sim, para testes.
- **Exige provider real:** recomendado para respostas confiáveis, não obrigatório tecnicamente.
- **Formato de resposta:** livre.

### `qa_report_analysis`
- **Finalidade:** analisar um relatório de QA (ex.: relatório Markdown de QA Automation do FinGuard) e resumir achados.
- **Entrada esperada:** `message` + `artifacts` (relatório em `type: "markdown"` ou `"qa_report"`) + `context` do projeto/ambiente.
- **Saída esperada:** resposta estruturada (ver `CONTRATO_QA_INTELLIGENCE.md`).
- **Pode usar Mock:** apenas para teste de integração/desenvolvimento, nunca para uma análise real considerada válida.
- **Exige provider real:** sim, para qualquer análise que será tratada como confiável (Decisão Técnica 020).
- **Formato de resposta:** estruturada (obrigatório).

### `qa_failure_diagnosis`
- **Finalidade:** diagnosticar prováveis causas de uma falha reportada em QA.
- **Entrada esperada:** `message` descrevendo a falha + `artifacts` (log, saída de terminal, relatório) + `context`.
- **Saída esperada:** resposta estruturada com `probable_causes` e `suggested_commands` (apenas sugestão, nunca execução — ver seção 5).
- **Pode usar Mock:** apenas para teste, nunca como diagnóstico real.
- **Exige provider real:** sim, para diagnóstico confiável.
- **Formato de resposta:** estruturada (obrigatório).

### `visual_qa_analysis`
- **Finalidade:** análise exploratória/visual de QA (ex.: screenshot de tela com possível regressão visual). Caso de uso central da futura QA Intelligence (`QA-AUTOMATION-01G`).
- **Entrada esperada:** `message` + `artifacts` do tipo `screenshot`/`image` + `context`.
- **Saída esperada:** resposta estruturada descrevendo observações visuais, nunca um veredito automático definitivo.
- **Pode usar Mock:** apenas para teste de integração.
- **Exige provider real:** sim, e um provider com suporte a análise de imagem (a definir em fase futura).
- **Formato de resposta:** estruturada (obrigatório).

### `log_analysis`
- **Finalidade:** analisar logs de execução (ex.: logs de teste ou de erro de aplicação).
- **Entrada esperada:** `message` + `artifacts` do tipo `log` ou `terminal_output`.
- **Saída esperada:** resposta estruturada com resumo e possíveis causas.
- **Pode usar Mock:** apenas para teste.
- **Exige provider real:** sim, para análise confiável.
- **Formato de resposta:** estruturada (recomendado).

### `roadmap_review`
- **Finalidade:** revisar/comentar um roadmap ou plano técnico de um projeto do ecossistema.
- **Entrada esperada:** `message` + `artifacts` (documento Markdown do roadmap) + `context`.
- **Saída esperada:** texto livre ou estruturado, a critério do sistema de origem.
- **Pode usar Mock:** sim, para testes.
- **Exige provider real:** recomendado para uso real.
- **Formato de resposta:** livre ou estruturada.

### `release_gate_review`
- **Finalidade:** apoiar a decisão de "pode avançar para release" com base em evidências de QA — **apoio à decisão, nunca decisão automática**.
- **Entrada esperada:** `message` + `artifacts` (relatórios de QA, resultados de smoke/E2E) + `context`.
- **Saída esperada:** resposta estruturada com `can_advance` como **sugestão**, nunca como aprovação automática vinculante.
- **Pode usar Mock:** apenas para teste, nunca para uma decisão real de release.
- **Exige provider real:** sim, obrigatoriamente, dado o caráter crítico da tarefa.
- **Formato de resposta:** estruturada (obrigatório).

### `artifact_summary`
- **Finalidade:** resumir um artefato (documento, log, relatório) sem análise crítica aprofundada.
- **Entrada esperada:** `message` + `artifacts`.
- **Saída esperada:** texto livre ou estruturado simples (resumo).
- **Pode usar Mock:** sim, para testes.
- **Exige provider real:** recomendado para resumo de qualidade em produção.
- **Formato de resposta:** livre ou estruturada, a critério do sistema de origem.

## 4. Resposta padronizada (planejada)

Formato base de resposta para qualquer `task_type`, quando o novo contrato existir:

```json
{
  "success": true,
  "task_type": "qa_report_analysis",
  "origin_system": "finguard",
  "answer": "...",
  "provider": "gemini",
  "model": "gemini-...",
  "fallback_used": false,
  "response_type": "structured",
  "warnings": [],
  "error": null,
  "metadata": {
    "confidence": 0.82,
    "risk_level": "medium"
  }
}
```

Campos herdam o espírito do contrato atual (`provider`, `model`, `fallback_used`, `error`) e adicionam: `success` (booleano simples de sucesso/falha), `task_type`/`origin_system` (para rastreabilidade), `response_type` (`"free_text"` ou `"structured"`), `warnings` (lista de alertas, ex.: fallback em tarefa crítica) e `metadata` livre (ex.: `confidence`, `risk_level`).

A resposta estruturada específica de QA está detalhada em `CONTRATO_QA_INTELLIGENCE.md`.

## 5. (ver documento de QA Intelligence)

A resposta estruturada específica para análise de QA (`status`, `risk_level`, `can_advance`, `confidence`, `suggested_commands`, etc.) está documentada em [`CONTRATO_QA_INTELLIGENCE.md`](./CONTRATO_QA_INTELLIGENCE.md), por ser um caso de uso mais específico e sensível.

## 6. Contrato de artefatos (planejado)

Tipos de `artifact.type` planejados:

| Tipo | Como é recebido | Texto ou arquivo | Pode conter dado sensível | Restrição de tamanho | Observação de segurança |
|---|---|---|---|---|---|
| `markdown` | Conteúdo textual no campo `content` do payload | Texto | Sim, se o documento de origem contiver dados sensíveis | A definir (limite de payload HTTP padrão nesta fase) | Não deve ser tratado como confiável sem contexto (`context`) — é texto livre, pode conter qualquer formatação |
| `log` | Conteúdo textual no `content` | Texto | Sim (pode conter tokens, caminhos internos, dados de usuário) | A definir | Sistema de origem é responsável por sanitizar segredos antes de enviar |
| `json` | Conteúdo textual (string JSON) no `content` | Texto | Depende do conteúdo | A definir | Deve ser validado como JSON válido antes do processamento (validação futura) |
| `screenshot` / `image` | Planejado como referência ou base64 — formato exato a definir em fase futura | Arquivo/binário | Pode conter dados de tela sensíveis (dados financeiros, PII) | A definir, provavelmente mais restritivo que texto | Exige cuidado extra: imagens de produtos como o FinGuard podem expor dados financeiros reais |
| `terminal_output` | Conteúdo textual no `content` | Texto | Sim (pode conter caminhos, variáveis de ambiente expostas em erro) | A definir | Sistema de origem deve evitar enviar saída de terminal com segredos |
| `documentation` | Conteúdo textual no `content` | Texto | Baixo, geralmente | A definir | Uso geral, menor risco |
| `qa_report` | Conteúdo textual no `content`, tipicamente Markdown livre | Texto | Pode conter dados de ambiente de teste | A definir | Ver observação específica abaixo sobre relatórios do FinGuard |

### Regras desta fase (obrigatórias)

- O PedroCore **ainda não lê arquivos externos automaticamente**. Nenhum caminho de pasta ou repositório é acessado.
- O consumo inicial planejado é **exclusivamente por conteúdo enviado no payload** (`artifact.content`), nunca por referência a caminho de arquivo em disco de outro projeto.
- Integração real com caminho/pasta de outros projetos (ex.: ler `qa/reports/` do FinGuard diretamente do disco) é **fase futura**, fora do escopo de `PEDROCORE-REPLAN-01B`.
- Relatórios de QA do FinGuard hoje são **Markdown livre, não JSON estruturado** — qualquer parser futuro para `qa_report`/`markdown` deve ser tolerante a variações de formatação, não pode assumir um schema rígido.

## 7. Provider preference e roteamento (planejado)

Valores planejados para `provider_preference`:

- `auto` — permite que o futuro Task Router escolha o provider mais adequado à tarefa (ainda não implementado; hoje não há Task Router).
- `mock` — força o uso do `MockProvider`. Adequado para tarefas simples, testes e desenvolvimento.
- `gemini`, `openai`, `claude`, `deepseek`, `grok` — força um provider real específico (sujeito à disponibilidade de chave configurada).

### Regras

- `auto` deve, no futuro, permitir escolha automática pelo Task Router com base no `task_type` e em critérios ainda a definir (custo, latência, capacidade exigida).
- `mock` pode ser usado livremente em tarefas simples (`general_chat`, testes, desenvolvimento).
- `mock` **não deve validar tarefas críticas de QA silenciosamente** — ou seja, para `task_type` como `qa_report_analysis`, `qa_failure_diagnosis` e `release_gate_review`, uma resposta via Mock nunca pode ser apresentada como uma análise real sem aviso explícito.
- Providers reais exigem chave configurada **e**, no desenho técnico futuro, um controle explícito adicional (ex.: flag de ambiente ou confirmação) para reduzir risco de chamada acidental (Decisão Técnica 013).
- Se `fallback_used = true` em uma tarefa crítica, a resposta **não deve ser tratada como validação confiável** pelo sistema de origem — deve ser tratada como indisponibilidade, não como aprovação/reprovação real.

## 8. Regras de fallback (planejado, à luz do comportamento atual)

- O fallback atual (implementado hoje em `ChatService`) existe e cai automaticamente para `MockProvider` quando um provider real falha ou não está configurado.
- Isso é bom para a experiência de chat conversacional — evita quebrar a interface com erro bruto.
- **Mas é perigoso para tarefas críticas.** Se aplicado sem aviso a `qa_report_analysis`, `qa_failure_diagnosis` ou `release_gate_review`, pode fazer o sistema de origem interpretar uma resposta simulada como uma análise real.
- Regras planejadas para tarefas críticas:
  - A resposta deve indicar claramente `fallback_used: true` e um `warning` explícito no array `warnings`.
  - Para essas tarefas, um fallback para Mock deve gerar **warning forte** e, dependendo do desenho futuro, pode **bloquear a conclusão** da tarefa em vez de devolver uma resposta simulada como se fosse válida.
  - Essa distinção entre "fallback aceitável" (chat geral) e "fallback perigoso" (tarefa crítica) é uma decisão de arquitetura a ser refinada em `PEDROCORE-REPLAN-01C`/`01D`, mas o princípio já está fixado aqui e na Decisão Técnica 020.

## 9. Relação com o FinGuard (reforço)

- O FinGuard é projeto externo e independente.
- O PedroCore não altera o FinGuard, não roda o QA Automation do FinGuard, não roda migrations do FinGuard, não roda seed/reset do FinGuard e não comita no FinGuard.
- O PedroCore poderá, no futuro, receber relatórios de QA do FinGuard como `artifacts` (payload), nunca por acesso direto ao repositório do FinGuard.
- O QA Automation do FinGuard continua pertencendo ao FinGuard; apenas `QA-AUTOMATION-01G` (agente exploratório assistido por IA) foi delegado ao PedroCore como caso de uso futuro — ver `CONTRATO_QA_INTELLIGENCE.md`.
- O PedroCore não calcula números financeiros oficiais do FinGuard.
