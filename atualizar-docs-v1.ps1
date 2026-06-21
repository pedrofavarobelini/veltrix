$ProjectRoot = "C:\Projetos\pedrocore-ia"

if (!(Test-Path $ProjectRoot)) {
    throw "Projeto não encontrado em C:\Projetos\pedrocore-ia"
}

Set-Location $ProjectRoot

if ((Get-Location).Path -like "*FinGuard*") {
    throw "ERRO: você está dentro do FinGuard. Pare agora."
}

$DocsPath = Join-Path $ProjectRoot "docs"
$Now = Get-Date -Format "dd/MM/yyyy HH:mm:ss"

New-Item -ItemType Directory -Path $DocsPath -Force | Out-Null
New-Item -ItemType Directory -Path "$DocsPath\historico" -Force | Out-Null
New-Item -ItemType Directory -Path "$DocsPath\erros" -Force | Out-Null
New-Item -ItemType Directory -Path "$DocsPath\versoes" -Force | Out-Null
New-Item -ItemType Directory -Path "$DocsPath\comandos" -Force | Out-Null

Set-Content -Path "$DocsPath\00_PLANEJAMENTO.md" -Encoding UTF8 -Value @"
# PedroCore IA — Planejamento Geral

Atualizado em: $Now

## Objetivo

O PedroCore IA é uma API/assistente pessoal de inteligência artificial criado para testar respostas, qualidade, contexto, escrita, comportamento e formato das respostas de IA.

O objetivo não é treinar uma IA do zero. O objetivo é criar uma camada própria de uso e controle de IA, permitindo futuramente conexão com outros projetos, como o FinGuard, sem misturar os códigos.

## Local oficial

Caminho correto:

    C:\Projetos\pedrocore-ia

Estrutura correta:

    C:\Projetos
      FinGuard
      pedrocore-ia

Estrutura errada:

    C:\Projetos\FinGuard\pedrocore-ia

## Regras principais

1. PedroCore IA fica em C:\Projetos\pedrocore-ia.
2. FinGuard fica separado em C:\Projetos\FinGuard.
3. PedroCore IA e FinGuard são projetos irmãos.
4. Nenhum comando do PedroCore IA deve ser executado dentro do FinGuard.
5. Todos os comandos devem ser enviados em blocos PowerShell organizados.
6. Toda alteração, erro, correção e decisão deve ser documentada.
7. A V1 deve ser simples e funcional.
8. Não adicionar banco, login, RAG, dashboard ou multi-provider na V1.
9. Evoluir por versões controladas.
10. Sempre registrar versão atual e próximas versões.

## Escopo da V1

A V1 entrega:

- Backend Python com FastAPI.
- Endpoint GET /health.
- Endpoint POST /api/chat.
- Provider mock.
- Frontend React com Vite e TypeScript.
- Interface simples de chat.
- Botão enviar.
- Botão copiar.
- Botão refazer.
- Botão gostei/não gostei.
- Painel de configurações simples.
- Prompt base editável.

## Fora do escopo da V1

- Banco de dados.
- Login.
- Histórico persistido.
- RAG.
- Gemini real.
- OpenAI real.
- Multi-provider.
- Integração direta com FinGuard.
- Deploy.
- Dashboard avançado.
"@

Set-Content -Path "$DocsPath\01_STACK.md" -Encoding UTF8 -Value @"
# PedroCore IA — Stack Técnica

Atualizado em: $Now

## Backend

- Python
- FastAPI
- Uvicorn
- Pydantic
- pydantic-settings
- python-dotenv
- Pytest
- Ruff
- HTTPX
- uv

## Frontend

- React
- Vite
- TypeScript
- CSS puro
- npm

## Futuro

- PostgreSQL
- pgvector
- SQLAlchemy ou SQLModel
- Alembic
- Gemini API
- OpenAI API
- Claude API
- DeepSeek API
- Grok API

## Justificativa

Python foi escolhido para o backend porque o projeto é focado em IA e também servirá como aprendizado prático de Python.

React com TypeScript foi mantido no frontend porque é adequado para uma interface web simples e já é uma stack conhecida.

## Decisão importante

A V1 começa com MockProvider, não com Gemini real.

Motivos:

- Evita travar o projeto por erro de chave de API.
- Permite testar frontend e backend primeiro.
- Garante que a comunicação local funciona.
- Reduz complexidade inicial.

## Ferramentas detectadas no PC

Durante o primeiro teste local:

- Python: 3.14.2
- Node: v24.13.0
- npm: 11.17.0
- uv: não encontrado
- pip: não encontrado no PATH

## Problema atual

O Python está instalado, mas pip e uv não foram reconhecidos no PowerShell.

Correção planejada:

    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
"@

Set-Content -Path "$DocsPath\02_DESIGN.md" -Encoding UTF8 -Value @"
# PedroCore IA — Design

Atualizado em: $Now

## Decisão de design

O primeiro design gerado ficou avançado demais, com cara de dashboard/SaaS.

Decisão final:

A interface deve ser simples, pessoal e intuitiva, porque será usada principalmente pelo Pedro para testar qualidade de resposta da IA.

## Design aprovado

Tipo:

- Chat simples pessoal.

Elementos principais:

- Cabeçalho com nome PedroCore IA.
- Seletor de modo.
- Seletor de modelo.
- Botão de configurações.
- Área de conversa.
- Campo de mensagem.
- Botão enviar.
- Botão copiar.
- Botão refazer.
- Botão gostei.
- Botão não gostei.
- Painel simples de configurações.

## Objetivo da interface

Testar:

- Forma da resposta.
- Clareza.
- Contexto.
- Qualidade da escrita.
- Erros graves.
- Se a resposta está útil.
- Se o prompt base está funcionando.
- Se o backend está retornando corretamente.

## Removido do design inicial

- Sidebar grande.
- Dashboard avançado.
- Métricas exageradas.
- Gráficos.
- Inspector lateral fixo.
- Comparação de modelos.
- Tela de logs visual.
- Tela complexa de avaliação.
- Multiusuário.
- Login.

## Veredito

O design aprovado para a V1 é um chat pessoal simples para teste de resposta.
"@

Set-Content -Path "$DocsPath\03_ROADMAP.md" -Encoding UTF8 -Value @"
# PedroCore IA — Roadmap

Atualizado em: $Now

## V1 — Chat simples + API mock

Status: atual.

Objetivo:

- Criar base funcional.
- Rodar backend.
- Rodar frontend.
- Testar comunicação frontend/backend.
- Validar design simples.
- Usar MockProvider.

## V2 — Integração real com Gemini

Status: próxima.

Objetivo:

- Conectar IA real.
- Usar chave GEMINI_API_KEY.
- Manter MockProvider como fallback.
- Tratar erro de API key.
- Tratar erro de quota.
- Tratar erro de rede.

## V3 — Histórico simples + gostei/não gostei salvo

Status: pendente.

Objetivo:

- Guardar histórico local.
- Registrar feedback de resposta.
- Salvar gostei/não gostei.
- Registrar observações básicas.

## V4 — Prompts por modo

Status: pendente.

Objetivo:

- Criar prompts específicos para modo normal, técnico, resumido e código.
- Melhorar comportamento da resposta.
- Permitir prompt base mais organizado.

## V5 — API interna para conexão com FinGuard

Status: pendente.

Objetivo:

- Criar endpoint seguro para outros projetos.
- Permitir que FinGuard chame PedroCore IA.
- Não misturar código dos projetos.
- Usar API separada.

## V6 — PostgreSQL + logs

Status: pendente.

Objetivo:

- Criar banco.
- Salvar chamadas.
- Salvar respostas.
- Salvar erros.
- Salvar provider/modelo usado.

## V7 — RAG/memória com documentos

Status: pendente.

Objetivo:

- Cadastrar documentos.
- Quebrar em chunks.
- Criar embeddings.
- Buscar contexto por similaridade.
- Responder com base em documentação.

## V8 — Multi-provider

Status: pendente.

Objetivo:

- Gemini.
- OpenAI.
- Claude.
- DeepSeek.
- Grok.
- Fallback entre provedores.

## V9 — Deploy/documentação final

Status: pendente.

Objetivo:

- Preparar projeto para GitHub.
- Documentação final.
- Prints.
- README profissional.
- Deploy opcional.
"@

Set-Content -Path "$DocsPath\04_COMANDOS.md" -Encoding UTF8 -Value @"
# PedroCore IA — Comandos PowerShell

Atualizado em: $Now

## Regra principal

Todos os comandos devem ser executados em blocos separados.

Nunca misturar backend e frontend no mesmo terminal.

## Caminho oficial

    cd C:\Projetos\pedrocore-ia

## Conferir estrutura

    dir

Resultado esperado:

    apps
    docs
    README.md
    VERSION.md
    COMANDOS_POWERSHELL.md

## Verificar ferramentas

    python --version
    node -v
    npm -v
    uv --version

## Instalar uv

    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

Depois fechar e abrir o PowerShell novamente.

## Terminal 1 — Backend

    cd C:\Projetos\pedrocore-ia\apps\api
    uv sync
    uv run pytest
    uv run uvicorn app.main:app --reload --port 3333

## Testar backend no navegador

    http://localhost:3333/health
    http://localhost:3333/docs

## Testar API no PowerShell

    Invoke-RestMethod -Uri "http://localhost:3333/health" -Method GET

## Terminal 2 — Frontend

    cd C:\Projetos\pedrocore-ia\apps\web
    npm install
    npm run dev

## Abrir frontend

    http://localhost:5173
"@

Set-Content -Path "$DocsPath\05_TESTES.md" -Encoding UTF8 -Value @"
# PedroCore IA — Testes da V1

Atualizado em: $Now

## Objetivo

Validar que a V1 funciona localmente.

## Teste de estrutura

Comando executado:

    cd C:\Projetos\pedrocore-ia
    dir

Resultado obtido:

    apps
    docs
    .gitignore
    COMANDOS_POWERSHELL.md
    README.md
    VERSION.md

Status:

    OK

## Testes de ferramentas

Resultados obtidos:

    python --version => Python 3.14.2
    node -v => v24.13.0
    npm -v => 11.17.0
    uv --version => erro, uv não reconhecido
    pip install uv => erro, pip não reconhecido

Status:

    Parcial

## Teste pendente — instalar uv

Comando planejado:

    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

## Testes pendentes do backend

Após uv funcionar:

    cd C:\Projetos\pedrocore-ia\apps\api
    uv sync
    uv run pytest
    uv run uvicorn app.main:app --reload --port 3333

## Testes pendentes no navegador

    http://localhost:3333/health
    http://localhost:3333/docs

## Testes pendentes do frontend

    cd C:\Projetos\pedrocore-ia\apps\web
    npm install
    npm run dev

Abrir:

    http://localhost:5173

## Teste funcional esperado

Mensagem:

    Explique o que é FastAPI nesse projeto.

Resultado esperado:

    Resposta simulada do MockProvider.

## Checklist V1

- [x] Pasta correta validada.
- [x] Estrutura raiz validada.
- [x] Python encontrado.
- [x] Node encontrado.
- [x] npm encontrado.
- [ ] uv instalado.
- [ ] Dependências backend instaladas.
- [ ] Pytest passou.
- [ ] Backend rodando.
- [ ] /health funcionando.
- [ ] /docs funcionando.
- [ ] Frontend instalado.
- [ ] Frontend rodando.
- [ ] Chat enviando mensagem.
- [ ] Resposta aparecendo.
- [ ] Botões básicos funcionando.
"@

Set-Content -Path "$DocsPath\06_ERROS_E_CORRECOES.md" -Encoding UTF8 -Value @"
# PedroCore IA — Erros e Correções

Atualizado em: $Now

## Erro 001 — ZIP com pasta raiz incorreta

Situação:

O primeiro ZIP gerado tinha risco de criar estrutura bagunçada.

Risco:

    C:\Projetos\pedrocore-ia-v1

em vez de:

    C:\Projetos\pedrocore-ia

Correção:

Foi gerado um ZIP revisado com apenas uma pasta raiz:

    pedrocore-ia

Status:

    Corrigido.

## Erro 002 — Caminho do projeto mal interpretado

Situação:

Foi considerado incorretamente que o projeto ficaria em outra pasta.

Correção:

Caminho oficial definido:

    C:\Projetos\pedrocore-ia

FinGuard fica em:

    C:\Projetos\FinGuard

Status:

    Corrigido.

## Erro 003 — uv não reconhecido

Comando executado:

    uv --version

Erro:

    uv : O termo 'uv' não é reconhecido como nome de cmdlet, função, arquivo de script ou programa operável.

Diagnóstico:

O uv ainda não está instalado ou não está no PATH do Windows.

Correção planejada:

    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

Depois fechar e abrir o PowerShell.

Status:

    Pendente.

## Erro 004 — pip não reconhecido

Comando executado:

    pip install uv

Erro:

    pip : O termo 'pip' não é reconhecido como nome de cmdlet, função, arquivo de script ou programa operável.

Diagnóstico:

O Python está instalado, mas pip não está acessível diretamente pelo PowerShell.

Alternativa:

    python -m ensurepip --upgrade
    python -m pip --version
    python -m pip install uv

Status:

    Pendente.

## Erro 005 — Documentação incompleta

Situação:

A documentação inicial existia, mas não registrava cada etapa no nível exigido.

Correção:

Criados/atualizados documentos:

- 00_PLANEJAMENTO.md
- 01_STACK.md
- 02_DESIGN.md
- 03_ROADMAP.md
- 04_COMANDOS.md
- 05_TESTES.md
- 06_ERROS_E_CORRECOES.md
- 07_DECISOES_TECNICAS.md
- 08_CHANGELOG.md
- 09_STATUS_ATUAL.md

Status:

    Corrigido a partir desta etapa.
"@

Set-Content -Path "$DocsPath\07_DECISOES_TECNICAS.md" -Encoding UTF8 -Value @"
# PedroCore IA — Decisões Técnicas

Atualizado em: $Now

## Decisão 001 — Não treinar IA do zero

O projeto não vai treinar um modelo próprio.

Decisão:

    Criar uma API/camada de orquestração de IA.

Motivo:

- Treinar IA do zero é caro.
- Não é necessário para o objetivo.
- O foco é usar provedores de IA com controle próprio.

## Decisão 002 — Backend em Python

Decisão:

    Usar Python + FastAPI no backend.

Motivos:

- Projeto é focado em IA.
- Python é útil para aprendizado.
- Pedro vai estudar Python na faculdade.
- Diversifica o portfólio além de TypeScript.

## Decisão 003 — Frontend em React + TypeScript

Decisão:

    Usar React + Vite + TypeScript.

Motivos:

- Interface simples.
- Stack conhecida.
- Melhor para painel web.
- Evita usar Streamlit/Gradio na V1.

## Decisão 004 — V1 com MockProvider

Decisão:

    Começar com provider mock.

Motivos:

- Evita travar com chave de API.
- Testa fluxo primeiro.
- Garante backend/frontend funcionando.
- Gemini real fica para V2.

## Decisão 005 — Sem banco na V1

Decisão:

    Não usar banco na V1.

Motivos:

- Reduz complexidade.
- Primeiro objetivo é validar base.
- Banco entra na V6.

## Decisão 006 — Design simples

Decisão:

    Chat simples pessoal.

Motivos:

- Projeto será usado pelo Pedro.
- Objetivo é testar qualidade de resposta.
- Dashboard avançado seria excesso.

## Decisão 007 — Projetos separados

Decisão:

    FinGuard e PedroCore IA são projetos irmãos dentro de C:\Projetos.

Estrutura:

    C:\Projetos\FinGuard
    C:\Projetos\pedrocore-ia

Motivo:

- Permite integração futura por API.
- Evita misturar código.
- Reduz risco de quebrar o FinGuard.

## Decisão 008 — Comandos sempre organizados

Decisão:

    Comandos PowerShell sempre em blocos por etapa.

Motivo:

- Evita bagunça.
- Facilita correção de erro.
- Ajuda a manter documentação.
"@

Set-Content -Path "$DocsPath\08_CHANGELOG.md" -Encoding UTF8 -Value @"
# PedroCore IA — Changelog

Atualizado em: $Now

## 0.1.0 — V1 inicial

### Adicionado

- Estrutura inicial do projeto.
- Backend FastAPI.
- Frontend React.
- MockProvider.
- Endpoint GET /health.
- Endpoint POST /api/chat.
- Interface simples de chat.
- Configurações básicas.
- Documentação inicial.
- README.
- VERSION.
- COMANDOS_POWERSHELL.

### Corrigido

- Caminho oficial definido como C:\Projetos\pedrocore-ia.
- ZIP revisado para ter somente uma pasta raiz.
- Regra de não interferir no FinGuard.
- Documentação retroativa criada.

### Pendente

- Instalar uv.
- Rodar uv sync.
- Rodar pytest.
- Rodar backend.
- Rodar frontend.
- Testar comunicação completa.

## Histórico operacional — 20/06/2026

- Projeto extraído em C:\Projetos\pedrocore-ia.
- Estrutura validada.
- Python encontrado.
- Node encontrado.
- npm encontrado.
- uv não encontrado.
- pip não encontrado.
- Documentação retroativa solicitada.
- Documentação retroativa criada.
"@

Set-Content -Path "$DocsPath\09_STATUS_ATUAL.md" -Encoding UTF8 -Value @"
# PedroCore IA — Status Atual

Atualizado em: $Now

## Versão atual

    V1 — Chat simples + API mock

## Local

    C:\Projetos\pedrocore-ia

## Estrutura validada

    apps
    docs
    .gitignore
    COMANDOS_POWERSHELL.md
    README.md
    VERSION.md

## Ferramentas detectadas

    Python 3.14.2
    Node v24.13.0
    npm 11.17.0

## Problemas atuais

    uv não reconhecido
    pip não reconhecido

## Próxima ação

Instalar uv:

    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

Depois fechar e abrir o PowerShell.

## Depois da correção

Rodar backend:

    cd C:\Projetos\pedrocore-ia\apps\api
    uv sync
    uv run pytest
    uv run uvicorn app.main:app --reload --port 3333

Rodar frontend:

    cd C:\Projetos\pedrocore-ia\apps\web
    npm install
    npm run dev

## Próximas versões

- V2 — Integração real com Gemini.
- V3 — Histórico simples + gostei/não gostei salvo.
- V4 — Prompts por modo.
- V5 — API interna para conexão com FinGuard.
- V6 — PostgreSQL + logs.
- V7 — RAG/memória com documentos.
- V8 — Multi-provider.
- V9 — Deploy/documentação final.
"@

Set-Content -Path "$ProjectRoot\VERSION.md" -Encoding UTF8 -Value @"
# PedroCore IA — Versionamento

Atualizado em: $Now

## Versão atual

    V1 — Chat simples + API mock

## Status

    Em teste local.

## Local oficial

    C:\Projetos\pedrocore-ia

## O que a V1 entrega

- Backend Python/FastAPI.
- Frontend React/Vite/TypeScript.
- MockProvider.
- Chat simples.
- Configurações básicas.
- Prompt base editável.

## Pendência atual

Instalar uv no Windows.

## Próxima versão

    V2 — Integração real com Gemini

## Roadmap

- V1 — Chat simples + API mock.
- V2 — Integração real com Gemini.
- V3 — Histórico simples + gostei/não gostei salvo.
- V4 — Prompts por modo.
- V5 — API interna para conexão com FinGuard.
- V6 — PostgreSQL + logs.
- V7 — RAG/memória com documentos.
- V8 — Multi-provider.
- V9 — Deploy/documentação final.
"@

Set-Content -Path "$ProjectRoot\COMANDOS_POWERSHELL.md" -Encoding UTF8 -Value @"
# PedroCore IA — Comandos PowerShell

Atualizado em: $Now

## Caminho oficial

    cd C:\Projetos\pedrocore-ia

## Verificar estrutura

    dir

## Verificar ferramentas

    python --version
    node -v
    npm -v
    uv --version

## Instalar uv

    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

Depois fechar e abrir o PowerShell.

## Backend — Terminal 1

    cd C:\Projetos\pedrocore-ia\apps\api
    uv sync
    uv run pytest
    uv run uvicorn app.main:app --reload --port 3333

## Testar backend

    http://localhost:3333/health
    http://localhost:3333/docs

## Frontend — Terminal 2

    cd C:\Projetos\pedrocore-ia\apps\web
    npm install
    npm run dev

## Abrir frontend

    http://localhost:5173

## Observação

Nunca executar comandos do PedroCore IA dentro da pasta FinGuard.
"@

Write-Host ""
Write-Host "Documentacao do PedroCore IA atualizada com sucesso." -ForegroundColor Green
Write-Host "Local: C:\Projetos\pedrocore-ia\docs" -ForegroundColor Cyan
Write-Host ""
