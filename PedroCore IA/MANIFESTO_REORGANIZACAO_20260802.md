# Manifesto da reorganização documental — 2026-08-02

## Resultado

O vault canônico do PedroCore IA está em `C:\Projetos\pedrocore-ia\PedroCore IA`.
A árvore versionada anterior `docs/` foi substituída por essa pasta-raiz sem
perda de conteúdo documental.

## Evidência de preservação

- 127 de 127 documentos Markdown anteriormente rastreados foram localizados na
  nova árvore com conteúdo byte a byte idêntico antes desta reconciliação;
- zero documento anterior ficou sem correspondente;
- cinco arquivos de configuração do Obsidian foram preservados na nova árvore;
- nenhum `.env`, credencial, banco, dump, `node_modules`, cache ou artefato de
  execução integra o vault;
- o validador canônico `app.modules.docs_graph` passou a usar `PedroCore IA`
  como raiz e `PedroCore IA/MOC_PEDROCORE_IA.md` como MOC principal.

## Alterações desta reconciliação

- referências atuais em `README.md`, `VERSION.md` e no status foram alinhadas
  ao novo caminho;
- o histórico técnico dentro dos documentos foi preservado, inclusive menções
  antigas a `docs/` quando descrevem o estado de uma frente anterior;
- este manifesto foi acrescentado como documento canônico e conectado ao MOC
  raiz;
- o código funcional do orquestrador, providers, políticas e interface não foi
  reaberto.

## Validação

O fechamento exige executar, sem provider real:

```powershell
cd C:\Projetos\pedrocore-ia\apps\api
.venv\Scripts\python.exe -m pytest tests\test_docs_graph.py
.venv\Scripts\python.exe -m app.modules.docs_graph.service
```

Resultado observado: 128 documentos, 697 links resolvidos, zero link quebrado,
zero link ambíguo, zero basename duplicado, zero órfão, zero beco sem saída e
todos os documentos alcançáveis a partir do MOC. O teste direcionado concluiu
com `15 passed, 1 warning`.

## Navegação

- [[MOC_PEDROCORE_IA]]
- [[09_STATUS_ATUAL]]
- [[08_CHANGELOG]]
