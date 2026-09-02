# Providers na interface — público, interno e modo DEV

Mapa da frente: [[MOC_UX_V1]].

Este documento explica **quais providers a interface oferece como IA e por
quê**. A regra é de apresentação, não de domínio: nenhum provider foi removido
do sistema. Todos continuam registrados em `providers/registry.py`, roteáveis
pelo pipeline e disponíveis para os consumidores da API.

## O problema que esta frente corrigiu

A frente anterior escondeu os providers internos do composer público, mas
manteve-os clicáveis na área avançada do drawer. O resultado era incoerente:

```text
drawer  → usuário seleciona `mock`
composer → "Nenhuma IA selecionada", envio bloqueado
           e nenhuma autorização possível de conceder
```

O usuário conseguia escolher algo que o sistema depois recusava, sem caminho
para destravar. A correção não foi afrouxar o composer, e sim **alinhar as duas
telas à mesma regra**.

## Três estados, não um

A primeira versão desta regra colapsou conceitos diferentes numa lista só
(`["gemini"]`). O efeito colateral foi sumir com OpenAI, Claude, DeepSeek e
Grok da interface e empurrá-los para a área de infraestrutura interna — onde
não pertencem. São IAs externas conhecidas, apenas ainda indisponíveis.

A classificação correta tem **três estados independentes**:

| Estado | Significado | Fonte |
| --- | --- | --- |
| **VISÍVEL** | É uma IA pública que o Veltrix conhece. Aparece nas Configurações e no seletor, com ou sem chave. | `PUBLIC_AI_PROVIDER_IDS` |
| **CONFIGURADO** | O backend tem credencial para ela. | `configured` de `/api/providers` |
| **SELECIONÁVEL** | Pode iniciar conversa agora: visível **e** homologada **e** configurada. | derivado |

`provider público conhecido != provider utilizável`.

## Catálogo VISÍVEL — IAs externas

| Provider | Visível | Homologado | Configurado hoje | Selecionável |
| --- | --- | --- | --- | --- |
| `gemini` | sim | **sim** | sim | **sim** |
| `openai` | sim | não | não | não |
| `claude` | sim | não | não | não |
| `deepseek` | sim | não | não | não |
| `grok` | sim | não | não | não |

Uma IA indisponível **não some da tela**: aparece no card de Configurações com
o estado real (`Não configurado` / `Não homologado`) e no seletor como
`<option disabled>` com o motivo no rótulo — `OpenAI — não configurado`.
Escondê-la seria pior: o usuário não saberia que ela existe nem o que fazer para
habilitá-la.

## Infraestrutura interna — não são IAs

Ficam em `Avançado — desenvolvimento`, nunca junto das IAs públicas.

| Provider | Build pública | Build DEV | Motivo técnico |
| --- | --- | --- | --- |
| `mock` | **não** | destino de conversa | `MockProvider.generate_response` devolve texto para qualquer mensagem; `real_provider=False`, `is_configured=True`, sem rede, sem chave, sem opt-in. |
| `local_qa` | **não** | **não** | Cai em `LOCAL_PROVIDERS` e nunca chega a um adapter. O pipeline responde com o resumo do `qa_text_analyzer` sobre *artefatos* — análise determinística de release gate, não conversa. |
| `local_model` | **não** | **não** | `_execute_local_model` exige `allow_local_model=true` no payload **e** `PEDROCORE_ENABLE_LOCAL_MODEL=true` com backend local. O composer não envia esse opt-in e o default é OFF, então selecioná-lo produziria fallback Mock silencioso. |
| `auto` | **não** | **não** | É estratégia de roteamento, não uma IA. Exige `allow_real_provider=true` e resolve em Gemini. Apresentá-lo como modelo mentiria sobre quem respondeu. |

## Habilitação futura sem tocar no frontend

Como a selecionabilidade lê `configured` do backend, o fluxo de ativação é:

```text
chave adicionada no .env do backend
        ↓
GET /api/providers  →  configured = true
        ↓
frontend detecta sozinho
        ↓
provider deixa de ficar desabilitado
```

Nenhuma alteração de frontend é necessária para ativar uma IA já catalogada. A
única barreira restante seria a **homologação**, que é decisão de frente própria
— e o motivo exibido muda de `não configurado` para `não homologado`,
distinguindo o que o operador resolve do que depende de homologação.

## Onde a regra vive

`apps/web/src/utils/publicProviders.ts` — um único lugar:

- `PUBLIC_AI_PROVIDER_IDS` — as cinco IAs externas conhecidas (VISÍVEL)
- `HOMOLOGATED_PROVIDER_IDS = ["gemini"]` — espelho do `provider_catalog`
- `DEV_SELECTABLE_PROVIDER_IDS = ["mock"]` — internos aptos a chat em DEV
- `isSelectableProvider(provider, dev)` — o predicado composto
- `describeUnavailability(provider, dev)` — o motivo exibido
- `filterPublicAiProviders` / `filterInternalProviders` / `filterOfferedProviders`

O parâmetro `dev` é explícito e injetável justamente para ser testável nos dois
ambientes sem depender do modo em que a suíte roda.

### Por que a homologação está declarada no frontend

`GET /api/providers` expõe apenas `name`, `label`, `default_model`,
`configured` e `real_provider`. Ele **não** expõe `homologation`, que existe em
`provider_catalog/service.py`. Enquanto o contrato público não carregar esse
campo, `HOMOLOGATED_PROVIDER_IDS` fica declarada em um único módulo do
frontend, documentada como espelho da verdade do backend. Quando
`/api/providers` passar a expor homologação, `publicProviders.ts` deve passar a
lê-la e a constante some.

Note que **`configured` já vem do backend** — só a homologação é espelhada.
Isso é o que permite a habilitação automática descrita acima.

## Sinalização de ambiente técnico

Com `mock` ativo em desenvolvimento, a interface é explícita:

- selo `DEV` ao lado do seletor de IA, com destaque visual deliberadamente
  destoante da barra;
- aviso permanente no composer: *"Ambiente técnico de desenvolvimento: as
  respostas vêm do provider interno do pipeline, não de uma IA real."*

O `mock` **não** exige autorização de uso real, e isso é correto: ele não é
`real_provider`, não usa chave e não faz chamada externa. Não existe uso real a
consentir.

## Garantias da build pública

- `import.meta.env.DEV` é substituído por `false` no build, então
  `filterOfferedProviders` retorna apenas as IAs públicas.
- A seção "Avançado — desenvolvimento" do drawer é eliminada do bundle. Foi
  verificado no artefato gerado: as classes e textos dessa seção não estão em
  `dist/`.
- Coberto por teste: *"na build de produção o mock deixa de ser oferecido"* e
  *"na build de produção o padrão `mock` não conta como IA escolhida"*.

## Relacionados

- [[20-ux-v1/UX_COMPOSER_V1]] — como o composer aplica a regra.
- [[20-ux-v1/TESTES_FRONTEND]] — testes que travam este comportamento.
- [[MOC_MULTI_PROVIDER_SAFE_EVOLUTION]] — catálogo, binding e autorização.
- [[MOC_SEGURANCA]] — safe mode e providers reais.
