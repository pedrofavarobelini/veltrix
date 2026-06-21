# PedroCore IA — Status Atual

Atualizado em: 21/06/2026

## Versão atual

V4.0.0 — Interface melhorada do chat e experiência de uso

## Status

IMPLEMENTADA PARA TESTES — aguardando aprovação visual local.

## Local oficial

```txt
C:\Projetos\pedrocore-ia
```

## Estado do projeto

A V4 mantém a base da V3 e melhora a interface React do chat, sem alterar backend, providers, banco, login ou integração com outros projetos.

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

## Providers validados

- MockProvider.
- GeminiProvider.

## Providers preparados estruturalmente

- OpenAIProvider.
- ClaudeProvider.
- DeepSeekProvider.
- GrokProvider.

## Decisão técnica da V4

A V4 usa componentização leve no frontend React e CSS próprio. Não foi adicionada biblioteca visual externa.

## Limitações atuais

- Histórico disponível apenas no navegador atual.
- Feedback não influencia respostas futuras.
- Sem banco de dados.
- Sem login.
- Sem RAG.
- Sem deploy.
- Sem integração com FinGuard.
- GitHub remoto ainda não utilizado.
- Botão `Nova conversa` limpa o histórico atual, mas ainda não cria sessões independentes.

## Versionamento Git da V4

Após os testes locais, a V4 deve ser salva no Git local com commit e tag próprios:

```txt
commit: feat: melhorar interface do chat
tag: v4.0.0
```

A tag `v3.0.0` deve continuar existindo como marco da versão anterior aprovada.

## Documentação Obsidian atualizada

A documentação da V4 foi registrada em Markdown dentro da pasta `docs`, compatível com Obsidian.

Arquivos principais:

```txt
docs/04-comandos/V4_COMANDOS.md
docs/06_ERROS_E_CORRECOES.md
docs/08_CHANGELOG.md
docs/11_V4_INTERFACE_CHAT.md
```

## Próxima versão

V5 — Configurações de provider pela interface.

## Próximas versões

- V5 — Configurações de provider pela interface.
- V6 — Persistência real com banco de dados.
- V7 — Sessões/conversas separadas.
- V8 — RAG inicial com documentos.
- V9 — Integração futura com FinGuard.
- V10 — GitHub profissional, deploy e documentação final.
