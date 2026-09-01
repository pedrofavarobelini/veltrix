# UX V1 — Composer e Configurações

Mapa da frente: [[MOC_UX_V1]].

Estado da interface pública do PedroCore IA na versão de produto **V5.2.0**.

## Layout

```text
┌─────────────────────────────────────────────────────────┐
│ PedroCore IA                                            │
├──────────┬──────────────────────────────────────────────┤
│ sidebar  │ Chat com PedroCore IA          [⚙ Config.]   │
│ (histó-  ├──────────────────────────────────────────────┤
│  rico)   │              mensagens                       │
│          ├──────────────────────────────────────────────┤
│          │ Digite sua mensagem...                       │
│          │ ┌────────────┐ ┌────────────┐                │
│          │ │ README.md  │ │ dados.csv  │  (anexos)      │
│          │ │ 4 KB  md ×│ │ 8 KB txt ×│                │
│          │ └────────────┘ └────────────┘                │
│          │ [+] [🎙]              [ Gemini ▼ ] [Enviar]   │
└──────────┴──────────────────────────────────────────────┘
```

A barra inferior tem dois grupos: **anexo e microfone à esquerda**, **seletor de
IA e Enviar à direita**. O seletor fica imediatamente antes do Enviar porque
escolher a IA e mandar a mensagem são a mesma decisão; separá-los deixava um vão
morto no meio da barra.

Não existe mais faixa de cards de provider no topo, nem painel lateral direito
permanente. Toda a configuração vive no drawer.

## Composer

- **Textarea** que cresce com o conteúdo até 200 px e depois rola, para não
  empurrar a conversa.
- **Enter** envia; **Shift+Enter** quebra a linha.
- **Envio bloqueado** quando: está carregando, o provider ativo não é
  oferecível neste ambiente, ou um provider real ainda não foi autorizado.
- O motivo do bloqueio é **sempre visível** em `role="status"`, nunca silencioso.
- Mensagem só com anexo é válida. Como `ChatRequest.message` tem
  `min_length=1` no backend, o composer sintetiza um texto descritivo
  (`"Analise o conteúdo anexado: …"`) em vez de enviar string vazia e tomar 422.

## Seletor de IA

Fica na própria barra do composer, agrupado com o botão Enviar.

Lista **todas as IAs públicas conhecidas** — Gemini, OpenAI, Claude, DeepSeek e
Grok/xAI — e não só as utilizáveis. As indisponíveis aparecem como
`<option disabled>` com o motivo no rótulo:

```text
Gemini
OpenAI — não configurado
Claude — não configurado
DeepSeek — não configurado
Grok/xAI — não configurado
```

Isso evita o pior dos dois extremos: a IA some da lista (e o usuário não
descobre que ela existe) ou a IA é selecionável e devolve fallback silencioso.
Ela é visível, explicada e impedida de iniciar conversa.

Em desenvolvimento, `mock` é acrescido ao final com selo `DEV`. Enquanto o
provider ativo não for selecionável, o seletor mostra `Selecionar IA` em vez de
fingir que há uma IA escolhida — e o aviso do composer diz o motivo real
(`OpenAI não está disponível: configure a credencial no .env do backend.`).

Classificação completa em [[20-ux-v1/PROVIDERS_MODO_DEV]].

## Configurações (drawer)

Botão `⚙ Configurações` no canto superior direito do workspace.

`SettingsDrawer` é uma casca de **apresentação**: não conhece provider, modelo
nem autorização. Cuida de abrir, fechar, overlay, Escape e foco. Quem conhece o
domínio é o `ProviderSettingsPanel` injetado como `children`.

### Provedores de IA

A seção lista as **cinco IAs externas conhecidas**, cada uma com seu modelo
padrão e o estado factual vindo do backend:

```text
PROVEDORES DE IA

[ Gemini     gemini-3.5-flash    CONFIGURADO     ]
[ OpenAI     gpt-5.2-mini        NÃO CONFIGURADO ]
[ Claude     claude-sonnet-4-5   NÃO CONFIGURADO ]
[ DeepSeek   deepseek-chat       NÃO CONFIGURADO ]
[ Grok/xAI   grok-4.3            NÃO CONFIGURADO ]
```

Cards indisponíveis ficam esmaecidos, com borda tracejada e desabilitados —
visíveis e reconhecíveis, apenas inativos.

A área `Avançado — desenvolvimento` contém **somente infraestrutura interna**
(`Mock`, `Local QA`, `Local Model`, `Auto`) e só existe na build de
desenvolvimento. Nenhuma IA externa aparece ali.

Acessibilidade:

- `role="dialog"` + `aria-modal="true"`, rotulado pelo título;
- **Escape** fecha; clique no overlay fecha;
- foco inicial previsível no botão fechar;
- foco devolvido a quem abriu, ao fechar;
- fechado, o drawer **não existe no DOM** — nada dentro dele é alcançável por
  Tab nem lido por leitor de tela.

## Autorização de provider real

O consentimento persiste como **identificador do provider autorizado**, não como
booleano global:

```ts
authorizedRealProvider: string | null
```

Consequências, todas cobertas por teste:

- a autorização do Gemini **sobrevive ao F5**;
- autorização gravada para outro provider **não vale** para o Gemini;
- **trocar de IA descarta** a autorização anterior (menor privilégio).

No `ChatPage`, `allowRealProvider` é valor **derivado**, não estado: só vale se
o ID persistido corresponder ao provider atual, esse provider ainda for real e
ainda for oferecível. Qualquer condição caindo, o consentimento deixa de valer
sem sincronização manual.

## Chaves de API

Nunca são gravadas no navegador. O `localStorage` guarda apenas provider,
modelo, modo, prompt base e o **ID** do provider autorizado — consentimento, não
credencial. As credenciais permanecem exclusivamente no backend, lidas de
`.env` por `core/config.py`. Há teste explícito de que o payload persistido não
contém `api_key`, `apikey`, `secret` nem `token`.

## Renderização e XSS

`MessageBubble` renderiza o conteúdo como texto (`{message.content}`), com o
escape padrão do React. Não há `dangerouslySetInnerHTML`, `innerHTML`, `eval`
nem renderizador de Markdown em lugar nenhum de `apps/web/src` — verificado por
varredura. Nome de anexo e mensagem de erro seguem o mesmo caminho de texto.

## Responsividade

- ≤ 900 px: o console vira coluna única.
- ≤ 640 px: drawer ocupa a largura toda; a barra do composer quebra em linhas;
  o chip de anexo ocupa a linha inteira, dando espaço para o nome truncar sem
  provocar rolagem horizontal.
- `prefers-reduced-motion`: a pulsação do microfone é desligada; o estado
  continua legível por cor e por `aria-pressed`.

## Relacionados

- [[20-ux-v1/VOZ_E_ANEXOS]] — microfone e anexos.
- [[20-ux-v1/PROVIDERS_MODO_DEV]] — o que aparece no seletor.
- [[20-ux-v1/TESTES_FRONTEND]] — cobertura desta interface.
- [[20-ux-v1/PEDROCORE_V1_FINAL_CLOSURE_01]] — fechamento da frente.
