# Testes frontend

Mapa da frente: [[MOC_UX_V1]].

Até esta frente o `apps/web` não tinha **nenhum** teste automatizado: a única
validação era `tsc -b` e `vite build`. Essa dívida foi paga aqui.

## Stack

| Pacote | Versão | Papel |
| --- | --- | --- |
| `vitest` | 4.1.10 | runner, integrado ao Vite existente |
| `jsdom` | 29.1.1 | ambiente DOM |
| `@testing-library/react` | 16.3.2 | render e consultas por papel/rótulo |
| `@testing-library/user-event` | 14.6.4 | interação |
| `@testing-library/jest-dom` | 7.0.1 | matchers de DOM |

**Todas as versões são exatas.** Nenhuma dependência nova usa `"latest"`.

> `jsdom` foi fixado em **29.1.1**, e não na 30.x, porque a 30 exige Node
> `^24.15.0` e o ambiente do projeto roda **24.13.0**. Fixar a 29 evita um
> `EBADENGINE` silencioso que só apareceria em CI.

A configuração vive em `vite.config.ts` usando `defineConfig` de
`vitest/config` — a mesma config do build real, acrescida do bloco `test`, para
não existir um segundo arquivo capaz de divergir.

## Comandos

```powershell
cd C:\Projetos\pedrocore-ia\apps\web
npm test          # vitest run
npm run typecheck # tsc -b
npm run build     # tsc -b && vite build
```

## Resultado atual — 2026-08-16

```text
Test Files  6 passed (6)
     Tests  117 passed (117)
```

Typecheck: **PASS**. Build: **PASS**.
Nenhum provider real é chamado: `sendChatMessage` e `getProviders` são sempre
substituídos por spy.

## Cobertura por arquivo

### `src/utils/publicProviders.test.ts`
As cinco IAs públicas (Gemini, OpenAI, Claude, DeepSeek, Grok) presentes no
catálogo visível, inclusive sem chave; ordem estável independente da ordem do
backend; a UI nunca inventa provider ausente do backend; `mock`, `local_qa`,
`local_model` e `auto` **fora** do catálogo público e agrupados como internos.

Selecionabilidade como predicado composto: Gemini configurado é selecionável;
Gemini sem chave deixa de sê-lo mas continua visível; as quatro não homologadas
não permitem envio real; provider configurado porém não homologado é distinguido
com o motivo correto; e um teste simula o backend passando a reportar
`configured=true` para verificar que o motivo migra de `não configurado` para
`não homologado` — a habilitação automática sem tocar no frontend.

Modo DEV: só `mock` liberado, ausente da build pública, e
`local_qa`/`local_model`/`auto` fora do composer nos dois ambientes.

### `src/utils/attachments.test.ts`
Saneamento de nome (caminho Windows/POSIX, `../`, caracteres de controle,
string vazia); allowlist e mapeamento para os tipos do backend; recusa de
formato, de extensão dupla, de MIME incoerente, de arquivo vazio e de arquivo
só com espaços; limite individual, limite de quantidade e cota total contando
anexos já presentes; decisão arquivo a arquivo; payload sem `metadata`; **teste
que trava os limites do frontend abaixo dos do backend**.

### `src/utils/providerSettings.test.ts`
Autorização sobrevive ao reload; guarda ID e não booleano; **nenhuma chave de
API no `localStorage`**; payload antigo lido como sem autorização; formatos
inválidos normalizados para `null`; JSON corrompido cai no default.

### `src/components/ChatComposer.test.tsx`
Enter envia, Shift+Enter quebra linha, vazio não envia, bloqueio do pai,
estado de carregamento; envio só com anexo; seletor mostrando `Selecionar IA`;
IA indisponível listada, desabilitada e com o motivo no rótulo; IA utilizável
habilitada; selo `DEV`; **seletor e Enviar no mesmo grupo**, sem os botões de
anexo/microfone; chips de anexo com nome/tamanho/tipo; **conteúdo do arquivo
nunca na tela**; remoção; limite atingido.

Microfone com a Web Speech API **mockada**: indisponível, construtor prefixado
`webkit`, início em `pt-BR`, transcrição final entregue ao textarea **sem envio
automático**, resultado interino ignorado, permissão negada, erro de rede,
cancelar (`abort`) e parar (`stop`).

> O construtor falso precisa ser `function`, não arrow: o hook faz
> `new Constructor()` e arrow function não é construtível.

### `src/components/SettingsDrawer.test.tsx`
Fechado não existe no DOM; `aria-modal` e nome acessível; Escape; overlay;
botão fechar; foco inicial no botão fechar; foco devolvido a quem abriu; sem
reação a Escape quando fechado.

### `src/pages/ChatPage.test.tsx`
Integração real da página: provider sem semântica de chat bloqueia; Gemini sem
autorização bloqueia; autorização sobrevive ao F5 e libera envio com
`allow_real_provider=true`; autorização de outro provider não vale; trocar de
IA descarta autorização; internos fora do seletor.

Modo DEV: envio ao `mock` **sem exigir autorização** — a regressão exata que
esta frente corrigiu — e, com `DEV=false`, o `mock` deixa de ser oferecido.

Catálogo: as cinco IAs públicas listadas no seletor; as sem chave desabilitadas
com o motivo; aviso factual em vez do genérico ("OpenAI não está disponível:
configure a credencial no `.env` do backend"); Gemini sem chave no backend deixa
de ser selecionável.

Configurações: as cinco IAs presentes na seção Provedores de IA mesmo sem chave;
quatro marcadas `Não configurado` e não clicáveis, Gemini `Configurado` e
clicável; **nenhuma IA pública na área de infraestrutura interna**, que contém
apenas Mock, Local QA, Local Model e Auto.

Anexos: envio como `artifacts` do contrato existente; recusa fora da allowlist;
limpeza após sucesso; **preservação após falha**; mensagem só com anexo
respeitando `min_length` do backend; remoção antes do envio.

## Notas de ambiente

- `Element.prototype.scrollIntoView` recebe um no-op no setup: o jsdom não
  implementa rolagem. É lacuna do ambiente de teste, não do produto.
- `vi.stubEnv("DEV", false)` simula a build pública; `unstubEnvs` e
  `restoreMocks` garantem que esse estado não vaze entre testes.
- Callbacks disparados pelo navegador (`onresult`, `onerror`) são invocados
  dentro de `act()`.

## Relacionados

- [[MOC_TESTES]] — suíte backend e testes opt-in.
- [[20-ux-v1/UX_COMPOSER_V1]] — o que está sob teste.
- [[20-ux-v1/PROVIDERS_MODO_DEV]] — regra travada pelos testes de provider.
