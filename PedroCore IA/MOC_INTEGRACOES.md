# MOC Integracoes

Mapa de integracoes controladas do lado PedroCore.

## Elyra

- [[17-multi-provider-safe-evolution/PEDROCORE_ELYRA_ONBOARDING_V1_TEXTUAL]]
- [[17-multi-provider-safe-evolution/GATE_PEDROCORE_ELYRA_ONBOARDING_V1_TEXTUAL]]
- [[10-contratos/CONTRATO_ELYRA_TEXTUAL_V1]]
- Consumer externo read-only, identidade própria `registered`, papel
  `common_consumer` e somente `wellbeing_report_interpretation`.
- Mock determinístico no CI; real somente por auto/Gemini não produtivo, sem
  modelo do caller e sem fallback.
- PedroCore recebe somente snapshot explícito; não acessa banco/Storage Elyra.
- Multimodal e learning permanecem desabilitados.

## Structa

- [[17-multi-provider-safe-evolution/PEDROCORE_STRUCTA_CONSUMER_01]]
- [[17-multi-provider-safe-evolution/GATE_PEDROCORE_STRUCTA_CONSUMER_01]]
- Consumer externo read-only, identidade própria `registered`, papel
  `technical_tool`, somente `qa_report_analysis` e Gemini não produtivo.
- Provider real continua default-off e depende de Gate separado do Structa.
- Structa não herda identidade ou permissões FinGuard/PedroCore.

## FinGuard

- [[00_MAPEAMENTO_GERAL_PEDROCORE]] - secao 20.
- [[11-integracoes/CONTRATO_FINGUARD_PEDROCORE]]
- [[11-integracoes/CONTRATO_FINGUARD_PEDROCORE_REAL_CONTROLADO]]
- [[13-fechamento/FECHAMENTO_PEDROCORE_IMPLEMENT_05B]]
- [[13-fechamento/FECHAMENTO_PEDROCORE_FINAL]]
- [[MOC_MULTI_PROVIDER_SAFE_EVOLUTION]]
- [[17-multi-provider-safe-evolution/FECHAMENTO_ETAPAS_1_A_7]]

## Contratos

- [[10-contratos/CONTRATOS_TECNICOS_PEDROCORE]]
- [[10-contratos/CONTRATO_ORQUESTRACAO]]
- [[10-contratos/CONTRATO_QA_INTELLIGENCE]]
- [[10-contratos/CONTRATO_ECOSYSTEM_ASSISTANT]] - sistemas consumidores do ecossistema (ECOSYSTEM-SUITE-01).
- [[10-contratos/CONTRATO_REPORT_MEMORY]] - memoria tecnica de relatorios (default off).
- [[10-contratos/CONTRATO_ELYRA_TEXTUAL_V1]] - capability textual versionada da Elyra Stage 09.
- [[10-api/EXEMPLOS_API_MVP]]

## Regras essenciais

- O PedroCore reconhece `origin_system=finguard` e `origin_system=finguard-local`.
- O lado PedroCore esta pronto para receber payload HTTP em `/api/orchestrate`.
- FinGuard é consumidor read-only do assistente de ecossistema (`assistant_chat`, `finance_advice`, `project_status`, `report_memory_query`).
- O cliente comum pede `provider=auto` sem modelo; identidade, autorização, provider e modelo são decididos pelo PedroCore.
- O PedroCore nao acessa, le, escreve, testa ou comita no FinGuard.
- Artifact Reader e bloqueado para origem/caminho FinGuard.
- Provider real é bloqueado por padrão; execução exige `allow_real_provider=true`, identidade registrada, credencial própria no PedroCore e binding elegível.
- Somente `gemini + gemini-3.5-flash` está homologado/autorizado neste checkpoint; nenhum segundo provider real está operacional.
- Release gate e conservador.
