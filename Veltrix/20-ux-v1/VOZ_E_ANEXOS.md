# Voz e anexos textuais

Mapa da frente: [[MOC_UX_V1]].

Dois recursos novos do composer, ambos **inteiramente do lado do navegador** no
que diz respeito a captura, e ambos entrando no backend apenas por contratos
que já existiam.

---

# 1. Ditado por voz

## Fluxo

```text
[🎙]
  ↓ permissão do navegador
usuário fala
  ↓ transcrição
texto ANEXADO ao textarea
  ↓
usuário revisa e edita
  ↓
usuário envia — nunca automático
```

Implementação: `apps/web/src/hooks/useSpeechRecognition.ts`.

## O que NÃO acontece

- áudio **não** é gravado;
- áudio **não** é guardado em memória, `localStorage` ou disco;
- áudio **não** é enviado ao backend do Veltrix;
- áudio **não** é enviado a nenhum provider;
- áudio **não** aparece em log.

O hook recebe do navegador apenas **texto já transcrito**. Áudio nunca passa
por código nosso.

## Honestidade sobre a transcrição

A Web Speech API é uma **interface**, não uma promessa de implementação. O
navegador decide como reconhece a fala, e vários — Chrome e Edge entre eles —
fazem isso enviando o áudio a um serviço de nuvem do próprio fornecedor.

Portanto a documentação e a interface **não afirmam que a transcrição é
offline**. O aviso mostrado durante a escuta diz exatamente isto:

> Ouvindo. A transcrição é feita pelo navegador e pode ser processada por um
> serviço do fornecedor dele; o áudio não é gravado nem enviado ao Veltrix.

## Detecção de suporte

Em tempo de execução, na ordem `SpeechRecognition` → `webkitSpeechRecognition`.
O prefixo `webkit` não é legado: é o único caminho em navegadores Chromium, ou
seja, o caso mais comum.

Sem suporte, o botão fica **desabilitado e explicado**
(`"Ditado por voz indisponível neste navegador"`). Não existe botão falso.

## Estados

| Estado | Interface |
| --- | --- |
| `idle` | botão disponível |
| `listening` | botão pulsando, `aria-pressed=true`, aviso de escuta, botão Cancelar |
| `denied` | `role="alert"` com "Permissão de microfone negada pelo navegador." |
| `error` | `role="alert"` com a causa (rede, sem microfone, sem fala) |
| `unsupported` | botão desabilitado com rótulo explicativo |

## Controles

- **Iniciar** — `recognition.start()`
- **Parar** — `recognition.stop()`: encerra **mantendo** o que foi transcrito
- **Cancelar** — `recognition.abort()`: encerra **descartando** o trecho

`aborted` é cancelamento pedido pelo próprio usuário e volta ao repouso em
silêncio, sem apresentar um erro que ele mesmo causou.

Só trechos **finais** entram no textarea: resultado interino muda sozinho e
reescreveria o que o usuário estivesse editando. A transcrição é **anexada** ao
texto existente, nunca o substitui.

Ao desmontar o componente, o reconhecimento é abortado — sem isso o navegador
seguiria com o microfone aberto.

Idioma inicial: `pt-BR`.

---

# 2. Anexos textuais

## Fluxo

```text
[+] → seleção → validação → leitura (File API) → chip
                    ↓ recusa explicada
      envio como `artifacts` no /api/chat já existente
```

Implementação: `apps/web/src/utils/attachments.ts`.

## Nenhum endpoint novo

Um anexo vira um `ArtifactInput` no campo `artifacts` que o `POST /api/chat`
**já aceita** desde a frente de artefatos — o mesmo contrato usado por FinGuard
e Structa. O backend não foi tocado.

```ts
{ type: "markdown", name: "notas.md", content: "# Título" }
```

`metadata` é **deliberadamente ausente**: o backend rejeita o artefato inteiro
ao encontrar chave de caminho (`path`, `file_path`, `directory`, …) em
`PATH_LIKE_METADATA_KEYS`, e não há nada a enviar além de nome e conteúdo.

## Allowlist por extensão

| Extensão | `type` do artefato |
| --- | --- |
| `.txt` | `text` |
| `.md`, `.markdown` | `markdown` |
| `.csv` | `text` |
| `.json` | `json_result` |
| `.log` | `log` |

Os tipos são os que `TEXT_ARTIFACT_TYPES` do backend já reconhece. `.csv` entra
como `text` — e não como um tipo inventado — para não disparar
`ARTIFACT_TYPE_UNKNOWN`.

A **extensão é a autoridade**, não o MIME: `File.type` vem do sistema
operacional, é facilmente vazio e não serve como controle de segurança. O MIME é
usado apenas como sinal adicional; vazio conta como confiável, porque é o que o
próprio navegador informa quando não sabe.

## Limites, e por que estes

| Limite | Valor | Backend correspondente |
| --- | --- | --- |
| Anexos por mensagem | 4 | `MAX_ARTIFACTS = 10` |
| Bytes por arquivo | 20000 | `MAX_ARTIFACT_CONTENT_CHARS = 20000` |
| Bytes somados | 60000 | `MAX_TOTAL_ARTIFACT_CHARS = 100000` |

O backend **trunca** o que passa dos limites, com warning — não rejeita. Truncar
em silêncio é pior do que recusar: o usuário veria o arquivo aceito e a IA
responderia sobre metade dele. Por isso os limites do frontend ficam
estritamente **abaixo** dos do backend, e a checagem é feita em **bytes antes da
leitura**: em UTF-8 todo caractere ocupa ao menos um byte, logo
`bytes <= 20000` garante `chars <= 20000` sem precisar ler o arquivo.

Há teste que trava essa relação: se alguém afrouxar um limite do frontend acima
do teto do backend, a suíte quebra.

## Segurança dos anexos

- allowlist explícita por extensão; extensão dupla (`relatorio.md.exe`) resolve
  para `.exe` e é recusada;
- MIME incoerente recusa mesmo com extensão permitida;
- arquivo vazio e arquivo só com espaços são recusados;
- limites de quantidade e de tamanho total contam os anexos **já presentes**;
- `sanitizeFileName` descarta qualquer componente de caminho (`/`, `\`) e
  caracteres de controle — o nome é **metadado**, nunca é usado para abrir,
  resolver ou construir caminho algum;
- o conteúdo **nunca é executado nem interpretado como HTML**: é string enviada
  ao backend e, na tela, só o nome aparece;
- decisão **arquivo a arquivo** — um recusado não derruba os válidos da mesma
  seleção, e o motivo de cada recusa é dito ao usuário;
- anexos vivem **apenas na mensagem atual**: não são persistidos no histórico
  local nem restaurados no F5;
- são limpos **somente no sucesso**; falhando o envio, permanecem no composer
  para reenvio sem reescolher os arquivos.

## Interface

Cada anexo é um chip com **nome, tamanho e tipo**, mais um botão de remover
rotulado (`"Remover anexo notas.md"`). O **conteúdo do arquivo nunca é exibido**
— há teste que garante isso.

## Relacionados

- [[20-ux-v1/UX_COMPOSER_V1]] — onde os dois recursos aparecem.
- [[20-ux-v1/V2_MULTIMODAL]] — por que imagem e PDF ficaram fora.
- [[20-ux-v1/TESTES_FRONTEND]] — cobertura de voz e anexos.
- [[10-contratos/CONTRATOS_TECNICOS_PEDROCORE]] — contrato de artefatos.
