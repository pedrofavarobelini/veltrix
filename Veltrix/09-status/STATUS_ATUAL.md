# Veltrix — Status Atual

> Nota DOCFIX: este arquivo era um status legado da V2. O status oficial atual fica em [[../09_STATUS_ATUAL]] e o mapa completo em [[../00_MAPEAMENTO_GERAL_PEDROCORE]].

## Status oficial resumido

- Projeto finalizado localmente como core operacional seguro.
- Tag final local: `v7.0.0`.
- Tag MVP backend: `v6.0.0`.
- Endpoints atuais: `/`, `/health`, `POST /api/chat`, `GET /api/providers`, `POST /api/orchestrate`.
- Providers reais: implementados estruturalmente, mas default-off pelo safe mode.
- QA textual: heurística local determinística.
- Release gate: conservador; somente `local_qa` com evidência textual limpa pode aprovar.
- FinGuard: reconhecido por contrato do lado Veltrix, sem acesso direto ao repositório.

Use [[../MOC_VELTRIX]] como entrada Obsidian.
