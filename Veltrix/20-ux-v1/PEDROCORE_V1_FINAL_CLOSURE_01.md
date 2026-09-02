# PEDROCORE-V1-FINAL-CLOSURE — RELATÓRIO FINAL

Mapa da frente: [[MOC_UX_V1]]. Data: 16/08/2026.

> **Adendo — `PEDROCORE-V1-FINAL-UI-FIX` (16/08/2026).** Após homologação visual
> humana, uma microcorreção ajustou a classificação dos providers e a posição do
> seletor. Onde este relatório disser que "somente Gemini é provider público",
> leia: **Gemini é a única IA pública habilitada/homologada para uso real**,
> enquanto OpenAI, Claude, DeepSeek e Grok continuam catalogadas e visíveis,
> porém indisponíveis até configuração/homologação. Números de teste do frontend
> passaram de 86 para **117**. Detalhes em [[20-ux-v1/PROVIDERS_MODO_DEV]] e no
> [[08_CHANGELOG]].

## 1. Veredito

**PASS COM RESSALVAS.**

Todos os gates técnicos passaram. A única ressalva é a ausência de `LICENSE`,
que é decisão humana/jurídica do proprietário e foi deliberadamente **não**
tomada pelo executor.

## 2. Estado Git inicial

```text
branch  main
HEAD    1b09cdd0464198b92d40169bdd842c85f7a80274
```

Working tree com os 8 arquivos da frente de UX anterior, todos autorizados:
6 modificados (`ChatComposer`, `ChatSidebar`, `ProviderSettingsPanel`,
`ChatPage`, `global.css`, `providerSettings`) e 2 não rastreados
(`SettingsDrawer.tsx`, `publicProviders.ts`).

**Nenhuma alteração desconhecida pré-existente.** `tsconfig.tsbuildinfo` estava
rastreado mas **não modificado**, então não houve artefato de build sujo a
restaurar.

## 3. Implementações concluídas

- Modo DEV coerente para providers internos.
- Ditado por voz no composer.
- Anexos textuais reais.
- Primeira suíte de testes do frontend.
- Fixação de todas as dependências do `apps/web`.
- Higiene do Git (`tsconfig.tsbuildinfo`).
- `SECURITY.md`, `CONTRIBUTING.md` e `README.md` público.
- Reconciliação documental e novo subgrafo `20-ux-v1/`.

**Backend intocado:** nenhum arquivo de `apps/api/` foi modificado.

## 4. UX final

Composer único com textarea autoajustável, seletor de IA na barra, `[+]` de
anexos, `[🎙]` de voz e botão Enviar. Configurações em drawer acessível.
Detalhes em [[20-ux-v1/UX_COMPOSER_V1]].

## 5. Microfone

`SpeechRecognition` / `webkitSpeechRecognition` com detecção em tempo de
execução, `pt-BR`, estados completos (disponível, ouvindo, finalizado, não
suportado, permissão negada, erro) e controles iniciar/parar/cancelar.

Áudio **não** é gravado, guardado, logado nem enviado ao Veltrix ou a
provider. A interface **não** afirma que a transcrição é offline — a Web Speech
API é interface, não promessa de implementação, e vários navegadores transcrevem
em nuvem própria. Nada é enviado automaticamente após transcrever.

Sem suporte, o botão fica desabilitado e explicado. Não há botão falso.

## 6. Anexos

`.txt`, `.md`, `.markdown`, `.csv`, `.json`, `.log` → `ArtifactInput` no campo
`artifacts` do `/api/chat` **já existente**. Nenhum endpoint novo.

Limites de 4 anexos / 20000 bytes por arquivo / 60000 bytes somados, todos
**abaixo** dos do backend, para que nada seja truncado em silêncio. Detalhes em
[[20-ux-v1/VOZ_E_ANEXOS]].

## 7. Multimodal

**Formalmente movido para a V2** — [[20-ux-v1/V2_MULTIMODAL]].

Motivo objetivo: `BaseAIProvider.generate_response(message, mode, model,
system_prompt)` só carrega texto. Suportar imagem exige mudar essa assinatura e,
com ela, os sete adapters — mudança estrutural, não aditiva. O adapter Gemini
não tem tratamento de `inline_data`/`parts`/`mime_type`, e o Prompt Builder
recebe `artifacts_text_block: str`.

A V1 **não é incompleta** por isso: o guard multimodal já existe, é honesto e
nunca envia imagem a provider.

## 8. Providers

*(Tabela corrigida por `PEDROCORE-V1-FINAL-UI-FIX`.)*

IAs externas públicas — **sempre visíveis**, com ou sem credencial:

| Provider | Visível | Homologado | Configurado | Selecionável |
| --- | --- | --- | --- | --- |
| `gemini` | sim | **sim** | sim | **sim** |
| `openai` | sim | não | não | não |
| `claude` | sim | não | não | não |
| `deepseek` | sim | não | não | não |
| `grok` | sim | não | não | não |

Infraestrutura interna — nunca junto das IAs públicas:

| Provider | DEV | Público | Papel |
| --- | --- | --- | --- |
| `mock` | selecionável | não | Fallback seguro e destino de conversa em DEV |
| `local_qa` | referência | não | Análise determinística de artefatos |
| `local_model` | referência | não | Opt-in default-off, sem transport real |
| `auto` | referência | não | Estratégia de roteamento |

Nenhum provider foi removido do sistema. A regra é de apresentação.

## 9. Modo DEV

**Defeito corrigido:** o drawer oferecia providers internos e o composer
bloqueava o envio com "Nenhuma IA selecionada", sem autorização possível de
conceder — becos sem saída para o usuário.

**Correção:** somente `mock` virou destino de conversa em desenvolvimento —
porque é o único interno que responde texto a mensagem arbitrária, sem rede,
sem chave e sem opt-in que a UI não envia. Recebe selo `DEV` e aviso de
ambiente técnico. Os demais internos passaram a ser exibidos como referência
**não selecionável**, com o motivo de cada um.

`mock` não exige autorização de uso real, e isso é correto: não é
`real_provider`, não há uso real a consentir. Justificativa completa em
[[20-ux-v1/PROVIDERS_MODO_DEV]].

## 10. Segurança

| Achado | Severidade | Correção | Estado |
| --- | --- | --- | --- |
| `apps/web/tsconfig.tsbuildinfo` rastreado apesar do `.gitignore` | Baixa | `git rm --cached`; arquivo local preservado | **Corrigido** |
| Dependências do `apps/web` em `"latest"` (build não reprodutível) | Média | Fixadas nas versões já instaladas, sem upgrade | **Corrigido** |
| Ausência de testes no frontend | Média | 86 testes | **Corrigido** |
| Drawer oferecia provider que o composer recusava | Média | Regra única de selecionabilidade | **Corrigido** |
| `AIza…` em `test_output_budget_observability.py` | — | Fixture `SECRET_LOOKING_KEY` preenchida com `DUMMY`, que testa a redação do sanitizador | **Falso positivo** |
| `/api/chat` sem autenticação | Alta **só no cenário D** | Documentado como requisito de deploy | **Aceito e documentado** |
| Sem rate limiting / teto de payload | Alta **só no cenário D** | Documentado como requisito de deploy | **Aceito e documentado** |
| 8 arquivos `.bak` locais de 20/06/2026 | Baixa | Não rastreados e cobertos por `.gitignore` | **Recomendação registrada** (§25) |

Sem achado de XSS: nenhum `dangerouslySetInnerHTML`, `innerHTML`, `eval` ou
`document.write` em `apps/web/src`.

## 11. Modelo de ameaça

| Cenário | Veredito |
| --- | --- |
| **A** — uso local | **SEGURO** |
| **B** — ecossistema local | **SEGURO** |
| **C** — código público no GitHub | **SEGURO** |
| **D** — API pública na internet | **NÃO SEGURO** — requisitos de deploy pendentes |

Detalhamento em [[20-ux-v1/MODELO_DE_AMEACA]].

## 12. Arquitetura

Preservada integralmente. Nenhum contrato congelado foi tocado: `/api/chat`,
`/api/orchestrate`, contratos FinGuard, `ChatRequest`, provider registry,
`provider=auto`, caller policies, binding, safe mode, fallback, circuit breaker,
adapters e normalização de resposta.

A única mudança de contrato foi **aditiva e no cliente**: o tipo TypeScript
`ChatRequest` passou a declarar `artifacts?`, campo que o backend já aceitava.

## 13. FinGuard

Intocado. Continua desacoplado dos providers: pede `provider=auto` sem escolher
modelo, não recebe nem repassa chaves, e o Veltrix resolve identidade,
autorização, provider e modelo. Homologação 4/4 preservada como evidência.

## 14. Structa

Intocado. Continua compatível: `registered` + `technical_tool` +
`qa_report_analysis` + Gemini + ambiente não produtivo. Coberto pelos 15 casos
de `test_structa_consumer_onboarding.py`, todos passando.

## 15. Testes frontend

```text
Test Files  6 passed (6)
     Tests  86 passed (86)
```

Vitest 4.1.10, jsdom 29.1.1, Testing Library — **versões exatas**. Cobre
providers e modo DEV, composer, persistência da autorização, drawer, microfone
(API mockada) e anexos. Nenhum provider real chamado. Detalhes em
[[20-ux-v1/TESTES_FRONTEND]].

## 16. Testes backend

```text
751 passed, 7 skipped, 2 warnings
```

Número **medido nesta sessão**, antes e depois das alterações. Os 7 skips são
os testes opt-in de recursos reais (`PEDROCORE_RUN_REAL_*_TESTS`), desligados
por padrão. Os 2 warnings são deprecations de biblioteca (Pydantic
`class Config`, Starlette TestClient), preexistentes e fora do escopo.

Nenhum provider real foi chamado; nenhum custo externo gerado.

## 17. Build/typecheck

```text
tsc -b       PASS
vite build   PASS (38 módulos, 236.90 kB js / 34.16 kB css)
```

Verificado no artefato de produção que a área técnica de providers internos é
**eliminada do bundle**.

## 18. Documentação auditada

**130 documentos** preexistentes no vault `Veltrix/`, mais `README.md` e
`VERSION.md` na raiz. Com os 8 criados nesta frente, o vault fechou em **138
documentos e 800 links resolvidos**. Classificação dos 130 auditados:

| Categoria | Aprox. | Exemplos |
| --- | --- | --- |
| **Canônico atual** | 15 | `09_STATUS_ATUAL`, `08_CHANGELOG`, MOCs, `README`, `VERSION` |
| **Histórico** | ~95 | `13-fechamento/*`, `10_V3_*` a `22_V5_1_9_*`, `04-comandos/V*` |
| **Precisava atualização** | 9 | corrigidos nesta frente (§19) |
| **Duplicado** | 2 pares | `03_ROADMAP.md` × `03-versoes/ROADMAP.md`; `09_STATUS_ATUAL.md` × `09-status/STATUS_ATUAL.md` |
| **Obsoleto** | 0 | nenhum documento foi classificado como fonte inválida |

Duplicados foram **preservados** por decisão explícita; o canônico prevalece e
está declarado como tal.

## 19. Documentos reconciliados

- `README.md` — reescrito como entrada pública do GitHub.
- `VERSION.md` — taxonomia das três numerações explicitada; produto → V5.2.0.
- `Veltrix/09_STATUS_ATUAL.md` — nova seção canônica; **proibição de
  alterar `apps/web` levantada** e explicada; "frontend preservado sem
  alteração" corrigido.
- `Veltrix/08_CHANGELOG.md` — entrada da frente + nota de convenção de
  caminhos `docs/`.
- `Veltrix/03-versoes/ROADMAP.md` — concluído movido para fora das
  pendências.
- `Veltrix/MOC_VELTRIX.md`, `MOC_TESTES.md`, `MOC_SEGURANCA.md`,
  `MOC_ESTUDO_PEDROCORE.md` — atualizados.

Criados: `SECURITY.md`, `CONTRIBUTING.md`, `MOC_UX_V1.md` e os seis documentos
de `20-ux-v1/`.

## 20. MOCs e links

Novo `MOC_UX_V1` ligado a partir do MOC raiz, em três pontos (seção canônica,
lista de mapas centrais e navegação rápida). Os seis documentos de `20-ux-v1/`
são alcançáveis a partir da raiz e apontam de volta para o mapa.

Referências obsoletas a `docs/…` foram corrigidas nos documentos de **navegação
canônica** (`09_STATUS_ATUAL`, `MOC_ESTUDO_PEDROCORE`) e **preservadas** nos
registros históricos, com nota de convenção no topo do changelog. Reescrever
`docs/` em um registro histórico o tornaria factualmente falso sobre a época que
descreve.

Validação final: **zero órfãos, zero links quebrados**.

## 21. Contradições resolvidas

1. Drawer oferecia provider que o composer recusava → regra única.
2. "Proibido alterar `apps/web`" enquanto a frente alterava `apps/web` → escopo
   datado e explicado.
3. "Frontend e design preservados sem alteração" → corrigido.
4. `V5.1.9` na documentação × UI com recursos novos → V5.2.0 com justificativa.
5. Documentação sem menção a testes frontend × 86 testes existentes → registrado.
6. Referências a `docs/` em documentos de navegação → corrigidas.
7. Roadmap listando como pendente o que acabara de ser entregue → movido.

## 22. Documentos históricos

Preservados e **identificáveis**: seções superadas trazem aviso explícito de
`(HISTÓRICO)` com ponteiro para o que as substituiu. Nenhum documento histórico
foi apagado ou reescrito para parecer refletir o estado atual.

## 23. README público

Reescrito: o que é, arquitetura, providers, recursos da V1, instalação,
configuração, execução, testes com números reais, integrações, segurança,
limitações e documentação. Sem caminhos da máquina do proprietário como
requisito — `C:\Projetos\pedrocore-ia` deixou de aparecer como pré-condição.

## 24. SECURITY.md

Criado: canal privado de reporte, modelo de segredos, postura de uso local,
distinção entre publicar código e publicar API, limitações de deploy e escopo
do que é ou não vulnerabilidade.

## 25. Git hygiene

- `apps/web/tsconfig.tsbuildinfo` **removido do rastreamento** com
  `git rm --cached`; o arquivo local foi preservado e o `.gitignore` já o cobria
  (`*.tsbuildinfo`).
- `.gitignore` já cobre `.venv/`, `node_modules/`, `dist/`, `__pycache__`,
  `.pytest_cache/`, `.ruff_cache/`, logs, `*.bak*` e `.env`. **Nenhuma regra
  nova foi necessária.**
- **8 arquivos `.bak`** (20/06/2026), todos não rastreados e ignorados:

```text
apps/api/app/modules/providers/mock_provider.py.bak-v2-0-1
apps/api/app/modules/providers/mock_provider.py.bak-v2-0-1-final
apps/api/app/modules/providers/mock_provider.py.bak-v2-0-1-fix
apps/api/app/modules/providers/mock_provider.py.bak-v2-0-2
apps/api/tests/test_chat.py.bak-v2-0-1-final
apps/web/src/pages/ChatPage.tsx.bak-v1.0.2
apps/web/src/pages/ChatPage.tsx.bak-v1.0.3
apps/web/src/styles/global.css.bak-v1.0.2
```

Classificação: **remover futuramente**. São cópias manuais anteriores ao uso
consistente do Git; o histórico já preserva esse conteúdo com mais fidelidade.
**Não foram apagados** — são locais, invisíveis ao GitHub e a remoção é decisão
do proprietário.

## 26. Secrets

Nenhum valor reproduzido neste relatório.

| Verificação | Resultado |
| --- | --- |
| `.env` rastreado no HEAD | **NÃO ENCONTRADO** |
| `.env` em todo o histórico Git | **NÃO ENCONTRADO** |
| `.pem`/`.key`/`.p12`/`.pfx`/`.db`/`.dump` no histórico | **NÃO ENCONTRADO** |
| Chave OpenAI / Anthropic / xAI / GitHub / AWS / bloco privado | **NÃO ENCONTRADO** |
| Padrão Google `AIza…` | **1 ocorrência — falso positivo** |

A ocorrência é `SECRET_LOOKING_KEY` em
`apps/api/tests/test_output_budget_observability.py`: literal preenchido com
`DUMMY` repetido, fixture sintética que verifica se o sanitizador redige strings
com formato de chave.

`apps/api/.env.example` contém apenas placeholders vazios e documentação;
credenciais permanecem exclusivamente no backend, em `.env` não versionado.

## 27. Versões

| Eixo | Antes | Depois |
| --- | --- | --- |
| Produto (UI) | V5.1.9 | **V5.2.0** |
| Técnica (API) | 0.2.0 | 0.2.0 (inalterado) |
| Tags Git | `v6.0.0`, `v7.0.0` | inalteradas — **nenhuma tag criada** |

`V5.2.0` é minor: recursos de interface sem quebra de contrato. `V6.0.0` foi
evitado deliberadamente para não colidir com a leitura da tag `v6.0.0`, que
marca o MVP backend. Nenhuma numeração histórica foi renumerada.

## 28. Roadmap após fechamento

Concluído e removido das pendências: interface pública, modo DEV, voz, anexos,
testes frontend, auditoria de segurança e reconciliação documental.

Permanece como futuro real: `LICENSE`, requisitos de deploy do cenário D, V2
multimodal, segundo provider homologado, transport real do `local_model`,
persistência da observabilidade e execução real de OCR/Playwright.

## 29. Pendências verdadeiras

1. **`LICENSE`** — bloqueia a publicação; é decisão humana.
2. **Requisitos do cenário D** — só se houver deploy público.
3. **V2 multimodal** — escopo definido, não iniciado.
4. **Segundo provider homologado** — decisão de produto.
5. **8 arquivos `.bak`** — limpeza local recomendada, sem impacto no GitHub.

Não há pendência técnica bloqueante para a homologação humana final.

## 30. Decisões humanas

- **Licença.** Não foi criada nenhuma. Sem `LICENSE`, o padrão legal é "todos
  os direitos reservados". Escolher entre MIT, Apache-2.0, GPL ou proprietária é
  decisão jurídica do proprietário, e o executor não deve tomá-la por ele.
- **Publicar ou não no GitHub**, e sob qual conta.
- **Remover ou preservar** os arquivos `.bak`.
- **Criar a tag** do fechamento, se desejada.

## 31. Aprendizado

1. **Coerência de estado** — se uma tela oferece uma opção, a outra precisa
   aceitá-la; beco sem saída é defeito, não detalhe.
2. **Contrato existente antes de endpoint novo** — anexos couberam inteiros no
   campo `artifacts` que já existia.
3. **Limite do cliente abaixo do limite do servidor** — recusar é mais honesto
   que truncar em silêncio.
4. **Invariante de codificação como validação barata** — em UTF-8
   `chars <= bytes`, então checar bytes antes de ler o arquivo já garante o teto
   de caracteres do backend.
5. **Feature detection, não suposição** — a Web Speech API é interface, não
   promessa de implementação.
6. **Honestidade sobre privacidade** — não afirmar "offline" o que o navegador
   pode processar em nuvem.
7. **Extensão como autoridade, MIME como sinal** — `File.type` vem do cliente.
8. **Nome de arquivo é metadado, nunca caminho.**
9. **Consentimento por identificador, não booleano** — impede a autorização de
   vazar entre providers.
10. **Valor derivado em vez de estado** — `allowRealProvider` não precisa de
    sincronização manual.
11. **Ambiente injetável = ambiente testável** — o parâmetro `dev` explícito
    permitiu testar build pública e de desenvolvimento na mesma suíte.
12. **Versão exata em dependência nova** — e `jsdom` fixado pela versão do Node
    disponível, não pela mais recente.
13. **Preservar história é diferente de manter contradição** — o histórico fica,
    marcado como histórico; o canônico é corrigido.
14. **Validador de documentação é teste de verdade** — pegou seis links
    quebrados que eu havia criado por referência antecipada.
15. **Adiar com escopo escrito é entrega** — "V2 multimodal" com lacunas e
    arquitetura definidas vale mais que uma implementação forçada.

## 32. Git final

```text
branch  main
HEAD    1b09cdd0464198b92d40169bdd842c85f7a80274   (inalterado — nenhum commit criado)
```

Working tree preparada para revisão humana: 19 arquivos modificados,
`tsconfig.tsbuildinfo` removido do índice e os novos arquivos de código,
teste e documentação como não rastreados.

Nenhum commit, tag, push, release ou deploy foi feito.

## 33. Veredito de propósito

| # | Pergunta | Resposta |
| --- | --- | --- |
| 1 | Cumpre a proposta original? | **Sim.** É de fato o gateway/orquestrador do ecossistema. |
| 2 | Está operacional? | **Sim**, local e para consumidores locais. |
| 3 | Seguro para uso local? | **Sim.** |
| 4 | Preparado para vários projetos? | **Sim** — novo consumidor entra por registry e política, sem código novo. |
| 5 | FinGuard continua funcionando? | **Sim**, intocado; homologação 4/4 preservada. |
| 6 | Structa continua compatível? | **Sim**, intocado; 15 testes passando. |
| 7 | Providers internos isolados da UI pública? | **Sim** — verificado inclusive no bundle de produção. |
| 8 | Gemini continua homologado? | **Sim**, único homologado e autorizado para `auto`. |
| 9 | Documentação representa o código real? | **Sim**, após esta reconciliação. |
| 10 | Grafo documental reconciliado? | **Sim.** |
| 11 | Links canônicos quebrados? | **Não** — zero. |
| 12 | Testes atuais passaram? | **Sim** — backend 751, frontend 86, typecheck e build PASS. |
| 13 | Código pronto para o GitHub? | **Sim, tecnicamente.** Falta a decisão de licença. |
| 14 | API pronta para a internet? | **Não** — ver §11. |
| 15 | Bloqueio técnico para homologação humana? | **Não.** |
| 16 | O que falta obrigatoriamente antes de publicar? | **`LICENSE`.** Só isso. |
| 17 | O que ficou para a V2? | Multimodal, segundo provider homologado, requisitos de deploy público, transport real do `local_model` e persistência da observabilidade. |

## Relacionados

- [[MOC_UX_V1]] — mapa da frente.
- [[20-ux-v1/UX_COMPOSER_V1]] · [[20-ux-v1/VOZ_E_ANEXOS]] ·
  [[20-ux-v1/PROVIDERS_MODO_DEV]]
- [[20-ux-v1/TESTES_FRONTEND]] · [[20-ux-v1/MODELO_DE_AMEACA]] ·
  [[20-ux-v1/V2_MULTIMODAL]]
- [[09_STATUS_ATUAL]] · [[08_CHANGELOG]] · [[MOC_VELTRIX]]
