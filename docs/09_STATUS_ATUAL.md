# PedroCore IA — Status Atual

Atualizado em: 21/06/2026

## Versão atual

V3.0.0 — Histórico local e feedback simples

## Status

IMPLEMENTADA PARA TESTES — aguardando aprovação final pela interface.

## Local oficial

```txt
C:\Projetos\pedrocore-ia
```

## Estado do projeto

A V3 mantém a base da V2 e adiciona histórico local no frontend com feedback básico por resposta.

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
- Botão para limpar histórico local.
- Contador simples de mensagens salvas no histórico local.

## Providers validados

- MockProvider.
- GeminiProvider.

## Providers preparados estruturalmente

- OpenAIProvider.
- ClaudeProvider.
- DeepSeekProvider.
- GrokProvider.

## Decisão técnica da V3

A persistência foi feita no frontend usando `localStorage` porque a V3 não deve introduzir banco de dados, login ou sincronização entre dispositivos.

## Limitações atuais

- Histórico disponível apenas no navegador atual.
- Feedback não influencia respostas futuras.
- Sem banco de dados.
- Sem login.
- Sem RAG.
- Sem deploy.
- Sem integração com FinGuard.
- GitHub remoto ainda não utilizado.

## Próxima versão

V4 — Melhorias de interface do chat e experiência de uso.

## Próximas versões

- V4 — Melhorias de interface do chat.
- V5 — Configurações de provider pela interface.
- V6 — Persistência real com banco de dados.
- V7 — Sessões/conversas separadas.
- V8 — RAG inicial com documentos.
- V9 — Integração futura com FinGuard.
- V10 — GitHub profissional, deploy e documentação final.
