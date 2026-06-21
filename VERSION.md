# PedroCore IA — Versionamento

Atualizado em: 21/06/2026

## Versão atual

V5.1.9 — Remoção definitiva dos ícones do topo interno

## Status

IMPLEMENTADA PARA TESTES — aguardando aprovação visual local.

## Resumo

A V5.1.9 remove de forma definitiva os ícones/círculos residuais do topo interno da interface. A correção preserva a responsividade da versão anterior, o design aprovado, a sidebar, o painel direito e o backend.

## Alterações

- Removidos os blocos `window-dots` e `window-actions` do JSX.
- Adicionado CSS defensivo para ocultar qualquer resíduo desses blocos.
- Mantida a estrutura visual aprovada.
- Mantida a responsividade.
- Mantido backend sem alteração funcional.

## Git sugerido

```txt
commit: fix: remover definitivamente icones do topo interno
tag: v5.1.9
```

## Próxima versão

V6 — Persistência real com banco de dados.
