# V5 — Configurações de Provider pela Interface

Atualizado em: 21/06/2026

## Objetivo

Adicionar uma tela própria para configurar providers no frontend React do Veltrix, permitindo escolher provider, modelo, modo e prompt base sem expor chaves de API no navegador.

## Escopo da V5

A V5 implementa:

- Painel dedicado de configuração de providers.
- Cards de providers disponíveis.
- Status visual de cada provider.
- Seleção de provider ativo.
- Edição do modelo usado na requisição.
- Botão para restaurar modelo padrão.
- Seleção do modo de resposta.
- Edição do prompt base.
- Botão para restaurar prompt padrão.
- Persistência local das preferências.
- Aviso explícito de que chaves continuam somente no backend.

## Providers exibidos

- Mock.
- Gemini.
- OpenAI.
- Claude.
- DeepSeek.
- Grok/xAI.

## Status exibidos

### Mock local

Indica que o provider é local e seguro para teste sem chave externa.

### Configurado

Indica que o backend detectou chave configurada no `.env` local.

### Sem chave

Indica que o provider real ainda não tem chave configurada. Nesse caso, o backend pode usar fallback para MockProvider.

## Persistência local

A V5 cria uma nova chave de `localStorage`:

```txt
pedrocore:v5:provider-settings
```

Ela salva:

- provider selecionado;
- modelo selecionado;
- modo de resposta;
- prompt base.

## Compatibilidade com V3/V4

A V5 preserva a chave de histórico criada na V3:

```txt
pedrocore:v3:chat-history
```

Isso evita perda de histórico ao atualizar da V4 para a V5.

## Segurança

A V5 não permite inserir chave de API pela interface.

As chaves continuam exclusivamente no backend, no arquivo:

```txt
apps/api/.env
```

Esse arquivo não deve ser versionado.

## Arquivos criados

```txt
apps/web/src/components/ProviderSettingsPanel.tsx
apps/web/src/utils/providerSettings.ts
docs/04-comandos/V5_COMANDOS.md
docs/12_V5_CONFIG_PROVIDER.md
```

## Arquivos alterados

```txt
README.md
VERSION.md
COMANDOS_POWERSHELL.md
apps/web/src/pages/ChatPage.tsx
apps/web/src/components/ChatSidebar.tsx
apps/web/src/styles/global.css
docs/06_ERROS_E_CORRECOES.md
docs/08_CHANGELOG.md
docs/09_STATUS_ATUAL.md
```

## Testes obrigatórios

- Rodar testes do backend.
- Rodar build do frontend.
- Abrir painel de providers.
- Trocar provider.
- Trocar modelo.
- Restaurar modelo padrão.
- Alterar prompt base.
- Restaurar prompt padrão.
- Recarregar navegador e confirmar persistência.
- Enviar mensagem com MockProvider.
- Enviar mensagem com GeminiProvider, se a chave estiver configurada.
- Confirmar que `.env` não entrou no Git.

## Limitações

- Sem cadastro de chave pela interface.
- Sem banco de dados.
- Sem login.
- Sem sincronização entre dispositivos.
- Sem RAG.
- Sem deploy.
- Sem GitHub remoto.
- Sem integração com FinGuard.

## Próxima versão

V6 — Persistência real com banco de dados.


## Complemento visual da V5

A V5 também aplica a logo oficial escolhida pelo usuário na sidebar, no avatar das respostas da IA e no favicon. O design aprovado da interface foi preservado.

---

## Navegacao

- [[MOC_HISTORICO_PEDROCORE]]
- [[MOC_VELTRIX]]
