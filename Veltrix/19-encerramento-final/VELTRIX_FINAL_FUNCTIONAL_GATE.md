# Veltrix — Final Functional Gate

Data: 03/09/2026
Resultado: **VELTRIX FINALIZATION = PASS**
Estado: **VELTRIX FUNCTIONAL FREEZE = ACTIVE**
Homologação humana em uso real: **HUMAN_RUNTIME_ACCEPTANCE = PASS**

Este é o registro do último gate de manutenção comum do Veltrix. Ele corrige os
defeitos concretos observados na homologação humana e declara o congelamento
funcional do produto.

---

## 1. O defeito

Homologação real: Gemini configurado, homologado, selecionado, com uso real
autorizado no navegador. Pergunta enviada:

> "Me fale o que foi feito recentemente no sistema."

Resultado observado: `provider: mock`, `model: mock-v1`, `fallback usado`, e a
resposta genérica

> "No momento não foi possível obter uma resposta completa do provider
> solicitado. Isso não executa nenhuma ação financeira nem altera seus dados."

### Causa raiz — o que NÃO era

O trace completo de uma requisição real provou que a identidade e a autorização
estavam corretas:

```text
caller           local-unauthenticated
identity         local_trusted
role             technical_tool
environment      development
project_id       pedrocore
autorização      allowed (regra "uso técnico do próprio Veltrix")
provider pedido  gemini
provider chamado gemini   (1 chamada)
```

O adapter Gemini **era alcançado**, com a chave e o modelo corretos
(`gemini-3.5-flash`). Uma chamada real controlada confirmou o adapter
funcionando fim a fim. Nada em `caller_identity`, `provider_authorization`,
`provider_binding` ou `provider_catalog` estava errado.

### Causa raiz — o que era

`OrchestrationService._mock_fallback` substitui **qualquer** falha do provider
real por uma resposta do Mock, e a apresenta como resposta normal. Quando o
Gemini falha por razão externa e transitória — quota/429, indisponibilidade,
timeout — o pipeline devolve `provider="mock"`, `fallback_used=true`, `status="ok"`
e um texto genérico. A interface continuava mostrando "Gemini".

Ou seja: **a arquitetura não impedia a conversa; ela escondia a falha.** O
comportamento é correto para um consumer integrado (FinGuard não pode ficar sem
resposta), e errado para o chat interativo do próprio Veltrix, onde o usuário
escolheu explicitamente com qual IA quer falar.

Um segundo defeito veio junto: o texto do fallback carregava um disclaimer
**financeiro** em qualquer contexto, inclusive numa pergunta sobre o sistema.

---

## 2. A correção

Feita pelo contrato que **já existia**. Nenhum booleano novo, nenhum contrato
duplicado, nenhuma autorização enfraquecida, nenhum wildcard, Safe Mode intacto.

| Camada | Mudança |
| --- | --- |
| `apps/web/src/pages/ChatPage.tsx` | Quando o usuário escolhe uma IA **real** explicitamente, o chat envia `allow_mock_fallback: false` — opt-out restritivo que já existia em `ChatRequest`. |
| `apps/web/src/components/MessageBubble.tsx` | `provider="none"` deixa de ser renderizado como resposta: a bolha vira aviso de falha, nomeia a IA que falhou e retira as ações de opinião. |
| `apps/api/.../orchestration/service.py` | `_fallback_answers()` escolhe a mensagem pelo contexto: FinGuard mantém o disclaimer financeiro; chat geral recebe texto sem menção a dinheiro ou dados. |

**O default do contrato não mudou.** `allow_mock_fallback` continua `true`;
FinGuard, Elyra, Structa e demais consumers seguem com o fallback seguro e com o
disclaimer financeiro onde ele faz sentido.

### Semântica resultante no chat do Veltrix

| Situação | provider efetivo | fallback | O que a UI mostra |
| --- | --- | --- | --- |
| Gemini respondeu | `gemini` | `false` | a resposta do Gemini |
| Gemini falhou | `none` | `false` | "Gemini não concluiu a solicitação." |
| Provider interno (dev) | `mock` | `false` | resposta do Mock, rotulada `DEV` |

A interface passou a representar a realidade. Nunca mais uma resposta Mock é
apresentada como resposta da IA selecionada.

---

## 3. Correções visuais

| Defeito | Correção |
| --- | --- |
| Badge de status invadindo nome e modelo nos cards de provider | Layout em áreas de grid: `[ícone] nome / modelo` e o status em linha própria; uma coluna de cards no drawer; nome e modelo com truncamento explícito. |
| "Observabilidade QA/local" colidindo com o título "DIAGNÓSTICO LOCAL" | O link vira `inline-flex` com respiro vertical próprio; a mesma regra vale para rótulo e conteúdo de qualquer seção do painel. |
| Marcas genéricas de OpenAI e Claude | Glifos redesenhados e reconhecíveis, locais, sem CDN e sem dependência nova. |

Logos: auditados. Os cinco assets carregam e são exibidos corretamente; passaram
a ter `display: block`, `object-fit: contain` e dimensão explícita, em vez de
depender do comportamento default do elemento substituído.

Nenhum reposicionamento absoluto, nenhuma redução de fonte para "caber".

---

## 4. Verificação

Medição em Chrome headless sobre o **DOM real** do drawer aberto, comparando o
CSS antes e depois da correção:

```text
larguras 360 / 390 / 420 / 768 / 1366 / 1440 / 1920
ANTES  OVERLAP: dock-label x observability-link (todas as larguras)
       + colisão visível do badge sobre nome/modelo nos cards
DEPOIS ZERO OVERLAP / ZERO OVERFLOW-X / LOGOS EM ESCALA (todas as larguras)
```

Gates executados nesta frente:

```text
backend   pytest        2027 passed, 62 skipped
backend   ruff          All checks passed
backend   docs graph    176 documentos, 1029 links, zero órfãos, zero quebrados
frontend  vitest        122 passed
frontend  typecheck     PASS
frontend  build         PASS
smoke real Gemini       provider=gemini, fallback=false, resposta obtida
```

O smoke real usou uma única chamada com mensagem sintética. Nenhum dado
pessoal, nenhum anexo do usuário, nenhuma chave exposta.

Regressões protegidas e verificadas: upload de arquivo, áudio/transcrição, nova
conversa, histórico local, persistência de preferências, seleção de provider,
modos, prompt base, copiar, feedback, refazer, observabilidade, Mock, Local QA,
Local Model, Auto, contratos, FinGuard, Elyra, Structa.

---

## 4b. Homologação humana em uso real

**`HUMAN_RUNTIME_ACCEPTANCE = PASS` — 03/09/2026.**

Fato posterior ao commit desta frente: o Pedro exercitou o produto em execução,
não apenas a suíte. É a única evidência de que o gate funciona **em uso**, e não
somente em teste.

Observado por ele na interface:

- Gemini selecionado e indicado como configurado;
- uso real autorizado no navegador;
- resposta real retornada pelo Gemini;
- provider exibido como **Gemini**, não como Mock;
- modelo `gemini-3.5-flash`;
- nenhuma resposta Mock apresentada como se fosse da IA selecionada;
- cards de provider sem sobreposição;
- `CONFIGURADO` / `NÃO CONFIGURADO` sem invadir nome nem modelo;
- logos visíveis;
- layout de Configurações corrigido.

### Os dois aceites são coisas diferentes

| Aceite | O que prova | Quando |
|---|---|---|
| `HUMAN_VISUAL_ACCEPTANCE = PASS` | a **aparência** do produto foi aprovada — design, identidade, UX | antes do Public Release Gate |
| `HUMAN_RUNTIME_ACCEPTANCE = PASS` | o **fluxo funcional real** foi exercitado por uma pessoa e se comportou como a interface promete | após o Final Functional Gate |

O primeiro não implica o segundo: uma tela correta pode estar mentindo sobre
quem respondeu — foi exatamente esse o defeito que esta frente corrigiu.

Não há screenshot, hash ou artefato de evidência arquivado. A evidência é a
observação humana registrada acima, e este documento é o registro dela.

---

## 5. Regra de freeze

**VELTRIX FUNCTIONAL FREEZE = ACTIVE.**

A manutenção comum do Veltrix está encerrada. Após este gate, não se abre frente
nova para:

- trocar textos;
- mudar detalhes visuais pequenos;
- reorganizar arquitetura sem necessidade;
- refatorar porque "ficaria melhor";
- acrescentar opções cosméticas;
- reinventar painel;
- alterar documentação sem fato novo.

Reabrir o projeto exige responder **sim** a esta pergunta:

> Esta mudança aumenta uma capacidade real do Veltrix, ou é necessária para ele
> operar como núcleo de outro sistema?

Exemplos que justificam reabertura: nova capacidade de IA; nova capacidade de
orquestração; integração estrutural necessária a outro produto; memória ou
aprendizado; nova modalidade relevante; novo mecanismo de segurança ou
governança; uso do Veltrix como cérebro de outro sistema.

Se a resposta for não, **não reabrir**.

---

Entrada Obsidian: [[../MOC_VELTRIX]].
