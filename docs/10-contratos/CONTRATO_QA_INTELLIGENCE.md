# Contrato de QA Intelligence (Planejado)

> Parte da frente `PEDROCORE-REPLAN-01B`. Este documento especifica o formato **futuro** de resposta estruturada para tarefas de QA e a relação de limites entre o PedroCore e o FinGuard. Nada aqui está implementado: não existe QA Intelligence, Artifact Reader real ou análise automática de QA no código hoje. O PedroCore continua sendo, hoje, apenas uma API de chat multi-provider (`POST /api/chat`, `GET /api/providers`).

## Por que este documento existe

O mapeamento do ecossistema identificou que a parte de IA exploratória/visual/inteligente do QA Automation do FinGuard foi delegada ao PedroCore como caso de uso futuro (`QA-AUTOMATION-01G`). Este documento planeja o contrato de resposta que esse caso de uso usaria, para orientar o desenho técnico das fases seguintes (`01C`, `01D`), sem implementar nada agora.

## 5. Resposta estruturada para QA Intelligence (planejada)

Formato conceitual de resposta estruturada para tarefas de QA (`qa_report_analysis`, `qa_failure_diagnosis`, `visual_qa_analysis`, `release_gate_review`):

```json
{
  "status": "pass|warning|fail|blocked",
  "summary": "...",
  "failures": [],
  "probable_causes": [],
  "suggested_commands": [],
  "risk_level": "low|medium|high|critical",
  "can_advance": true,
  "confidence": 0.85
}
```

### Explicação dos campos

- **`status`** — resultado geral da análise, na visão do PedroCore, para a evidência apresentada:
  - `pass`: nenhum problema relevante identificado nos artefatos analisados.
  - `warning`: identificados pontos de atenção, não necessariamente bloqueantes.
  - `fail`: identificada falha relevante na evidência analisada.
  - `blocked`: o PedroCore não conseguiu concluir a análise (ex.: artefato insuficiente, fallback em tarefa crítica).
- **`risk_level`** — nível de risco percebido (`low`, `medium`, `high`, `critical`), independente do `status`, para ajudar o sistema de origem a priorizar atenção humana.
- **`can_advance`** — **sugestão** de que o item avaliado poderia avançar (ex.: para release), nunca uma aprovação automática vinculante. É sempre uma recomendação para decisão humana ou para o próprio QA Automation do FinGuard, nunca uma ação executada pelo PedroCore.
- **`confidence`** — grau de confiança do próprio PedroCore na análise gerada (0 a 1), refletindo qualidade/quantidade dos artefatos recebidos e se um provider real ou fallback foi usado.
- **`suggested_commands`** — lista de comandos que **poderiam** ser executados por um humano ou pelo QA Automation do FinGuard para investigar/corrigir (ex.: `npm run test:e2e -- --grep "dashboard"`). São sugestões textuais; o PedroCore nunca os executa.

### Diferença entre diagnóstico e correção

O PedroCore, nesta visão de arquitetura, **diagnostica e sugere** — ele nunca corrige, nunca executa e nunca aplica mudanças automaticamente:

- Diagnóstico: identificar o que provavelmente está errado (`probable_causes`), qual o risco (`risk_level`) e o que precisaria ser investigado.
- Correção: aplicar a mudança de código, rodar o comando sugerido, ajustar configuração — isso é sempre responsabilidade do sistema de origem (ex.: FinGuard) ou de um humano, nunca do PedroCore.

### PedroCore não executa comandos automaticamente

`suggested_commands` é sempre uma lista de texto/sugestão. O PedroCore, nesta arquitetura planejada, **não tem e não terá nesta fase** capacidade de executar comandos, scripts, testes ou qualquer ação dentro do FinGuard ou de qualquer outro sistema externo. Qualquer execução real permanece exclusivamente no sistema de origem.

## Relação com o FinGuard (QA Intelligence)

- O QA Automation do FinGuard (validação de API, backend, frontend, rotas, banco de teste, Prisma, Playwright, smoke tests, E2E, relatórios e evidências) está encerrado em seu escopo próprio e continua pertencendo integralmente ao FinGuard.
- `QA-AUTOMATION-01G` — o agente exploratório assistido por IA — foi delegado ao PedroCore como caso de uso futuro (esta documentação), não implementado.
- O PedroCore poderá futuramente receber relatórios de QA do FinGuard como artefatos (`type: "qa_report"` ou `"markdown"`) via payload — nunca por leitura direta do repositório do FinGuard.
- Os relatórios de QA atuais do FinGuard são **Markdown livre, não JSON estruturado**. Qualquer análise futura precisa ser tolerante a essa variação, não pode assumir um schema fixo do lado do FinGuard.
- O PedroCore não roda o QA Automation do FinGuard, não roda migrations, não roda seed/reset, não executa testes do FinGuard e não comita no FinGuard.
- O PedroCore **não calcula números financeiros oficiais** do FinGuard — pode explicar, resumir, analisar e sugerir a partir de artefatos recebidos, mas os cálculos financeiros permanecem exclusivamente no FinGuard.

## Uso seguro de providers reais nesta análise

- Para qualquer resultado que será tratado como análise real (não apenas teste de integração), a tarefa exige provider real configurado, nunca apenas `MockProvider` (Decisão Técnica 020).
- Se a resposta foi gerada com `fallback_used: true`, o `status` recomendado é `blocked` (ou, no mínimo, um `warning` forte e explícito), nunca `pass` ou `fail` apresentados como se fossem conclusivos.
- `confidence` deve refletir isso: uma resposta via fallback deve ter `confidence` baixo ou o campo deve ser omitido/nulo, nunca um valor alto que sugira confiabilidade.
