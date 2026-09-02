# Veltrix — Erros e Correções

Atualizado em: 21/06/2026

## V4.0.0 — Interface melhorada do chat

### Risco identificado

A V4 poderia quebrar o histórico local criado na V3 se a chave do `localStorage` fosse alterada.

### Correção aplicada

A chave `pedrocore:v3:chat-history` foi preservada por compatibilidade.

---

### Risco identificado

A interface poderia ficar grande demais dentro de `ChatPage.tsx`, dificultando manutenção nas próximas versões.

### Correção aplicada

Foi criada componentização leve com componentes específicos para sidebar, bolha de mensagem, campo de envio, loading e erro.

---

### Risco identificado

Um erro de backend desligado poderia continuar aparecendo como falha bruta ou mensagem confusa.

### Correção aplicada

Foi criado `ErrorBanner` com mensagem amigável e botão `Tentar novamente`.

---

### Risco identificado

O build TypeScript pode gerar arquivo `tsconfig.tsbuildinfo`, que não deve ser enviado como arquivo de versão.

### Correção aplicada

O `.gitignore` foi reforçado com `*.tsbuildinfo`.

---

### Risco identificado

A configuração local do Obsidian poderia aparecer no Git como `docs/.obsidian/`.

### Correção aplicada

O `.gitignore` foi reforçado com `docs/.obsidian/`.

---

### Risco identificado

A V4 poderia ser confundida com uma versão de arquitetura, banco, login ou provider.

### Correção aplicada

A documentação registra explicitamente que a V4 é apenas interface/UX, sem backend funcional novo.

## V3.0.0 — Histórico e feedback local

### Risco identificado

O histórico poderia ser perdido ao recarregar a página, pois antes as mensagens ficavam apenas no estado do React.

### Correção aplicada

Foi criada persistência local usando `localStorage`.

---

### Risco identificado

O `localStorage` poderia crescer indefinidamente.

### Correção aplicada

Foi definido limite técnico de 100 mensagens armazenadas localmente.

---

### Risco identificado

Feedback poderia ficar vinculado ao índice da lista e ser salvo na resposta errada.

### Correção aplicada

Cada mensagem recebeu identificador único.

## V2.0.0 — Multi-provider

### Risco identificado

Providers reais poderiam falhar por falta de chave local.

### Correção aplicada

Fallback para MockProvider preservado.

---

## V5.0.0 — Configurações de provider pela interface

### Risco identificado

A configuração básica de provider estava espalhada entre selects simples e um painel inline, o que deixava a experiência pouco clara para uma versão multi-provider.

### Correção aplicada

Foi criado o componente `ProviderSettingsPanel.tsx`, dedicado à configuração de providers, modelos, modos e prompt base.

### Risco identificado

O usuário poderia interpretar que a interface permitiria cadastrar chaves de API no frontend.

### Correção aplicada

A V5 adicionou aviso explícito de segurança informando que as chaves continuam exclusivamente no backend, no arquivo `.env`.

### Risco identificado

Trocar provider e modelo sem persistência faria a configuração voltar ao padrão ao recarregar a página.

### Correção aplicada

Foi criado o utilitário `providerSettings.ts` com persistência local em `localStorage` usando a chave `pedrocore:v5:provider-settings`.

### Risco identificado

Providers reais sem chave poderiam causar confusão visual.

### Correção aplicada

A interface agora mostra status visual por provider: `Mock local`, `Configurado` ou `Sem chave`.

### Risco identificado

A V5 poderia quebrar o histórico local criado na V3.

### Correção aplicada

A chave `pedrocore:v3:chat-history` foi preservada sem migração forçada.

### Testes executados

- Backend: `uv run pytest`.
- Resultado: 7 testes passaram.
- Frontend: `npm run build`.
- Resultado: build concluído com sucesso.

## V5.0.0 — Configuração de providers e logo oficial

### Risco identificado

A aplicação da logo poderia alterar o design aprovado da V5.

### Correção aplicada

A logo foi aplicada somente nos pontos de identidade visual: sidebar, avatar da IA e favicon. O layout aprovado, cards de providers, histórico, chat e painel lateral foram preservados.

### Risco identificado

Usar a imagem original completa poderia carregar fundo quadriculado, marcações brancas e texto rasterizado no layout.

### Correção aplicada

Foi extraído um asset de ícone limpo da logo escolhida e o texto `Veltrix` continuou sendo renderizado pela interface React.

### Risco identificado

Chaves de API poderiam ser expostas na interface ao criar painel de providers.

### Correção aplicada

A interface mostra apenas status de configuração. As chaves permanecem exclusivamente no `.env` do backend e o ZIP não inclui `.env`.

## V5.1.1 — Correção de escopo visual da V5

### Erro identificado

A primeira entrega da V5 aplicou a logo e ajustes de configuração, mas não redesenhou o frontend no nível visual esperado pelo mockup aprovado.

### Correção aplicada

A V5.1 refaz a interface React com layout em console, sidebar escura, área central de chat, provider strip, painel direito de providers e uso consistente da logo oficial.

### Decisão

Registrar como V5.1.1 para preservar histórico Git e deixar claro que foi uma revisão de escopo visual, não uma alteração de backend.


---

## V5.1.9 — Correção de CSS e providers

### Erro identificado

Após a V5.1.2, a interface ficou mais responsiva, mas ainda apresentou problemas visuais no topo e no bloco de conversas recentes. Os cards de providers também ainda exibiam abreviações em texto em vez de ícones/logos visuais.

### Correção aplicada

Foi ajustado o CSS do topo, do bloco de conversas recentes e do estado vazio do histórico. Também foram adicionados SVGs internos para representar visualmente os providers Mock, Gemini, OpenAI/GPT, Claude, DeepSeek e Grok/xAI.


---

## V5.1.9 — Correção de responsividade estrutural

### Erro identificado

A V5.1.3 ainda não era verdadeiramente responsiva em notebook. O layout rolava como página inteira e os painéis não respeitavam a altura útil do navegador.

### Correção aplicada

A estrutura foi corrigida para usar `100dvh`, painéis internos com rolagem própria e botão Configurações focando o painel direito.


---

## V5.1.9 — Correção do erro introduzido na V5.1.5

### Erro identificado

A V5.1.5 limpou topo/sidebar, mas removeu o bloco CSS estrutural da responsividade criada na V5.1.4.

### Correção aplicada

A V5.1.9 foi reconstruída a partir da V5.1.4, preservando a responsividade e aplicando somente os ajustes pequenos solicitados.


---

## V5.1.9 — Correção de duplicidades visuais

### Erro identificado

Ainda havia um botão Histórico redundante na sidebar e uma duplicação visual no topo interno da janela.

### Correção aplicada

O botão Histórico foi removido e a barra interna deixou de exibir logo/nome duplicados. A responsividade da V5.1.6 foi preservada.


---

## V5.1.9 — Correção do alvo errado

### Erro identificado

A tentativa anterior removeu/escondeu apenas parte do topo. Os 3 ícones ainda permaneciam porque também vinham do bloco `window-actions`.

### Correção aplicada

Foram removidos/escondidos tanto `window-dots` quanto `window-actions`, sem alterar o restante do layout.


---

## V5.1.9 — Correção definitiva dos ícones residuais do topo

### Erro identificado

Os 3 ícones do topo interno continuavam aparecendo porque vinham de blocos diferentes do cabeçalho interno.

### Correção aplicada

Foram removidos os blocos `window-dots` e `window-actions` do JSX e mantido CSS defensivo para ocultar resíduos.

---

## Navegacao

- [[MOC_HISTORICO_PEDROCORE]]
- [[MOC_VELTRIX]]
