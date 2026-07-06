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
- [[10-api/EXEMPLOS_API_MVP]]

## Regras essenciais

- O PedroCore reconhece `origin_system=finguard` e `origin_system=finguard-local`.
- O lado PedroCore esta pronto para receber payload HTTP em `/api/orchestrate`.
- O cliente HTTP no repositorio FinGuard ainda e frente separada.
- O PedroCore nao acessa, le, escreve, testa ou comita no FinGuard.
- Artifact Reader e bloqueado para origem/caminho FinGuard.
- Provider real e bloqueado por padrao.
- Release gate e conservador.
