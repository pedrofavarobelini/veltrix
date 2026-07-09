# MOC Integracoes

Mapa de integracoes controladas do lado PedroCore.

## FinGuard

- [[00_MAPEAMENTO_GERAL_PEDROCORE]] - secao 20.
- [[11-integracoes/CONTRATO_FINGUARD_PEDROCORE]]
- [[11-integracoes/CONTRATO_FINGUARD_PEDROCORE_REAL_CONTROLADO]]
- [[13-fechamento/FECHAMENTO_PEDROCORE_IMPLEMENT_05B]]
- [[13-fechamento/FECHAMENTO_PEDROCORE_FINAL]]

## Contratos

- [[10-contratos/CONTRATOS_TECNICOS_PEDROCORE]]
- [[10-contratos/CONTRATO_ORQUESTRACAO]]
- [[10-contratos/CONTRATO_QA_INTELLIGENCE]]
- [[10-contratos/CONTRATO_ECOSYSTEM_ASSISTANT]] - sistemas consumidores do ecossistema (ECOSYSTEM-SUITE-01).
- [[10-contratos/CONTRATO_REPORT_MEMORY]] - memoria tecnica de relatorios (default off).
- [[10-api/EXEMPLOS_API_MVP]]

## Regras essenciais

- O PedroCore reconhece `origin_system=finguard` e `origin_system=finguard-local`.
- O lado PedroCore esta pronto para receber payload HTTP em `/api/orchestrate`.
- FinGuard e consumidor read-only do assistente de ecossistema (`assistant_chat`, `finance_advice`, `project_status`, `report_memory_query`); a integracao do Assistente FinGuard via PedroCore pertence a FINGUARD-PEDROCORE-ASSISTANT-01.
- O cliente HTTP do Assistente no repositorio FinGuard ja consome `/api/orchestrate`; REAL-PROVIDER-QA-01 adiciona pedido controlado `provider=auto|gemini`.
- O PedroCore nao acessa, le, escreve, testa ou comita no FinGuard.
- Artifact Reader e bloqueado para origem/caminho FinGuard.
- Provider real e bloqueado por padrao; Gemini real so com `allow_real_provider=true`, chave no PedroCore e teste manual opt-in.
- Release gate e conservador.
