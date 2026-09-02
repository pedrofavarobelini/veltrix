# Veltrix — Decisões Técnicas

Atualizado em: 21/06/2026

## V4.0.0 — Componentização leve da interface React

A V4 iniciou a separação da interface do chat em componentes React pequenos.

Componentes criados:

```txt
ChatSidebar
MessageBubble
ChatComposer
LoadingBubble
ErrorBanner
```

## Motivo

A interface estava concentrada em `ChatPage.tsx`. A componentização leve reduz o acoplamento visual e prepara o projeto para V5 e V6.

## Decisão

Usar React + TypeScript + CSS próprio.

Não usar ainda:

- Tailwind.
- shadcn/ui.
- Material UI.
- Bootstrap.
- Design system completo.

## Justificativa

A prioridade da V4 é melhorar a experiência de uso mantendo estabilidade. Bibliotecas visuais externas seriam custo adicional neste momento.

## Compatibilidade com V3

A V4 preserva a chave de armazenamento local da V3:

```txt
pedrocore:v3:chat-history
```

Essa decisão evita perda de histórico local ao atualizar da V3 para a V4.

---

## Navegacao

- [[MOC_HISTORICO_PEDROCORE]]
- [[MOC_VELTRIX]]
