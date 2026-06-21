# PedroCore IA

API pessoal de IA para testar qualidade de resposta, comportamento, contexto, histórico, feedback e integração com múltiplos provedores.

## Versão atual

**V3.0.0 — Histórico local e feedback simples**

A V3 mantém a base aprovada da V2 e adiciona:

- Histórico simples de mensagens no frontend.
- Persistência local usando `localStorage`.
- Feedback `Gostei` e `Não gostei` por resposta da IA.
- Botão para limpar histórico local.

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

O arquivo `.env` contém chaves reais e não deve ser versionado nem enviado para o GitHub.

Use `.env.example` como modelo seguro de configuração.

## Limitação da V3

O histórico e os feedbacks ficam apenas no navegador atual. Eles ainda não são salvos em banco de dados e não treinam o modelo.
