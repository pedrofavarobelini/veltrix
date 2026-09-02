# V5.1.9 — Responsividade estrutural e configurações

## Objetivo

Corrigir o problema persistente de responsividade em notebook e tornar o botão Configurações funcional em relação ao painel de provider.

## Problemas identificados

- O layout ainda gerava scroll geral da página no notebook.
- O painel central ficava grande demais e sobrava espaço vertical.
- A área de provider à direita precisava de rolagem interna real.
- O botão Configurações da sidebar não abria nem focava o painel de configuração.
- A responsividade não estava estrutural; era apenas ajuste visual.

## Correções aplicadas

- `html`, `body` e `#root` agora usam altura total.
- O `body` não rola no layout desktop/notebook; os painéis internos rolam.
- O `app-shell` usa `100dvh`.
- A janela principal usa `flex` e altura real do viewport.
- Sidebar, chat e painel de providers têm altura controlada.
- Chat central usa `flex` real, sem espaço morto excessivo.
- Provider dock tem rolagem interna.
- Botão Configurações agora foca o painel de providers à direita.
- Breakpoints mantidos para largura menor e telas móveis.

## Mantido

- Logo oficial.
- Ícones dos providers.
- Backend FastAPI sem alteração funcional.
- Histórico local.
- Configurações locais.
- Documentação Obsidian.

---

## Navegacao

- [[MOC_HISTORICO_PEDROCORE]]
- [[MOC_VELTRIX]]
