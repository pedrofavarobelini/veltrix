# PedroCore IA

API pessoal de IA para testar qualidade de resposta, comportamento, contexto e integração com múltiplos provedores.

## Versão atual

**V2 — Multi-provider completo inicial**

A V2 mantém a base aprovada da V1.0.4 e adiciona uma arquitetura multi-provider preparada para:

- Mock
- Gemini
- OpenAI
- Claude
- DeepSeek
- Grok/xAI

## Local correto

```txt
C:\Projetos\pedrocore-ia
```

O projeto deve ficar ao lado do FinGuard, nunca dentro dele:

```txt
C:\Projetos\FinGuard
C:\Projetos\pedrocore-ia
```

## Como rodar

Veja o arquivo:

```txt
COMANDOS_POWERSHELL.md
```

## Observação importante

A V2 já possui a estrutura para todos os provedores, mas cada provedor real só responde se sua respectiva API key estiver configurada no `.env`.

Sem chave configurada, o sistema usa fallback para MockProvider e não quebra a interface.
