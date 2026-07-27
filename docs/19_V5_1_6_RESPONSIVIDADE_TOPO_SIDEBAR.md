# V5.1.9 — Preservar responsividade e limpar topo/sidebar

## Objetivo

Corrigir o erro da V5.1.5, que limpou o topo/sidebar mas acabou removendo parte da correção estrutural de responsividade da V5.1.4.

## Problema identificado

A V5.1.5 voltou a quebrar a responsividade porque o bloco CSS estrutural da V5.1.4 foi removido durante a geração da versão.

## Correção aplicada

- Base retomada a partir da V5.1.4 responsiva.
- Preservado o bloco estrutural de responsividade com `100dvh`, painéis internos e rolagem interna.
- Removido apenas o botão Configurações abaixo de Histórico.
- Topo simplificado para logo + PedroCore IA.
- Removidos textos quebrados de versão/provider do topo.
- Mantidos ícones dos providers.
- Backend sem alteração funcional.

## Regra para próximas correções visuais

Não substituir nem remover os blocos de responsividade já aprovados. Ajustes visuais pequenos devem ser aplicados por override incremental, nunca por reescrita destrutiva do CSS.

---

## Navegacao

- [[MOC_HISTORICO_PEDROCORE]]
- [[MOC_PEDROCORE_IA]]
