# PedroCore IA — Versionamento

Atualizado em: 21/06/2026

## Versão atual

V3.0.0 — Histórico local e feedback simples

## Status

IMPLEMENTADA PARA TESTES — aguardando aprovação final pela interface.

## Local oficial

```txt
C:\Projetos\pedrocore-ia
```

## Resumo da V3

A V3 adiciona persistência local de conversas no frontend e feedback básico por resposta da IA.

## Entregas concluídas na V3

- Histórico simples de mensagens no frontend.
- Persistência usando `localStorage`.
- Identificador único por mensagem.
- Feedback `Gostei` e `Não gostei` vinculado a cada resposta da IA.
- Feedback persistente após recarregar a página.
- Contador de mensagens do histórico local.
- Botão para limpar histórico local.
- Limite técnico de 100 mensagens de conversa salvas localmente.
- Leitura segura do histórico salvo, com proteção contra JSON inválido.
- Documentação da V3 criada/atualizada.

## Limitações conhecidas da V3

- O histórico fica apenas no navegador atual.
- Limpar dados do navegador remove o histórico.
- O feedback ainda não treina o modelo e não altera respostas futuras.
- Ainda não existe banco de dados.
- Ainda não existe login.
- Ainda não existe sincronização entre dispositivos.

## Versões concluídas

- V1 — Chat simples + API mock. APROVADA.
- V1.0.4 — Correção definitiva dos textos da interface. APROVADA.
- V2 — Multi-provider com Gemini real. APROVADA.
- V3.0.0 — Histórico local + feedback simples. IMPLEMENTADA PARA TESTES.

## Próxima versão

V4 — Melhorias de interface do chat e experiência de uso.

## Roadmap

- V4 — Melhorias de interface do chat.
- V5 — Configurações de provider pela interface.
- V6 — Persistência real com banco de dados.
- V7 — Sessões/conversas separadas.
- V8 — RAG inicial com documentos.
- V9 — Integração futura com FinGuard.
- V10 — GitHub profissional, deploy e documentação final.
