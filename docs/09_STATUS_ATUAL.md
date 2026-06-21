# PedroCore IA — Status Atual

Atualizado em: 21/06/2026

## Versão atual

V5.0.0 — Configurações de provider pela interface e logo oficial

## Status

IMPLEMENTADA PARA TESTES — aguardando aprovação local.

## Local oficial

```txt
C:\Projetos\pedrocore-ia
```

## Estado do projeto

A V5 mantém a base da V4, adiciona uma experiência mais completa para configurar providers pela interface React, preserva o histórico local da V3/V4 e aplica a logo oficial escolhida para o PedroCore IA.

## Funcionalidades disponíveis

- Backend FastAPI funcionando.
- Frontend React/Vite/TypeScript funcionando.
- Endpoint `/health` funcionando.
- Endpoint `/api/providers` funcionando.
- Endpoint `/api/chat` funcionando.
- MockProvider funcionando.
- GeminiProvider funcionando com chave real local.
- Estrutura multi-provider mantida.
- Fallback para MockProvider preservado.
- Histórico de mensagens salvo no navegador com `localStorage`.
- Feedback `Gostei` e `Não gostei` salvo por resposta da IA.
- Interface com sidebar de histórico local.
- Bolhas modernas de mensagem.
- Botão copiar resposta.
- Timestamp simples nas mensagens.
- Loading visual `PedroCore está pensando...`.
- Erro visual com opção de tentar novamente.
- Métricas simples da conversa.
- Layout responsivo.
- Painel dedicado de configuração de providers.
- Cards visuais de provider.
- Status por provider: mock local, configurado ou sem chave.
- Seleção de provider, modelo, modo e prompt base pela interface.
- Preferências de provider salvas localmente em `pedrocore:v5:provider-settings`.
- Logo oficial aplicada na sidebar.
- Logo oficial aplicada no avatar das respostas da IA.
- Favicon atualizado com a identidade visual oficial.

## Providers validados

- MockProvider.
- GeminiProvider.

## Providers preparados estruturalmente

- OpenAIProvider.
- ClaudeProvider.
- DeepSeekProvider.
- GrokProvider.

## Decisão técnica da V5

A V5 adiciona um painel React dedicado para configuração de providers, mantém CSS próprio, usa persistência local via `localStorage` e aplica a logo oficial como asset estático do frontend. Nenhuma chave de API é exposta no frontend.

## Limitações atuais

- Histórico disponível apenas no navegador atual.
- Preferências de provider disponíveis apenas no navegador atual.
- Feedback não influencia respostas futuras.
- Sem cadastro de chaves pela interface.
- A logo foi extraída a partir da imagem enviada; uma versão SVG/PNG transparente original pode melhorar nitidez futuramente.
- Sem banco de dados.
- Sem login.
- Sem RAG.
- Sem deploy.
- Sem integração com FinGuard.
- GitHub remoto ainda não utilizado.
- Botão `Nova conversa` limpa o histórico atual, mas ainda não cria sessões independentes.

## Versionamento Git da V5

Após os testes locais, a V5 deve ser salva no Git local com commit e tag próprios:

```txt
commit: feat: adicionar configuracoes de provider e logo oficial
tag: v5.0.0
```

As tags `v2.0.0`, `v3.0.0` e `v4.0.0` devem continuar existindo como marcos das versões anteriores aprovadas.

## Documentação Obsidian atualizada

A documentação da V5 foi registrada em Markdown dentro da pasta `docs`, compatível com Obsidian.

Arquivos principais:

```txt
docs/04-comandos/V5_COMANDOS.md
docs/06_ERROS_E_CORRECOES.md
docs/08_CHANGELOG.md
docs/12_V5_CONFIG_PROVIDER.md
docs/13_V5_IDENTIDADE_VISUAL.md
```

## Próxima versão

V6 — Persistência real com banco de dados.

## Próximas versões

- V6 — Persistência real com banco de dados.
- V7 — Sessões/conversas separadas.
- V8 — RAG inicial com documentos.
- V9 — Integração futura com FinGuard.
- V10 — GitHub profissional, deploy e documentação final.

## Atualização — V5.1.9

Versão atual do pacote: V5.1.1 — Redesign real do front-end com logo oficial.

### Estado

Implementada para testes locais.

### Funcionalidades disponíveis

- Chat com histórico local.
- Feedback gostei/não gostei.
- Interface redesenhada com sidebar, chat central e painel direito.
- Configuração de provider pela interface.
- Logo oficial aplicada.
- Providers estruturais mantidos.

### Ainda não implementado

- Banco de dados.
- Login.
- RAG.
- Deploy.
- GitHub.
- Integração com FinGuard.


---

## V5.1.9 — Ajuste de CSS e logos dos providers

Status: implementada para testes.

A V5.1.9 corrige problemas visuais restantes no topo e no bloco de conversas recentes. Também cadastra ícones SVG internos para Mock, Gemini, OpenAI/GPT, Claude, DeepSeek e Grok/xAI nos cards de provider.


---

## V5.1.9 — Responsividade estrutural e configurações

Status: implementada para testes. Corrige scroll geral em notebook, altura dos painéis e foco do botão Configurações.


---

## V5.1.9 — Responsividade preservada e topo limpo

Status: implementada para testes. Corrige o erro da V5.1.5, preservando a responsividade da V5.1.4 e mantendo apenas as correções de topo/sidebar.


---

## V5.1.9 — Topo e Histórico limpos

Status: implementada para testes. Remove o botão Histórico da sidebar e a duplicação do topo interno, preservando a responsividade da V5.1.6.


---

## V5.1.9 — Remoção definitiva dos ícones do topo interno

Status: implementada para testes. Remove `window-dots` e `window-actions` sem alterar o layout.
