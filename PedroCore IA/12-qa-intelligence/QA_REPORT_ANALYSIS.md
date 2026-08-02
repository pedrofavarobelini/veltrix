# QA Intelligence — Análise de Relatório de QA (`qa_report_analysis`)

> Nota DOCFIX: este caso de uso foi implementado no lado PedroCore como heurística textual local em `POST /api/orchestrate` e `/api/chat`, usando `task_type="qa_report_analysis"`. Não é IA real, não lê o FinGuard e não executa testes.

## Objetivo

Analisar um relatório de QA (tipicamente Markdown livre, como os relatórios do FinGuard) e devolver um diagnóstico estruturado: resumo, achados, falhas, causas prováveis e nível de risco — sem executar nenhum teste.

## Entrada esperada

- `message` — instrução da análise (ex.: "Analise este relatório de QA").
- `artifacts` — pelo menos um artefato do tipo `qa_report` ou `markdown`, contendo o texto do relatório (ver `docs/10-contratos/CONTRATO_ORQUESTRACAO.md`, seção 6, e `QA_INTELLIGENCE_OVERVIEW.md`, seção 4).
- `context` — recomendado incluir `project`, `environment` e `module`, para situar a análise.

## Saída esperada

Resposta estruturada seguindo o formato descrito em `QA_INTELLIGENCE_OVERVIEW.md`, seção 6 (`status`, `summary`, `findings`, `failures`, `probable_causes`, `risk_level`, `confidence`, `fallback_used`, `warnings`). Para este caso de uso, `can_advance` e `suggested_commands` são opcionais — o foco principal é resumir e diagnosticar o relatório, não necessariamente decidir sobre avanço de release (isso é o foco de `QA_RELEASE_GATE.md`).

## Exige resposta estruturada?

Sim, obrigatoriamente (Decisão Técnica 018) — texto livre não é suficiente para um sistema externo consumir essa análise de forma confiável.

## Mock pode ser usado?

Apenas para teste de integração e desenvolvimento. **Mock não é confiável para validar um relatório real de QA** (ver Decisão Técnica 020 e regra de fallback na seção 9 de `QA_INTELLIGENCE_OVERVIEW.md`).

## Fallback Mock deve bloquear conclusão?

Sim — se o provider real falhar e a resposta cair para `MockProvider`, a análise deve indicar `status: "blocked"` ou, no mínimo, `warning` forte, com `confidence` baixo. Nunca deve ser apresentada como uma análise real do relatório.

## Observações de segurança

- O conteúdo do relatório pode conter dados de ambiente de teste; o sistema de origem é responsável por não enviar segredos/dados sensíveis desnecessários no payload.
- Relatórios incompletos ou truncados devem resultar em `confidence` baixo, nunca em suposições preenchidas pelo PedroCore para "completar" a análise.
- Esta análise nunca lê o relatório diretamente do repositório do FinGuard — apenas o conteúdo enviado no payload é considerado (Decisão Técnica 019 e 026).

## Links relacionados

- [[../MOC_QA_RELEASE_GATE]]
- [[../MOC_QA_SAFETY_HARDENING]]
- [[../16-qa-safety-hardening/REPORT_MEMORY_SAFETY]]
- [[../16-qa-safety-hardening/PROVIDER_REAL_SAFETY]]
