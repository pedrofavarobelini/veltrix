# QA Intelligence — Diagnóstico de Falha (`qa_failure_diagnosis`)

> Nota DOCFIX: este caso de uso foi implementado no lado PedroCore como heurística textual local em `POST /api/orchestrate` e `/api/chat`, usando `task_type="qa_failure_diagnosis"`. Não é IA real, não lê o FinGuard e não executa testes.

## Objetivo

Diagnosticar prováveis causas de uma falha já identificada em evidências de QA (log, saída de terminal, relatório), sugerindo investigação — nunca corrigindo ou executando nada.

## Entrada esperada

- `message` — descrição da falha observada (ex.: "o teste de login está falhando intermitentemente").
- `artifacts` — evidências relacionadas: `log`, `terminal_output`, `json_result`, `qa_report`, e futuramente `playwright_trace`.
- `context` — recomendado incluir `project`, `environment` e `module`/`route` afetados.

## Saída esperada

Resposta estruturada (ver `QA_INTELLIGENCE_OVERVIEW.md`, seção 6), com ênfase em:

- `failures` — a(s) falha(s) identificada(s) a partir da evidência.
- `probable_causes` — hipóteses de causa raiz, apresentadas como diagnóstico, nunca como certeza.
- `suggested_commands` — comandos de investigação sugeridos (texto, nunca executados).
- `risk_level` e `confidence` conforme os critérios gerais.

## Diferença entre diagnóstico e correção (reforço)

Este caso de uso **diagnostica** (identifica o que provavelmente está errado e o que investigar) — ele **não corrige** (não aplica mudança de código, não roda o comando sugerido, não ajusta configuração). A correção real permanece sempre responsabilidade do sistema de origem (ex.: FinGuard) ou de um humano.

## Exige resposta estruturada?

Sim, obrigatoriamente — um diagnóstico de falha precisa ser consumível por sistemas externos sem depender de um humano interpretando texto livre.

## Mock pode ser usado?

Apenas para teste, nunca como diagnóstico real de uma falha.

## Fallback Mock deve bloquear conclusão?

Sim — um diagnóstico gerado via fallback não pode ser tratado como diagnóstico confiável. `fallback_used: true` deve resultar em `status: "blocked"` ou `warning` forte.

## Observações de segurança

- Logs e saídas de terminal podem conter tokens, caminhos internos ou dados de usuário — o sistema de origem é responsável por sanitizar segredos antes de enviar.
- `suggested_commands` nunca deve incluir comandos que alterem estado (ex.: `DROP`, `DELETE`, `rm -rf`, `migrate`, `seed`, `reset`) como se fossem seguros de rodar sem revisão — mesmo como sugestão, o texto deve deixar claro que é responsabilidade do sistema de origem avaliar antes de executar.
- Este diagnóstico nunca executa nada no FinGuard ou em qualquer sistema externo — é estritamente análise textual do que foi enviado.
