# PedroCore - Fluxo Completo

Atualizado em: 09/07/2026

## Fluxo de alto nivel

```text
Sistema consumidor
  -> backend do consumidor
  -> PedroCore /api/orchestrate
  -> pipeline seguro
  -> provider ou fallback
  -> resposta padronizada
  -> backend do consumidor
  -> interface do consumidor
```

O consumidor nao deve chamar provider externo diretamente. O PedroCore e a camada de controle.

## Diagrama textual

```text
[Front-end consumidor]
        |
        v
[Backend consumidor]
        |
        v
[POST /api/orchestrate]
        |
        v
[ChatRequest]
        |
        v
[Task Router]
        |
        v
[Project Context]
        |
        v
[Policy Enforcement]
        |
        v
[Intelligence Layer]
        |
        v
[Report Memory opcional]
        |
        v
[Artifact Reader opcional] -> [Artifacts Service]
        |
        v
[Prompt Builder]
        |
        v
[Provider decision]
        |
        +--> local_qa deterministico
        +--> local_model gate opt-in
        +--> provider real bloqueado por default
        +--> Mock fallback
        |
        v
[QA Text Analyzer]
        |
        v
[QA Response / Release Gate]
        |
        v
[Audit]
        |
        v
[OrchestrateResponse]
```

## 1. Entrada

O payload principal e `ChatRequest`. Campos importantes:

- `message`: texto de entrada.
- `origin_system`: identifica o consumidor (`pedrocore`, `finguard`, `finguard-local`).
- `task_type`: classifica a finalidade.
- `provider`: `mock`, `local_qa`, `local_model` ou provider real.
- `allow_real_provider`: default `false`.
- `allow_local_model`: default `false`.
- `context_from_memory`: default `false`.
- `artifacts`: conteudo enviado por payload, nao por leitura livre de disco.

## 2. Task Router

O Task Router normaliza `task_type` e define `response_style`, resposta estruturada, criticidade e permissao de mock.

Tasks criticas, como `release_gate_review`, recebem tratamento conservador.

## 3. Project Context

O Project Context resolve os limites do projeto a partir de `origin_system`.

Para `finguard` e `finguard-local`, o comportamento e read-only: nao executar comandos, nao escrever arquivos, nao ler repositorio real e aceitar apenas tasks permitidas.

## 4. Policy Enforcement

Policy Enforcement bloqueia antes de provider quando encontra task com semantica de execucao/escrita/delecao, payload com chaves como `command`/`exec`/`script`/`write_file`, task critica nao permitida para o projeto ou origem desconhecida em fluxo critico.

## 5. Intelligence Layer

A Intelligence Layer monta um plano deterministico com perfil de resposta, flags de seguranca, instrucoes internas e hints de avaliacao/memoria. Ela nao chama provider, nao habilita provider real e nao treina nada.

## 6. Report Memory opcional

Quando `context_from_memory=true`, o PedroCore tenta anexar um snapshot tecnico do projeto. Por default a persistencia esta off, nada e consultado e `memory_used=false`. Se desabilitada, retorna warning e segue sem inventar dados.

## 7. Artifacts e Artifact Reader

No uso padrao, artifacts entram por payload. Paths sao rejeitados. O Artifact Reader existe apenas como opt-in allowlisted e continua proibido para origem/caminho FinGuard.

## 8. Prompt Builder

O Prompt Builder monta o prompt enriquecido com mensagem, modo, contexto, estrategia da task, contexto de projeto, artefatos, instrucoes da Intelligence Layer e memoria tecnica quando usada.

## 9. Provider decision

- `local_qa`: caminho deterministico local para QA.
- `local_model`: exige `allow_local_model=true`, flag/backend validos e task nao critica.
- provider real: exige `allow_real_provider=true`; sem isso, safe mode bloqueia.
- fallback: MockProvider.

## 10. QA e release gate

O QA Text Analyzer processa evidencias textuais com heuristica local.

Release gate so pode avancar com evidencias textuais limpas, risco baixo, confianca suficiente, sem fallback, sem safe mode block e provider efetivo `local_qa`.

Provider real e mock nao aprovam release gate sozinhos.

## 11. Audit e resposta

O audit registra metadados como `audit_id`, timestamp, origem, task, provider pedido/usado, fallback, safe mode, status, latencia, risco e `can_advance`. O audit nao guarda conteudo de `.env` nem artefatos secretos.

## Links relacionados

- [[../MOC_ESTUDO_PEDROCORE]]
- [[../MOC_PEDROCORE_IA]]
- [[../MOC_ARQUITETURA]]
- [[../00_MAPEAMENTO_GERAL_PEDROCORE]]
- [[../10-contratos/CONTRATO_ORQUESTRACAO]]
