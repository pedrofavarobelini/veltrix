# PedroCore IA — Versionamento

Atualizado em: 21/06/2026

## Versão atual

V4.0.0 — Interface melhorada do chat e experiência de uso

## Status

IMPLEMENTADA PARA TESTES — aguardando aprovação visual local.

## Local oficial

```txt
C:\Projetos\pedrocore-ia
```

## Resumo da V4

A V4 melhora a interface React do chat sem alterar a arquitetura do backend, os providers ou a persistência local criada na V3.

## Entregas concluídas na V4

- Layout principal reorganizado com sidebar de histórico local.
- Chat visualmente mais limpo e profissional.
- Bolhas modernas para mensagens do usuário e da IA.
- Componentização leve da interface React.
- Componentes criados para sidebar, bolha de mensagem, composer, loading e erro visual.
- Botão copiar resposta mantido e melhorado visualmente.
- Feedback `Gostei` e `Não gostei` preservado e melhorado visualmente.
- Timestamp simples por mensagem.
- Indicador de carregamento `PedroCore está pensando...`.
- Tratamento visual de erro com botão `Tentar novamente`.
- Métricas simples da conversa: mensagens, respostas, gostei e não gostei.
- Responsividade melhorada para telas menores.
- Persistência local da V3 preservada usando `localStorage`.
- Documentação da V4 criada/atualizada em Markdown compatível com Obsidian.

## Limitações conhecidas da V4

- O histórico continua local, apenas no navegador atual.
- O feedback ainda não treina o modelo e não altera respostas futuras.
- Ainda não existe banco de dados.
- Ainda não existe login.
- Ainda não existe sistema real de múltiplas conversas.
- Ainda não existe RAG.
- Ainda não existe deploy.
- Ainda não existe integração com FinGuard.

## Versões concluídas

- V1 — Chat simples + API mock. APROVADA.
- V1.0.4 — Correção definitiva dos textos da interface. APROVADA.
- V2 — Multi-provider com Gemini real. APROVADA.
- V3.0.0 — Histórico local + feedback simples. APROVADA E VERSIONADA.
- V4.0.0 — Interface melhorada do chat e experiência de uso. IMPLEMENTADA PARA TESTES.

## Git local da V4

Depois dos testes e da aprovação visual, a V4 deve ser salva no Git local com:

```txt
commit: feat: melhorar interface do chat
tag: v4.0.0
```

A tag anterior `v3.0.0` deve ser preservada.

## Documentação Obsidian da V4

Documentos principais da V4:

```txt
docs/04-comandos/V4_COMANDOS.md
docs/06_ERROS_E_CORRECOES.md
docs/08_CHANGELOG.md
docs/09_STATUS_ATUAL.md
docs/11_V4_INTERFACE_CHAT.md
```

## Próxima versão

V5 — Configurações de provider pela interface.

## Roadmap

- V5 — Configurações de provider pela interface.
- V6 — Persistência real com banco de dados.
- V7 — Sessões/conversas separadas.
- V8 — RAG inicial com documentos.
- V9 — Integração futura com FinGuard.
- V10 — GitHub profissional, deploy e documentação final.
