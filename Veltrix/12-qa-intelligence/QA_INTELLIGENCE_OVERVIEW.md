# QA Intelligence — Visão Geral

> Nota DOCFIX: este documento nasceu como planejamento da frente `PEDROCORE-REPLAN-01D`. Em `v7.0.0`, o Veltrix já possui QA textual local determinístico, `POST /api/orchestrate`, `qa`, `release_gate`, `visual_qa_analysis` stub e `exploration` assistido/manual. QA com IA real, QA visual real e automação autônoma continuam fora do padrão. Use [[../00_MAPEAMENTO_GERAL_PEDROCORE]] como estado atual.

## 1. Definição de QA Intelligence

QA Intelligence é uma camada futura do Veltrix para:

- Interpretar relatórios de QA recebidos de sistemas externos.
- Analisar falhas relatadas em evidências/artefatos.
- Classificar risco (`risk_level`) das falhas e observações.
- Sugerir próximos comandos de investigação (nunca executá-los).
- Explicar causas prováveis de uma falha.
- Avaliar, de forma assistida, se uma frente de trabalho pode avançar (`can_advance`).
- Apoiar análise textual/exploratória de evidências e, de forma futura/opt-in, análise visual real de screenshots/gravações.
- Padronizar o diagnóstico técnico devolvido a sistemas externos, em formato estruturado e consumível por máquina.

**Estado atual:** a camada existe como heurística textual local determinística (`apps/api/app/modules/qa_analysis/`) e release gate conservador (`apps/api/app/modules/qa_response/`). Ela não chama provider real, não executa testes, não lê o FinGuard e não substitui revisão humana.

## 2. Relação com o QA Automation do FinGuard

- O FinGuard é um projeto externo e independente.
- O QA Automation pertence ao FinGuard e já valida, dentro do próprio FinGuard: API, backend, frontend, rotas, banco de teste, Prisma, Playwright, smoke tests, E2E, relatórios e evidências.
- O lado Veltrix implementa exploração assistida/manual como plano/checklist (`exploration`), sem execução autônoma.
- O Veltrix **não executa** o QA do FinGuard.
- O Veltrix **não roda testes** do FinGuard.
- O Veltrix **não roda migrations** do FinGuard.
- O Veltrix **não roda seed/reset** do FinGuard.
- O Veltrix **não comita** no FinGuard.
- O Veltrix **não altera arquivos** do FinGuard.
- O Veltrix pode receber artefatos do FinGuard como payload textual controlado — nunca por acesso direto ao repositório ou à infraestrutura do FinGuard.

**QA Intelligence não é o QA Automation.** QA Intelligence não executa testes e não substitui Playwright, smoke tests, banco de teste, Prisma, migrations, seed/reset ou scripts do FinGuard — ela analisa artefatos **já produzidos** por esses processos e devolve um diagnóstico estruturado.

## 3. Artefatos que QA Intelligence poderá analisar futuramente

Todos os tipos abaixo nasceram como planejamento. No estado atual, a análise padrão ocorre com conteúdo enviado no payload; o Artifact Reader existe como opt-in allowlisted, default-off e bloqueado para FinGuard.

| Tipo | Finalidade | Formato esperado | Riscos | Texto ou visual | Exige provider multimodal | Payload nesta fase | Leitura automática |
|---|---|---|---|---|---|---|---|
| `qa_report` | Relatório de QA consolidado | Markdown livre (ver seção 4) | Pode conter dados de ambiente de teste | Texto | Não | Sim | Não existe |
| `markdown` | Documento genérico em Markdown | Texto livre | Pode conter qualquer conteúdo, inclusive dados sensíveis do autor | Texto | Não | Sim | Não existe |
| `terminal_output` | Saída de comandos/scripts de teste | Texto plano | Pode conter caminhos, variáveis de ambiente expostas em erro | Texto | Não | Sim | Não existe |
| `log` | Log de execução de aplicação/testes | Texto plano, possivelmente extenso | Pode conter tokens, dados de usuário | Texto | Não | Sim | Não existe |
| `json_result` | Resultado estruturado de execução (ex.: relatório de test runner) | JSON válido | Deve ser validado antes do uso; formato pode variar por ferramenta | Texto | Não | Sim | Não existe |
| `screenshot` | Captura de tela de uma execução ou estado da UI | Imagem (formato a definir) | Pode expor dados financeiros reais ou PII, especialmente em produtos como o FinGuard | Visual | Sim (fase futura) | Não definido nesta fase | Não existe |
| `image` | Imagem genérica de evidência | Imagem (formato a definir) | Mesmo risco de `screenshot` | Visual | Sim (fase futura) | Não definido nesta fase | Não existe |
| `playwright_trace` | Trace de execução do Playwright | Formato proprietário do Playwright (binário/zip) | Pode conter dados de sessão, requests, respostas de API real | Misto (visual + dados) | Sim, para interpretação visual | Não definido nesta fase | Não existe |
| `documentation` | Documentação de apoio (ex.: guia técnico) | Texto/Markdown | Baixo, geralmente | Texto | Não | Sim | Não existe |
| `roadmap_doc` | Roadmap ou plano técnico do sistema externo | Markdown | Baixo | Texto | Não | Sim | Não existe |
| `changelog` | Changelog do sistema externo | Markdown | Baixo | Texto | Não | Sim | Não existe |
| `pending_list` | Lista de pendências/itens em aberto | Texto/Markdown livre | Baixo | Texto | Não | Sim | Não existe |

## 4. Relatórios QA Markdown (planejamento específico)

Os relatórios de QA atuais do FinGuard são **Markdown livre**, não JSON estruturado. Planejamento inicial:

- O Veltrix deve aceitar conteúdo Markdown enviado no payload (`artifacts[].content`), como já especificado em `docs/10-contratos/CONTRATO_ORQUESTRACAO.md`.
- O Veltrix deve extrair informações por **interpretação textual** (o provider de IA interpretando o texto), não por um parser rígido de seções fixas.
- O Veltrix **não deve depender inicialmente de JSON estruturado** vindo do FinGuard.
- JSON estruturado do lado do FinGuard **pode ser uma evolução futura**, mas não é pré-requisito para o planejamento desta fase.
- Qualquer parser/interpretação futura deve ser **tolerante a variação de texto** — títulos, ordens de seção e nível de detalhe podem mudar entre relatórios.
- **Se o relatório estiver incompleto**, a resposta estruturada de QA Intelligence deve indicar **baixa confiança** (`confidence` baixo) em vez de tentar preencher lacunas com suposições.

## 5. Casos de uso

Ver documentos dedicados por caso de uso:

- [`QA_REPORT_ANALYSIS.md`](./QA_REPORT_ANALYSIS.md) — `qa_report_analysis`.
- [`QA_FAILURE_DIAGNOSIS.md`](./QA_FAILURE_DIAGNOSIS.md) — `qa_failure_diagnosis`.
- [`QA_RELEASE_GATE.md`](./QA_RELEASE_GATE.md) — `release_gate_review`, incluindo a regra de avanço/bloqueio (`can_advance`).

Os demais casos de uso (`visual_qa_analysis`, `artifact_summary`, `regression_risk_review`, `test_gap_analysis`, `next_commands_suggestion`) estão descritos na tabela abaixo, por serem variações do mesmo princípio de "analisar e diagnosticar, nunca executar".

| Caso de uso | Objetivo | Entrada esperada | Saída esperada | Resposta estruturada obrigatória | Mock permitido | Fallback Mock bloqueia conclusão | Observação de segurança |
|---|---|---|---|---|---|---|---|
| `visual_qa_analysis` | Registrar evidência visual (screenshot/trace) de possível regressão | `message` + `artifacts` do tipo `screenshot`/`image`/`playwright_trace` | Stub conservador com revisão humana | Sim | Apenas para teste de integração | Sim, em uso crítico | QA visual real exige provider multimodal em frente futura/opt-in; hoje há stub |
| `artifact_summary` | Resumir um artefato sem análise crítica aprofundada | `message` + `artifacts` | Texto livre ou resumo estruturado simples | Não (recomendado) | Sim, livremente | Não é crítico por padrão | Uso geral, menor risco |
| `regression_risk_review` | Avaliar risco de regressão a partir de mudanças/evidências | `message` + `artifacts` (diff, changelog, relatório) + `context` | Resposta estruturada com `risk_level` | Sim | Apenas para teste | Sim, em avaliação real | Não substitui análise de QA automatizado do FinGuard |
| `test_gap_analysis` | Identificar lacunas de cobertura de teste a partir de relatórios/roadmap | `message` + `artifacts` (relatório, roadmap) | Resposta estruturada ou lista de lacunas | Recomendado | Sim | Não necessariamente crítico | Diagnóstico, não implementação de testes |
| `next_commands_suggestion` | Sugerir próximos comandos de investigação a partir de uma falha | `message` + `artifacts` (log, relatório) | Lista de `suggested_commands` (texto, nunca executado) | Recomendado | Sim, para teste | Não crítico isoladamente | Veltrix nunca executa os comandos sugeridos |

## 6. Resposta estruturada de QA (planejada)

```json
{
  "status": "pass|warning|fail|blocked",
  "summary": "...",
  "findings": [],
  "failures": [],
  "probable_causes": [],
  "suggested_commands": [],
  "suggested_fixes": [],
  "risk_level": "low|medium|high|critical",
  "can_advance": true,
  "confidence": 0.85,
  "fallback_used": false,
  "warnings": []
}
```

### Explicação dos campos

- **`status`** — resultado geral da análise: `pass` (nenhum problema relevante), `warning` (pontos de atenção não bloqueantes), `fail` (falha relevante identificada), `blocked` (análise não pôde ser concluída, ex.: artefato insuficiente ou fallback em tarefa crítica).
- **`summary`** — resumo textual curto da análise, para leitura humana rápida.
- **`findings`** — lista de observações gerais encontradas na análise (não necessariamente falhas).
- **`failures`** — lista específica de falhas identificadas nos artefatos analisados.
- **`probable_causes`** — hipóteses de causa raiz das falhas, como diagnóstico, não como certeza absoluta.
- **`suggested_commands`** — lista de comandos que poderiam ser executados por um humano ou pelo QA Automation do FinGuard para investigar mais. **Nunca são executados pelo Veltrix.**
- **`suggested_fixes`** — lista de sugestões textuais de correção. **Nunca são aplicadas automaticamente pelo Veltrix.**
- **`risk_level`** — nível de risco percebido (`low`, `medium`, `high`, `critical`), ver critérios na seção 7.
- **`can_advance`** — sugestão de que a frente avaliada poderia avançar (ex.: para release). **Recomendação assistida, nunca autorização automática** (ver seção 8).
- **`confidence`** — grau de confiança do Veltrix na análise (0 a 1), refletindo qualidade dos artefatos recebidos e se houve fallback.
- **`fallback_used`** — indica se a resposta foi gerada via `MockProvider` em vez de um provider real (ver seção 9).
- **`warnings`** — lista de alertas explícitos (ex.: "análise gerada via fallback, não usar como validação real").

### Diferenciação importante

- `suggested_commands` **não são comandos executados** — são apenas texto sugerido para um humano ou para o QA Automation do FinGuard rodar, se desejarem.
- `suggested_fixes` **não são correções aplicadas** — são apenas texto sugerido; nenhuma mudança de código ou configuração é feita pelo Veltrix.
- `can_advance` **é uma decisão assistida, não uma autorização automática** — a decisão final de avançar ou não permanece sempre com um humano ou com o processo de release do sistema de origem.

## 7. Severidade e risco (`risk_level`)

Critérios conceituais para classificação de risco:

- **`low`** — falha menor, documentação incompleta, alerta sem impacto funcional grave.
- **`medium`** — teste parcialmente quebrado, comportamento inconsistente, falha em fluxo não crítico.
- **`high`** — falha em login, API principal, banco de teste, dashboard financeiro, autenticação ou rota crítica.
- **`critical`** — risco de banco errado (ex.: ambiente de teste apontando para banco de produção), risco de exposição de dados reais, falha de segurança, evidência de alteração indevida, quebra total do QA, ou provider real usado indevidamente (ex.: chamada a um provider real quando deveria ser Mock, ou vice-versa em contexto sensível).

## 8. Regra de avanço/bloqueio (`can_advance`)

- **`can_advance: true`** — quando os testes principais passam, as falhas identificadas são não bloqueantes e as evidências analisadas são suficientes para uma recomendação com confiança razoável.
- **`can_advance: false`** — quando há falha crítica, o relatório está incompleto, houve fallback para Mock em tarefa crítica, a evidência é insuficiente, há risco de banco/dados/segurança, ou um teste essencial falhou.

**O Veltrix não decide sozinho.** `can_advance` é sempre uma recomendação. **O Veltrix recomenda; o usuário/desenvolvedor aprova.** Nenhuma ação de release, merge ou deploy é disparada automaticamente a partir dessa resposta.

## 9. Fallback Mock em QA (regra forte)

- O `MockProvider` pode ser útil em desenvolvimento e para simular o formato da resposta estruturada.
- O `MockProvider` **não pode validar um relatório real de QA** — uma resposta gerada por Mock não é uma análise real.
- O `MockProvider` **não pode liberar um release gate** — `can_advance: true` nunca deve vir de uma resposta com `fallback_used: true` em tarefa crítica.
- Se `fallback_used = true` em uma tarefa crítica (`qa_report_analysis`, `qa_failure_diagnosis`, `release_gate_review`, `visual_qa_analysis`), a resposta deve indicar `status: "warning"` ou `status: "blocked"`, nunca `pass` ou `fail` como se fossem conclusivos.
- Sistemas externos devem tratar `fallback_used: true` como **sinal de baixa confiabilidade** e não como um resultado equivalente a uma análise feita por provider real.

## 10. Análise visual/exploratória futura

- `visual_qa_analysis` existe hoje como stub conservador para `screenshot`, `image`, `pdf` e `playwright_trace`.
- **Não existe análise visual real automática** nesta versão; o stub exige revisão humana e nunca libera release gate sozinho.
- Essa capacidade pode exigir um **provider multimodal** — nenhum provider atual do Veltrix (Mock, Gemini, OpenAI, Claude, DeepSeek, Grok) está configurado ou testado para esse uso nesta fase.
- QA Intelligence **não deve navegar no sistema sozinha** no fluxo padrão — Playwright é opt-in, read-only e bloqueia ações interativas.
- QA Intelligence **não deve clicar, editar ou executar ações automaticamente** sem uma fase própria e dedicada de planejamento para isso.
- Exploração visual autônoma (ex.: um agente que navega e testa por conta própria) deve ser **planejada separadamente**, depois que a base textual/estruturada (relatórios, logs, diagnóstico) estiver madura.

## 11. Limites e proibições

QA Intelligence, em toda a sua concepção planejada, **não deve**:

- Executar testes.
- Rodar scripts.
- Alterar arquivos (de qualquer projeto, incluindo o FinGuard).
- Modificar o FinGuard de qualquer forma.
- Mexer em banco de dados (do Veltrix ou de qualquer sistema externo).
- Rodar Prisma.
- Rodar migrations.
- Rodar seed/reset.
- Fazer commit (em nenhum repositório).
- Aplicar correções automaticamente.
- Calcular números financeiros oficiais.
- Substituir a revisão humana na decisão final.
- Mascarar uma falha crítica com uma resposta "bonita" (bem escrita, mas que esconda ou minimize um problema real) — em caso de dúvida, a resposta deve pender para `warning`/`blocked` e `risk_level` mais alto, nunca para uma resposta artificialmente tranquilizadora.

## 12. Relação com a arquitetura-alvo (01C)

QA Intelligence é um caso de uso que consumiria os módulos já documentados em `docs/11-arquitetura-alvo/`:

- **Task Router** identificaria o `task_type` de QA (`qa_report_analysis`, `qa_failure_diagnosis`, `release_gate_review`, `visual_qa_analysis`, etc.) e decidiria a estratégia (Mock permitido ou não, resposta estruturada obrigatória).
- **Project Context** aplicaria os limites do projeto externo (ex.: FinGuard: `read_only: true`, `can_execute_commands: false`, `can_write_files: false`, `allowed_tasks` incluindo as tarefas de QA).
- **Artifact Reader** opt-in pode ler artefatos allowlisted em modo somente leitura, mas nunca para FinGuard; o padrão continua payload.
- **Prompt Builder** montaria um prompt especializado de QA, combinando o artefato, o contexto do projeto e o schema de resposta estruturada esperado.
- **Provider Orchestration** escolheria um provider adequado (real, para análises confiáveis; Mock apenas para teste).
- **Structured Responses** validaria que a resposta segue o schema de QA descrito na seção 6.
- **Audit/logs** registraria a análise realizada (origem, tarefa, provider, fallback, criticidade), sem armazenar dados sensíveis do conteúdo analisado.

**Estado atual:** Task Router, Project Context, Prompt Builder, Artifact Service, Artifact Reader opt-in, QA Analysis, QA Response, Orchestration e Audit já existem em código. Provider Orchestration avançada, logs persistentes e QA visual real continuam opcionais/futuros.

## Links relacionados

- [[../MOC_QA_RELEASE_GATE]]
- [[../MOC_QA_SAFETY_HARDENING]]
- [[../16-qa-safety-hardening/QA_SAFETY_HARDENING_PLAN]]
- [[../16-qa-safety-hardening/FECHAMENTO_PEDROCORE_QA_SAFETY_HARDENING_01]]
