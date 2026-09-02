# Fix — Homologação e configuração de modelos

Frente: `PEDROCORE-MULTI-PROVIDER-SAFE-EVOLUTION`.

Status: **falhas confirmadas e corrigidas**.

Commits:

- `8c97004 — fix: separar homologacao e configuracao de modelos`;
- `0daa34b — docs: reconciliar binding explicito de modelos`.

## Falhas confirmadas

### Falha A — default runtime contaminava o catálogo

```text
adapter.default_model
→ modelo tratado como conhecido
→ homologação herdada do provider
```

Um identificador configurado podia entrar na caracterização sem uma definição
explícita própria.

### Falha B — binding incompleto chegava ao adapter

```text
default válido ausente
→ model=None
→ adapter escolhia seu default
```

Isso quebrava a garantia de que provider e modelo fossem aprovados como uma
unidade antes da execução.

## Correção

- `_MODEL_CATALOG` virou a fonte única e explícita dos modelos reconhecidos.
- Configuração runtime apenas seleciona um identificador candidato.
- Cada modelo declara provider proprietário, registro, implementação,
  homologação, autorização, default e compatibilidade com task.
- Provider homologado não homologa seus modelos.
- Posição no catálogo não cria default nem homologação.
- Default configurado precisa existir no catálogo, pertencer ao provider e
  estar marcado como `default_for_provider`.
- Binding inválido falha fechado antes do adapter.
- Adapter real recebe somente `binding.model_id`, nunca `model=None`.

## Resultado

Somente `gemini + gemini-3.5-flash` permanece homologado e autorizado para o
automático real. Claude/OpenAI continuam conhecidos, mas não homologados.

O checkpoint da correção registrou `515 passed, 7 skipped`, eval harness
`14/14` e zero chamadas externas reais.

## Links relacionados

- [[FECHAMENTO_ETAPAS_1_A_7]]
- [[ETAPA_1_CATALOGO_PROVIDERS]]
- [[ETAPA_3_PROVIDER_MODEL_BINDING]]
- [[ETAPA_4_SHADOW_MODE]]
- [[../MOC_MULTI_PROVIDER_SAFE_EVOLUTION]]
- [[../08_CHANGELOG]]
