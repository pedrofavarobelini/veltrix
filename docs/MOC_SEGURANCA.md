# MOC Seguranca

Mapa dos limites de seguranca do PedroCore IA.

## Referencias atuais

- [[00_MAPEAMENTO_GERAL_PEDROCORE]] - secoes 11 a 19 e 27.
- [[13-fechamento/FECHAMENTO_PEDROCORE_FINAL]] - garantias finais.
- [[MOC_QA_SAFETY_HARDENING]] - safety hardening commitado em `d6106b7`.
- [[16-qa-safety-hardening/PROVIDER_REAL_SAFETY]] - bloqueio estrutural de providers reais.
- [[16-qa-safety-hardening/REPORT_MEMORY_SAFETY]] - Report Memory default-off e nao treinamento.
- [[16-qa-safety-hardening/MATRIZ_TASK_PROVIDER_POLICY]] - matriz de policy por task/provider.
- [[11-integracoes/CONTRATO_FINGUARD_PEDROCORE_REAL_CONTROLADO]] - bloqueios para FinGuard.
- [[10-api/EXEMPLOS_API_MVP]] - exemplos seguros.
- [[MOC_MULTI_PROVIDER_SAFE_EVOLUTION]] - segurança ponta a ponta das Etapas 1–7.
- [[17-multi-provider-safe-evolution/FIX_CREDENCIAL_COMPARTILHADA]] - credencial global não concede identidade privilegiada.
- [[17-multi-provider-safe-evolution/FIX_HOMOLOGACAO_CONFIGURACAO_MODELOS]] - configuração runtime não homologa modelo.

## Controles principais

- Safe mode: `allow_real_provider=false` por padrao.
- Policy enforcement: bloqueio de tasks perigosas e payload com comando.
- Artifact Reader: opt-in, allowlist e bloqueio de `.env`, segredo, binario, traversal e FinGuard.
- Release gate: somente `local_qa` com evidencia textual limpa aprova.
- OCR: local, opt-in e com revisao humana.
- Multimodal: guard/contrato, sem envio real nesta versao.
- Playwright: opt-in, read-only, allowlist e acoes interativas bloqueadas.
- Audit: nao persistente e sem conteudo de artefatos.
- Report Memory: default off; `context_from_memory=false` por request; segredos redigidos; relatorios nao treinam IA.
- Local model: opt-in duplo (flag + `allow_local_model`); sem rede nesta frente; bloqueado em release gate e tarefa critica.
- Guard de testes: provider real bloqueado por construcao na suite padrao; `allow_real_provider=true` nao e usado em testes padrao.
- finance_advice: read-only, disclaimer obrigatorio, sem acao financeira.
- Eval harness: rejeita `allow_real_provider=true` por validacao; sem rede.
- Identidade/autorização: credencial compartilhada fica ambígua e a matriz nega por padrão.
- Binding: provider e modelo devem formar par explícito, homologado e autorizado; configuração não promove catálogo.
- Circuit breaker: local por processo, default-off, separado por environment/provider/model.
- Fallback real: default-off, somente para `provider_pre_dispatch + not_dispatched + external_dispatch=false`, no máximo um secundário; timeout nunca qualifica.

## Codigo relacionado

- `apps/api/app/modules/policy_enforcement/`
- `apps/api/app/modules/real_features/`
- `apps/api/app/modules/artifact_reader/`
- `apps/api/app/modules/qa_response/`
- `apps/api/app/modules/exploration/playwright_adapter.py`
- `apps/api/app/modules/contracts/codes.py`

## Riscos conhecidos

- Falso positivo/negativo da heuristica textual.
- Chamada real se provider real for autorizado explicitamente.
- Fallback Mock mascarando falha se consumidor ignorar `fallback_used`.
- Documentos historicos fora dos MOCs podem refletir fases antigas.
- **Cancelamento remoto não comprovável**: após um timeout de transporte, o
  PedroCore fecha a conexão local, mas não há prova de que a geração remota
  tenha parado. Ver
  [[18-provider-output-budget-cancellation/PEDROCORE_PROVIDER_OUTPUT_BUDGET_CANCELLATION_01]].
- Valores de orçamento de saída derivam do `response_style` das tasks, não de
  medição real de tokens; podem precisar de ajuste após sonda autorizada.
