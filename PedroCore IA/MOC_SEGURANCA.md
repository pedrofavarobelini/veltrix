# MOC Seguranca

Mapa dos limites de seguranca do PedroCore IA.

## Referencias atuais

- [[19-encerramento-final/PEDROCORE_FECHAMENTO_DOCUMENTAL_FINAL_ERAS_1_A_3]] -
  limites consolidados das Eras 1–3 e do roadmap de treinamento.
- [[10-contratos/CONTRATO_OPERATIONAL_MEMORY]] - evidência, promoção e lifecycle.
- [[10-contratos/CONTRATO_EXECUTION_CONTRACT]] - HMAC, scope, gates e review humano.
- [[10-contratos/CONTRATO_TRAINING_DATA_CANDIDATE]] - privacy, provenance e autorização neural.
- [[16-training-data/DATASET_READINESS_AUDIT]] - zero candidatos reais autorizados.
- [[20-ux-v1/MODELO_DE_AMEACA]] - **cenários A/B/C/D**: seguro para uso local,
  ecossistema local e código público; NÃO seguro para API na internet, com a
  lista dos requisitos de deploy que faltam.
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
- [[17-multi-provider-safe-evolution/PEDROCORE_STRUCTA_CONSUMER_01]] - onboarding Structa com identidade registrada, role/task/provider mínimos e threat model.
- [[17-multi-provider-safe-evolution/GATE_PEDROCORE_STRUCTA_CONSUMER_01]] - evidência offline de autorização e negações sem provider real.

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
- Structa: somente `registered + technical_tool + qa_report_analysis + gemini` em ambiente não produtivo; `local_trusted`, wildcard e providers diferentes são negados.

### Frontend (UX V1)

- Chaves de API **nunca** no navegador: o `localStorage` guarda preferências e o
  **ID** do provider autorizado, que é consentimento e não credencial.
- Autorização por provider: trocar de IA descarta a anterior; autorização de um
  provider não vale para outro.
- Sem XSS: nenhum `dangerouslySetInnerHTML`, `innerHTML` ou `eval` em
  `apps/web/src`; conteúdo renderizado como texto pelo escape do React.
- Microfone: áudio não é gravado, guardado, logado nem enviado ao PedroCore ou
  a provider; a interface não afirma que a transcrição é offline.
- Anexos: allowlist por extensão, MIME como sinal secundário, limites abaixo dos
  do backend, nome saneado tratado como metadado e nunca como caminho, conteúdo
  nunca executado nem exibido.
- Providers internos ficam fora da build pública; a área técnica do drawer é
  eliminada do bundle de produção.

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
  tenha parado. Nem mesmo `transport_close_outcome="confirmed"` altera isso.
  Ver
  [[18-provider-output-budget-cancellation/PEDROCORE_PROVIDER_OUTPUT_BUDGET_CANCELLATION_01]]
  e [[18-provider-output-budget-cancellation/PEDROCORE_ASSISTANT_FINAL_CLOSURE_01]].
- Diagnóstico de falha de provider real vive em ring buffer **em memória**: ele
  não sobrevive ao encerramento do processo, e por isso a causa da última falha
  do cenário Organizar não pôde ser determinada.
- Valores de orçamento de saída derivam do `response_style` das tasks, não de
  medição real de tokens; podem precisar de ajuste após sonda autorizada.
- **`/api/chat` não tem autenticação.** É deliberado: o endpoint serve o próprio
  frontend local e mantém compatibilidade com consumidores antigos. Isso é
  aceitável nos cenários A, B e C, e é bloqueante para o cenário D. Ver
  [[20-ux-v1/MODELO_DE_AMEACA]].
- Não há rate limiting nem teto global de payload; ambos são requisitos de
  deploy, não de uso local.
