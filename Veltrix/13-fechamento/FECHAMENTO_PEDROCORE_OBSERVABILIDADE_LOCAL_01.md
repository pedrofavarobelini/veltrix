# FECHAMENTO PEDROCORE OBSERVABILIDADE LOCAL 01

Data: 2026-07-18

## Veredito

**Observabilidade visual técnica do Veltrix implementada e testada localmente.** A frente instrumenta o pipeline real, preserva o safe mode e não transforma memória/avaliação em alegação de treinamento.

Este fechamento é local/QA. Não equivale a homologação de provider real, operação pública, treinamento de modelo ou prontidão de produção.

## Commits da frente

- `b22338a` — store sanitizado e instrumentação de provider, fallback, memória e avaliação;
- `df6d72f` — interface visual técnica de execuções;
- `f995d5e` — smoke Gemini real opt-in, timeout e fallback;
- `3b11b36` — CORS local, falha total QA e replay FinGuard → Veltrix.

Base auditada: `15182b1a977ade2497c2304e5731c6760def5019`.

## Arquitetura implementada

### Store

- ring buffer em memória, sem persistência em banco/arquivo;
- `PEDROCORE_OBSERVABILITY_ENABLED=false` por padrão;
- habilitação somente nos ambientes `dev`, `development`, `local`, `qa`, `test` e `testing`;
- bloqueio explícito em `prod`/`production`;
- limite configurável por `PEDROCORE_OBSERVABILITY_MAX_ENTRIES` (default 200, mínimo 10, máximo 1.000);
- acesso HTTP somente por loopback e somente quando o modo está habilitado;
- sanitização central antes da retenção.

Cada execução pode mostrar:

- `execution_id`, `audit_id`, timestamp, origem, task, status e duração;
- payload sanitizado e nomes dos campos removidos;
- provider solicitado, selecionado e efetivo;
- tentativas, timeout, erro sanitizado, fallback e timeline;
- resposta pública devolvida;
- QA, release gate, avaliação, sinais e recomendação;
- memória técnica consultada e memória criada.

Nunca deve reter API key, Authorization, cookie, token, senha, `.env`, ciphertext desnecessário, payload financeiro bruto ou prompt com segredo.

### Endpoints locais

- `GET /api/observability/status`;
- `GET /api/observability/executions`;
- `GET /api/observability/executions/{execution_id}`;
- `POST /api/observability/gemini-smoke`.

### Interface

Rota local do frontend: `#/observability`.

A tela contém:

- lista de execuções com horário, origem, task, status, provider efetivo, fallback, duração e audit ID;
- filtros por origem, task, status, provider e fallback;
- detalhe com timeline, sanitização, roteamento, tentativas, resposta, QA, avaliação, release gate, sinais, memória e erro;
- smoke Gemini com confirmações explícitas, sem botão no FinGuard;
- aviso de que o painel é local/QA, não público.

Textos obrigatórios presentes:

> Memória técnica não altera os pesos do modelo e não constitui treinamento ou fine-tuning.

> Treinamento de modelo: não implementado.

## Provider e fallback

- `mock` e `local_qa` continuam locais e determinísticos;
- `auto` respeita safe mode e opt-in;
- `gemini` continua real e externo, nunca default em teste;
- timeout configurável por `PEDROCORE_PROVIDER_TIMEOUT_SECONDS` (default 30 s);
- tentativa principal, resultado, fallback, motivo sanitizado e duração ficam visíveis no Veltrix;
- o consumidor FinGuard recebe apenas a resposta pública, sem metadado técnico.

A flag `PEDROCORE_QA_FORCE_TOTAL_PROVIDER_FAILURE` é uma injeção de falha estritamente limitada a QA/test, observabilidade ativa e origem `finguard`.

## Gemini real opt-in

O endpoint exige simultaneamente:

- `PEDROCORE_RUN_REAL_PROVIDER_TESTS=true`;
- `PEDROCORE_RUN_REAL_GEMINI_TESTS=true`;
- ambiente não produtivo e observabilidade local disponível;
- três confirmações explícitas: rede, possível custo e integridade da chave;
- payload sintético imutável, sem conteúdo financeiro ou arquivo do usuário.

O prompt real é curto e fixo: resposta apenas com `OK`. A implementação permite no máximo uma chamada por execução e nunca imprime a chave.

Nesta frente, a chave foi verificada somente por presença/formato plausível; os dois opt-ins estavam desligados. Resultado: **0 chamadas Gemini reais**. Esse bloqueio externo não reprova a entrega local e não foi convertido em sucesso simulado.

## Integração FinGuard

O replay conjunto iniciou os dois sistemas em portas dedicadas:

| Serviço | Porta |
| --- | ---: |
| Veltrix API | 3347 |
| FinGuard API | 3348 |
| FinGuard web | 5188 |
| Veltrix web | 5191 |

Run final: `mrpxts1l-d376b365`.

Cobertura:

- contexto `PERSONAL` e Quitar Dívida pela UI do FinGuard;
- execução real FinGuard → Veltrix → FinGuard com mock local;
- relatório QA sanitizado analisado e ingerido na memória técnica volátil;
- fallback controlado visível no Veltrix e oculto tecnicamente no FinGuard;
- falha total diagnosticada no Veltrix e erro amigável no FinGuard;
- audit ID, timeline, avaliação, release gate e memória visíveis no painel;
- cleanup de processos e usuários QA;
- Organizar, Crescer, Família e Empresa não usados como prova.

Resultado final do runner: 34.188 ms, cleanup concluído, Gemini=0.

## Validação

### Backend

```powershell
cd C:\Projetos\pedrocore-ia\apps\api
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider
```

Resultado final: `368 passed, 7 skipped, 2 warnings` em 6,86 s (wrapper 7.617 ms). Os skips são testes reais opt-in.

### Frontend

```powershell
cd C:\Projetos\pedrocore-ia\apps\web
npm.cmd run build
```

Resultado: exit 0 (wrapper 2.420 ms).

### Testes principais adicionados

- `apps/api/tests/test_observability.py`;
- `apps/api/tests/test_gemini_smoke.py`;
- contratos do painel e do replay cobertos pela suíte integral;
- replay conjunto executado pelo FinGuard em `qa:e2e:finguard-pedrocore-observability`.

## Limites

- não é painel público nem deve ser exposto automaticamente na rede;
- store é volátil e local; restart limpa o histórico;
- memória técnica não é RAG, treinamento, fine-tuning ou atualização de pesos;
- avaliação/release gate são conservadores e não substituem revisão humana;
- provider real não aprova release gate sozinho;
- sem `.env` real alterado, sem segredo commitado, sem push/tag/merge;
- OCR, multimodal, Playwright real e providers externos continuam opt-in e fora da suíte padrão.

## Ações externas de Pedro

- decidir quando executar um smoke Gemini dedicado com os dois opt-ins, confirmando rede/custo/chave;
- fornecer/homologar credenciais e contas externas quando houver frente própria;
- decidir eventual exposição operacional do painel; o default deve permanecer loopback/local;
- decidir persistência futura da observabilidade, se necessária, com rotação e threat model próprios.

## Relações

- [[../../README]]
- [[../09_STATUS_ATUAL]]
- [[../MOC_QA_RELEASE_GATE]]
- [[../MOC_TESTES]]
- [[../MOC_INTEGRACOES]]
- [[../16-qa-safety-hardening/RELEASE_GATE_CHECKLIST]]
- [[../11-integracoes/CONTRATO_FINGUARD_PEDROCORE]]
