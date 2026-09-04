# Veltrix — Flashcards

Atualizado em: 03/09/2026 · **ESTUDO ATUAL**

Revisão ativa. Priorizam **conceitos duráveis** — números que envelhecem estão
isolados na última seção e explicitamente datados.

---

## Produto e história

P: O que é o Veltrix?
R: Um AI Runtime & Learning Control Plane: fica entre um agente de IA e a
execução; analisa, decide, governa e registra. Não executa.

P: O Veltrix é um modelo treinado?
R: Não. Não há fine-tuning, autoaprendizado, RAG vetorial nem modelo próprio.

P: O que mudou de PedroCore para Veltrix?
R: O nome do **produto**. Identificadores técnicos minúsculos (`pedrocore_*`,
`project_id="pedrocore"`, contratos) foram preservados de propósito.

P: `pedrocore` minúsculo no código é erro?
R: Não. É identificador técnico preservado. `PedroCore` maiúsculo é que virou
Veltrix.

P: O que é Functional Freeze?
R: A manutenção comum está encerrada. Reabrir exige aumentar uma capacidade real
ou ser necessário para outro sistema usar o Veltrix como núcleo.

## Arquitetura

P: Quais são os dois planos?
R: Runtime Plane (responder agora) e Learning Plane (aprender depois).

P: O que separa os dois planos?
R: Evidência e contratos. E a fronteira é **verificada por teste**: import de
topo do Runtime para o Learning reprova a suíte.

P: O que é a Evidence Platform?
R: Ingestão fail-closed com validação de contrato; a ponte entre os planos.

P: Quantos Universal Contracts V1 existem?
R: Cinco, mais o envelope de integração. Congelados por fingerprint de schema.

P: O que acontece se alguém alterar a forma de um contrato congelado?
R: O build quebra.

P: Quantas Eras tem o Control Plane, e qual o resultado?
R: Eras 1–10, todas PASS. Estado arquitetural `CONTROL_PLANE_READY`.

## Risk Engine

P: O Risk Engine executa alguma coisa?
R: Não. Emite um Execution Contract; a execução acontece fora, pelo Agent.

P: Quantas dimensões de risco existem, e por quê?
R: Seis independentes — dados, segurança, migração, escopo, regressão, operação.
Para não colapsar risco em um número opaco.

P: O que é BLOCK?
R: O gate mais restritivo. Intransponível **por construção**, com teste negativo
provando que não há bypass.

P: O que protege o Execution Contract?
R: HMAC sobre todos os campos, prazo de validade, e registro de override humano
autorizado.

P: O que é blast radius?
R: O alcance estimado de uma operação, com unidade explícita.

P: O que P1 a P5 tinham em comum?
R: Eram problemas objetivos do Risk Engine V1, todos fechados no V2 (R0–R5).

P: P4 — qual era o problema?
R: O gate era calculado, mas não intransponível por construção.

P: O que é o Project Registry?
R: O catálogo de projetos. **Identidade, não capacidade.**

P: Um projeto sem Capability Manifest pode ser analisado?
R: Sim. Os fatos ausentes ficam `UNKNOWN`; o que ele não ganha é permissão.

P: Quantos estados de tela tem o Risk Console?
R: Três exclusivos: entrada, revisão de contexto, resultado.

## Providers

P: Quais são os seis estados de um provider?
R: Conhecido, configurado, homologado, autorizado, executável, executado.

P: Provider selecionado é provider executado?
R: Não. Executado significa que o adapter foi chamado **e respondeu**.

P: Qual provider real está homologado?
R: Apenas Gemini, com `gemini-3.5-flash`.

P: Por que `auto` sempre resolve para o Gemini?
R: Porque é o único homologado. Decisão de homologação, não pendência técnica.

P: O que é `allow_real_provider`?
R: Flag do payload que autoriza provider real. Default `false` (safe mode).

P: O que é `allow_mock_fallback`?
R: Opt-out restritivo, default `true`. Quando `false`, uma falha do provider não
é substituída pelo Mock.

P: Quem envia `allow_mock_fallback=false`?
R: O chat interativo do próprio Veltrix, quando o usuário escolhe explicitamente
uma IA real.

P: Gemini falhou no chat com IA real escolhida — o que a resposta traz?
R: `provider="none"`, `model="none"`, `fallback_used=false`, `status="blocked"`.

P: E o que a interface mostra nesse caso?
R: "Gemini não concluiu a solicitação." Nunca uma resposta do Mock disfarçada.

P: O contrato mudou para os consumers integrados?
R: Não. O default continua `true` e o fallback seguro continua existindo.

P: `local_qa` e `local_model` são a mesma coisa?
R: Não. `local_qa` é heurística determinística sem rede; `local_model` seria um
LLM local, e está default-off sem transport real.

P: Qual provider o release gate aceita?
R: Somente `local_qa`, com evidência textual limpa. Nem Mock nem provider real
aprovam sozinhos.

P: O que a matriz de autorização combina?
R: `identity_strength + project_id + caller_role + environment + provider`.
Default: negar.

P: Credencial compartilhada alcança provider real?
R: Nunca. Identidade `ambiguous` não aparece em regra nenhuma.

## Learning e Dataset

P: `CONTROL_PLANE_READY` significa dataset pronto?
R: Não. São independentes.

P: Qual o readiness atual do dataset?
R: `DATASET_NOT_READY`.

P: Isso é um erro?
R: Não. É a resposta correta: não existe população real autorizada, e nada foi
fabricado.

P: Quantos Training Candidates reais autorizados existem?
R: Zero.

P: A Candidate Acquisition Foundation existe?
R: Sim, implementada. O que não existe é população autorizada.

P: Report Memory é RAG?
R: Não. E também não é treinamento.

P: `automatic_collection` é `true`?
R: Não. É invariante executável no Policy Engine: `false`.

## Segurança

P: O Veltrix executa comandos?
R: Não. O Policy Engine recusa execução, escrita, deleção, deploy e push, com
teste negativo.

P: A suíte padrão pode chamar provider real?
R: Não. O guard de `conftest.py` bloqueia estruturalmente e falha o teste.

P: Como o FinGuard é tratado?
R: Como consumer registrado de menor privilégio. O Veltrix não lê nem altera o
repositório dele.

P: Quais consumers existem?
R: FinGuard, Elyra e Structa.

## Versões

P: Qual a versão de produto?
R: V5.2.0.

P: Qual a versão da API/backend?
R: 0.2.0.

P: A tag `v6.0.0` é a versão 6 do produto?
R: Não. É o MVP backend. Produto, API e tags são três eixos independentes.

P: O que o Final Functional Gate mudou de versão?
R: Nada. Corrigiu defeitos dentro de contratos já congelados.

P: Qual a diferença entre `HUMAN_VISUAL_ACCEPTANCE` e
`HUMAN_RUNTIME_ACCEPTANCE`?
R: O primeiro aprova a aparência; o segundo aprova o fluxo funcional real em
uso. Uma tela correta pode estar mentindo sobre quem respondeu.

---

## Números — CHECKPOINT 03/09/2026

> Estes cartões envelhecem. Só valem como snapshot desta data; a fonte corrente
> é a CI do HEAD e [[../MOC_TESTES]].

P: Suíte backend no checkpoint de 03/09/2026?
R: `2027 passed, 62 skipped`.

P: Suíte frontend no mesmo checkpoint?
R: `122 passed`.

P: Superfície HTTP no mesmo checkpoint?
R: 43 paths.

P: Migrations no mesmo checkpoint?
R: `0001`–`0012`, todas aditivas.

> **Snapshot histórico de 09/07/2026**, preservado para contraste: naquela data
> a suíte era `296 passed, 6 skipped` e o HEAD auditado era `e0ff8e3`. Esses
> números descrevem o PedroCore de julho e **não** são o estado atual — a
> auditoria daquele dia está em [[PEDROCORE_AUDITORIA_STUDY_MAP_01]].

## Links relacionados

- [[../MOC_ESTUDO_PEDROCORE]]
- [[PEDROCORE_GLOSSARIO]]
- [[PEDROCORE_PERGUNTAS_E_RESPOSTAS]]
- [[PEDROCORE_FLUXO_COMPLETO]]
