# Veltrix — Perguntas e Respostas

Atualizado em: 03/09/2026 · **ESTUDO ATUAL**

---

## Produto e história

**1. O que é o Veltrix?**
Um *AI Runtime & Learning Control Plane*: fica entre um agente de IA e a
execução, e responde antes de qualquer coisa acontecer — a IA interpreta, a
policy decide, o risk prevê, a execução prova, a evidence registra, o learning
governa. Ele analisa, decide, governa e registra. Não executa.

**2. O que mudou de PedroCore para Veltrix?**
O nome do **produto**. Os identificadores técnicos foram preservados de
propósito: `pedrocore` minúsculo em tabelas, contratos e `project_id`, e
`PEDROCORE_*` como alias de variável de ambiente. A regra do rename foi separar
marca de protocolo pela caixa da palavra — assim não foi preciso manter uma
lista de exceções que alguém esqueceria de atualizar. Um replace cego teria
quebrado seis contratos congelados e cinco consumidores.

**3. Ele é uma IA própria?**
Não. É uma camada própria de orquestração e governança determinística. Não há
modelo treinado, fine-tuning, autoaprendizado nem RAG vetorial.

## Arquitetura

**4. O que é o Runtime Plane?**
O plano que *responde agora*: chat, orchestration, providers, policy, risk.

**5. O que é o Learning Plane?**
O plano que *aprende depois*: operational intelligence, memória, dataset,
training foundation. Entre os dois passam evidência e contratos, nunca chamadas
diretas — e a fronteira é verificada por teste, não por convenção.

**6. O que são os Universal Contracts?**
Cinco contratos V1 congelados — Project Capability Manifest, Quality Evidence,
Execution Outcome, Learning Source e o envelope de integração. Congelados por
fingerprint de schema: alterar a forma de qualquer um quebra o build.

**7. O que é a Evidence Platform?**
A ingestão fail-closed com validação de contrato. É por onde um fato verificado
atravessa do Runtime para o Learning. Sem evidência válida, nada entra — e
evidência não vira automaticamente candidato de treino.

## Risk Engine

**8. O que é o Risk Engine?**
O subsistema que analisa e governa risco de execução por IA. Recebe uma
intenção, resolve contexto, mede ambiguidade e escopo, produz sinais e findings
em seis dimensões independentes, calcula alcance, simula cenários e emite um
gate.

**9. O Risk Engine executa alguma coisa?**
**Não.** Ele emite um Execution Contract assinado. A execução acontece fora,
pelo Agent ou Test Harness. Depois, o pós-execução compara o resultado
produzido com o contrato que havia sido autorizado.

**10. O que é o Risk Engine V2?**
A evolução que fechou cinco problemas objetivos do V1, em seis stages R0–R5,
sem enfraquecer nenhuma invariante e sem tocar nos contratos congelados.

**11. O que significavam P1–P5?**

| | Problema no V1 | Fechado em |
|---|---|---|
| P1 | a persistência do risco não era do risco | R2 + R2.1 |
| P2 | "simulação" era enumeração fixa, não simulação | R5 |
| P3 | blast radius não tinha unidade | R3 |
| P4 | o gate era calculado, mas não intransponível por construção | R1 |
| P5 | o Risk Engine não usava os Universal Contracts | R4 |

**12. O que é BLOCK?**
O gate mais restritivo: a operação não deve prosseguir. Desde o R1 ele é
**intransponível por construção** — existe teste negativo provando que não há
caminho de bypass.

**13. O que é o Execution Contract?**
O artefato que transforma análise em restrições verificáveis. HMAC cobre todos
os campos, tem prazo de validade, e override humano autorizado é registrado.

**14. O que é blast radius?**
O alcance estimado de uma operação, **com unidade explícita**. Antes do R3 era
um número sem unidade — portanto sem significado.

**15. O que é o Risk Console?**
A interface do motor: TUI e CLI (`veltrix risk`), com três estados exclusivos —
entrada, revisão de contexto e resultado. No resultado a ordem é gate → resumo
→ principais riscos → por quê → o que fazer, com toda a evidência preservada em
seis abas.

**16. O que é o Project Registry?**
O catálogo dos projetos que o Veltrix conhece. **Identidade, não capacidade.**
Ele substituiu o Capability Manifest como fonte da lista de projetos, porque um
usuário com projeto próprio não conseguia analisá-lo. Um projeto registrado é
analisável; o que ele não ganha é permissão — sem manifesto, os fatos ausentes
ficam `UNKNOWN`.

## Learning e Dataset

**17. `CONTROL_PLANE_READY` significa que o dataset está pronto?**
**Não.** São coisas independentes. O plano de controle estar pronto não fabrica
população de treino. Os dois estados coexistem hoje:
`CONTROL_PLANE_READY` + `DATASET_NOT_READY`.

**18. O Veltrix tem modelo próprio treinado?**
Não. Não há fine-tuning, PEFT, LoRA, SFT, splits, dataset canônico gerado nem
consulta a Hugging Face. A Candidate Acquisition Foundation está implementada;
candidatos reais autorizados: **zero**.

**19. `DATASET_NOT_READY` significa erro?**
Não. É a **resposta correta**: não existe população real autorizada, e nenhuma
foi fabricada para fazer o número parecer melhor.

**20. Relatórios técnicos treinam o Veltrix?**
Não. Viram sinais e memória técnica. Isso é contexto, não peso.

## Providers

**21. Quais providers existem?**
`mock`, `local_qa`, `local_model`, `gemini`, `openai`, `claude`, `deepseek`,
`grok`.

**22. Qual provider real está homologado?**
Apenas **Gemini**, com `gemini-3.5-flash`. Por isso `auto` sempre resolve para
ele. É decisão de homologação, não pendência técnica.

**23. Qual a diferença entre conhecido, configurado, homologado, autorizado,
executável e executado?**
Conhecido = está no catálogo. Configurado = há credencial no ambiente.
Homologado = foi aprovado para uso real. Autorizado = *este* caller pode usá-lo
agora, segundo a matriz. Executável = implementado ∧ configurado ∧ homologado.
Executado = o adapter foi chamado **e respondeu**. Um provider selecionado na
interface não é um provider executado — essa confusão era exatamente o bug do
Final Functional Gate.

**24. Por que uma falha do Gemini não vira mais Mock no chat?**
Porque a interface estaria mentindo. Com o Gemini escolhido explicitamente, o
chat envia `allow_mock_fallback=false`; se o provider falha, a resposta volta
com `provider="none"`, `fallback_used=false`, `status="blocked"`, e a UI diz
"Gemini não concluiu a solicitação".

**25. O que é `allow_mock_fallback`?**
Um opt-out restritivo que **já existia** no contrato, com default `true`.
Quando `false`, a falha do provider não é substituída pelo Mock. O chat
interativo usa `false`; consumers integrados não enviam o campo e continuam
protegidos pelo fallback seguro.

**26. Qual a diferença entre `local_qa` e `local_model`?**
`local_qa` é heurística determinística local, sem rede, e é o **único** provider
em que o release gate confia. `local_model` seria um LLM local generativo: está
registrado, é opt-in, default-off e **não tem transport real**.

## Versões e estado

**27. Qual é a versão atual?**
Produto/UI **V5.2.0**; API/backend **0.2.0**; a tag Git mais recente é
`v7.0.0`.

**28. Por que produto, API e tag têm números diferentes?**
Porque são três eixos independentes. O produto marca entregas de interface; a
API marca o pacote Python; as tags marcam marcos técnicos do repositório. A tag
`v6.0.0` é o **MVP backend**, não a versão 6 do produto. Eles nunca foram
sincronizados e não devem ser.

**29. O Veltrix está publicado?**
Sim. `github.com/pedrofavarobelini/veltrix`, público, sob Apache-2.0, branch
padrão `main`. A publicação passou por higienização de watermark, sanitização
do histórico e um gate de release verificado.

**30. O Veltrix executa comandos?**
Não. O Policy Engine recusa semântica de execução, escrita, deleção, migration,
deploy e push — e isso é regra com teste negativo, não promessa.

**31. O que é o Functional Freeze?**
O estado do projeto após o Final Functional Gate: a manutenção comum está
encerrada. Uma nova frente só existe se a mudança aumentar uma capacidade real
do Veltrix ou for necessária para ele operar como núcleo de outro sistema.
Trocar texto, rearranjar card ou refatorar por preferência não reabrem o
projeto.

**32. O que significa `HUMAN_RUNTIME_ACCEPTANCE = PASS`?**
Que o fluxo funcional real foi exercitado por uma pessoa em uso, não só em
teste. É diferente de `HUMAN_VISUAL_ACCEPTANCE`, que é sobre aparência — e a
diferença importa, porque uma tela correta pode estar mentindo sobre quem
respondeu.

**33. Como testar sem risco?**
Suíte padrão com `provider=mock` ou `local_qa` e `allow_real_provider=false`. O
guard de `tests/conftest.py` impede estruturalmente que a suíte alcance provider
real ou rede. Comandos em [[../MOC_TESTES]].

**34. Como explicar em entrevista?**
"Veltrix é um control plane de IA: governa identidade, autorização, provider,
risco e evidência entre agentes de IA e a execução. Ele não executa nada e não
é um modelo treinado. Implementa safe mode, matriz de autorização fail-closed,
um motor de risco com gates intransponíveis por construção, contratos
congelados por fingerprint e uma separação testada entre o plano que responde
agora e o plano que aprende depois."

## Links relacionados

- [[../MOC_ESTUDO_PEDROCORE]]
- [[PEDROCORE_RESUMO_EXECUTIVO]]
- [[PEDROCORE_GLOSSARIO]]
- [[PEDROCORE_FLASHCARDS]]
- [[VELTRIX_RISK_ENGINE_ESTUDO]]
