"""CLI do Risk Engine.

Por que argparse e nao click/typer
----------------------------------

`click` ate ja esta instalado, de carona no uvicorn. Mas depender de algo que
so existe como dependencia transitiva de outra coisa e depender de um acidente:
o dia em que o uvicorn trocar de CLI, o console quebra sem ter mudado.

E a alternativa e barata. Esta CLI tem um punhado de subcomandos e flags
simples; `argparse` e biblioteca padrao, resolve isso inteiro e nao acrescenta
nada ao ambiente de quem so quer analisar um prompt.

O nome do comando
-----------------

`pedrocore risk`. O nome vem de `branding.COMMAND_NAME` e nao esta escrito por
extenso no texto de ajuda, para que o alias `veltrix` da frente de rename seja
uma linha em `[project.scripts]` e nao uma revisao de mensagens.

Garantia que atravessa todos os subcomandos
-------------------------------------------

Nenhum executa a operacao analisada. A CLI le, analisa, imprime e sai.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from app.modules.risk_console.branding import (
    COMMAND_NAME,
    CONSOLE_SUBCOMMAND,
    PRODUCT_NAME,
    PRODUCT_SUBTITLE,
)
from app.modules.risk_console.domain import (
    ENVIRONMENTS,
    EXECUTORS,
    ConsoleInputError,
    ConsoleRequestInput,
    available_projects,
    split_list,
)

EXIT_OK = 0
EXIT_INPUT_ERROR = 2
EXIT_OPERATIONAL_ERROR = 3
# Gate BLOCK tem codigo proprio para que um pipeline possa reagir a "bloqueado"
# sem precisar interpretar texto. Falha de uso e falha de politica sao coisas
# diferentes e nao deveriam compartilhar codigo de saida.
EXIT_BLOCKED = 4

_ENVIRONMENT_LABELS = [label for label, _ in ENVIRONMENTS]
_EXECUTOR_LABELS = [label for label, _ in EXECUTORS]


def _console_flags(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--project", help="Projeto que declara a capability de risco.")
    parser.add_argument(
        "--environment",
        choices=_ENVIRONMENT_LABELS,
        default=_ENVIRONMENT_LABELS[0],
        help="Ambiente da operação.",
    )
    parser.add_argument(
        "--executor",
        choices=_EXECUTOR_LABELS,
        default=_EXECUTOR_LABELS[0],
        help="Quem executaria a operação. Nesta versão é contexto, não ação.",
    )
    parser.add_argument("--permissions", default="", help="Permissões declaradas.")
    parser.add_argument("--allowed-scope", default="", help="Escopo permitido.")
    parser.add_argument("--forbidden-scope", default="", help="Escopo proibido.")
    parser.add_argument("--targets", default="", help="Alvos da operação.")
    parser.add_argument("--required-tests", default="", help="Testes exigidos.")
    parser.add_argument("--constraints", default="", help="Restrições declaradas.")
    parser.add_argument(
        "--acceptance-criteria", default="", help="Critérios de aceitação."
    )
    parser.add_argument("--integrations", default="", help="Integrações externas.")
    parser.add_argument("--database", default=None, help="Banco de dados afetado.")
    parser.add_argument(
        "--rollback-plan",
        action="store_true",
        help="Declara que existe plano de rollback.",
    )
    parser.add_argument("--json", action="store_true", help="Saída em JSON sanitizado.")
    parser.add_argument("--output", help="Grava a saída no arquivo indicado.")
    parser.add_argument(
        "--no-ai",
        action="store_true",
        help=(
            "Explicita o caminho determinístico. O Risk Engine já não chama "
            "provider algum; a flag existe para tornar isso verificável."
        ),
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=COMMAND_NAME,
        description=f"{PRODUCT_NAME} — {PRODUCT_SUBTITLE}",
    )
    subparsers = parser.add_subparsers(dest="group", required=True)

    risk = subparsers.add_parser(
        CONSOLE_SUBCOMMAND, help="Análise de risco pré-execução."
    )
    actions = risk.add_subparsers(dest="action")

    analyze_parser = actions.add_parser("analyze", help="Analisa um prompt.")
    analyze_parser.add_argument(
        "file", nargs="?", help="Arquivo com o prompt. Omita para usar --stdin."
    )
    analyze_parser.add_argument(
        "--stdin", action="store_true", help="Lê o prompt da entrada padrão."
    )
    _console_flags(analyze_parser)

    inspect_parser = actions.add_parser(
        "inspect", help="Mostra projetos, ambientes e executores disponíveis."
    )
    inspect_parser.add_argument("--json", action="store_true", help="Saída em JSON.")

    contract_parser = actions.add_parser(
        "contract", help="Emite Execution Contract para um prompt aprovado."
    )
    contract_parser.add_argument("file", nargs="?", help="Arquivo com o prompt.")
    contract_parser.add_argument("--stdin", action="store_true", help="Lê da entrada padrão.")
    _console_flags(contract_parser)

    validate_parser = actions.add_parser(
        "validate-contract", help="Valida um contrato universal de risco (JSON)."
    )
    validate_parser.add_argument("file", help="Arquivo com o contrato.")
    validate_parser.add_argument("--project", required=True, help="Projeto autenticado.")
    validate_parser.add_argument("--producer", required=True, help="Produtor autenticado.")
    validate_parser.add_argument("--json", action="store_true", help="Saída em JSON.")

    history_parser = actions.add_parser(
        "history", help="Resumo histórico de risco do projeto."
    )
    history_parser.add_argument("--project", required=True, help="Projeto consultado.")
    history_parser.add_argument("--producer", required=True, help="Produtor autenticado.")
    history_parser.add_argument(
        "--days", type=int, default=30, help="Tamanho da janela, em dias (padrão: 30)."
    )
    history_parser.add_argument("--json", action="store_true", help="Saída em JSON.")

    # `benchmark` recebe os casos por arquivo, e nao por flag, porque o
    # servico real exige uma lista de `BenchmarkCase` — cada um com uma
    # RiskRequest completa. Nao ha como derivar isso de um punhado de flags, e
    # inventar um caso sintetico produziria o benchmark de nada.
    benchmark_parser = actions.add_parser(
        "benchmark", help="Compara estratégias registradas no histórico."
    )
    benchmark_parser.add_argument(
        "cases_file", help="Arquivo JSON com a requisição de benchmark completa."
    )
    benchmark_parser.add_argument("--json", action="store_true", help="Saída em JSON.")

    return parser


# --- leitura de prompt ----------------------------------------------------


def _read_prompt(args) -> str:
    if args.stdin:
        return sys.stdin.read()
    if not args.file:
        raise ConsoleInputError(
            "Informe um arquivo com o prompt ou use --stdin para ler da entrada padrão."
        )
    path = Path(args.file)
    if not path.is_file():
        # O caminho digitado pelo usuario e dele; devolve-lo nao vaza nada que
        # ele ja nao soubesse.
        raise ConsoleInputError(f"Arquivo não encontrado: {path}")
    return path.read_text(encoding="utf-8")


def _entry_from(args, prompt: str) -> ConsoleRequestInput:
    projects = available_projects()
    project = args.project or (projects[0] if projects else "")
    return ConsoleRequestInput(
        project_id=project,
        environment_label=args.environment,
        executor_label=args.executor,
        prompt=prompt,
        permissions=split_list(args.permissions),
        allowed_scope=split_list(args.allowed_scope),
        forbidden_scope=split_list(args.forbidden_scope),
        targets=split_list(args.targets),
        required_tests=split_list(args.required_tests),
        constraints=split_list(args.constraints),
        acceptance_criteria=split_list(args.acceptance_criteria),
        external_integrations=split_list(args.integrations),
        database=args.database,
        rollback_plan_present=args.rollback_plan,
    )


def _emit(text: str, args, stream) -> None:
    if getattr(args, "output", None):
        Path(args.output).write_text(text, encoding="utf-8")
        print(f"Gravado em {args.output}", file=stream)
        return
    print(text, file=stream)


# --- subcomandos ----------------------------------------------------------


def _cmd_analyze(args, stream) -> int:
    from app.modules.risk_console.analysis import ConsoleOperationError, analyze
    from app.modules.risk_console.export import as_json
    from app.modules.risk_console.render import render_analysis

    try:
        prompt = _read_prompt(args)
        result = analyze(_entry_from(args, prompt))
    except ConsoleInputError as error:
        print(f"Erro de entrada: {error}", file=stream)
        return EXIT_INPUT_ERROR
    except ConsoleOperationError as error:
        print(f"Erro operacional: {error}", file=stream)
        return EXIT_OPERATIONAL_ERROR

    _emit(as_json(result) if args.json else _plain(render_analysis(result)), args, stream)
    return EXIT_BLOCKED if result.blocked else EXIT_OK


def _cmd_contract(args, stream) -> int:
    from app.modules.risk_console.analysis import (
        ConsoleOperationError,
        analyze,
        issue_contract,
    )

    try:
        prompt = _read_prompt(args)
        result = analyze(_entry_from(args, prompt))
    except ConsoleInputError as error:
        print(f"Erro de entrada: {error}", file=stream)
        return EXIT_INPUT_ERROR
    except ConsoleOperationError as error:
        print(f"Erro operacional: {error}", file=stream)
        return EXIT_OPERATIONAL_ERROR

    if result.blocked:
        print(
            "EXECUÇÃO BLOQUEADA: contrato não é emitido enquanto o gate for BLOQUEADO.",
            file=stream,
        )
        return EXIT_BLOCKED

    try:
        contract = issue_contract(result)
    except ConsoleOperationError as error:
        print(f"Erro operacional: {error}", file=stream)
        return EXIT_OPERATIONAL_ERROR

    payload = contract.model_dump(mode="json")
    _emit(
        json.dumps(payload, ensure_ascii=False, indent=2)
        if args.json
        else f"Contrato emitido: {contract.contract_id}\nGate: {contract.gate.value}",
        args,
        stream,
    )
    return EXIT_OK


def _cmd_inspect(args, stream) -> int:
    data = {
        "produto": PRODUCT_NAME,
        "comando": f"{COMMAND_NAME} {CONSOLE_SUBCOMMAND}",
        "projetos": list(available_projects()),
        "ambientes": _ENVIRONMENT_LABELS,
        "executores": _EXECUTOR_LABELS,
    }
    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2), file=stream)
        return EXIT_OK
    print(f"{PRODUCT_NAME} — {PRODUCT_SUBTITLE}", file=stream)
    print(f"  Projetos ...... {', '.join(data['projetos']) or 'nenhum'}", file=stream)
    print(f"  Ambientes ..... {', '.join(data['ambientes'])}", file=stream)
    print(f"  Executores .... {', '.join(data['executores'])}", file=stream)
    return EXIT_OK


def _cmd_validate_contract(args, stream) -> int:
    from app.modules.risk_engine.universal_contract import validate_risk_contract

    path = Path(args.file)
    if not path.is_file():
        print(f"Erro de entrada: arquivo não encontrado: {path}", file=stream)
        return EXIT_INPUT_ERROR
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        print("Erro de entrada: o arquivo não contém JSON válido.", file=stream)
        return EXIT_INPUT_ERROR

    validation = validate_risk_contract(
        payload,
        authenticated_project_id=args.project,
        authenticated_producer_id=args.producer,
    )
    data = {
        "aceito": validation.accepted,
        "codigo_erro": validation.error_code,
        "motivo": validation.reason,
        "violacoes_de_autoridade": validation.authority_violations,
        "gate_decidido_pelo_consumidor": validation.gate_decided,
    }
    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2), file=stream)
    elif validation.accepted:
        print("Contrato aceito.", file=stream)
    else:
        print(f"Contrato recusado [{validation.error_code}]: {validation.reason}", file=stream)
    return EXIT_OK if validation.accepted else EXIT_INPUT_ERROR


def _cmd_history(args, stream) -> int:
    from datetime import datetime, timedelta, timezone

    from app.modules.risk_engine.historical_schemas import HistoricalRiskQuery
    from app.modules.risk_engine.historical_service import historical_risk_service

    if args.days < 1:
        print("Erro de entrada: --days deve ser pelo menos 1.", file=stream)
        return EXIT_INPUT_ERROR

    end = datetime.now(timezone.utc)
    summary = historical_risk_service.summarize(
        HistoricalRiskQuery(
            producer=args.producer,
            project_id=args.project,
            window_start=end - timedelta(days=args.days),
            window_end=end,
        )
    )
    if args.json:
        print(
            json.dumps(summary.model_dump(mode="json"), ensure_ascii=False, indent=2),
            file=stream,
        )
        return EXIT_OK
    print(f"Projeto ......... {summary.project_id}", file=stream)
    print(f"Situação ........ {summary.status}", file=stream)
    print(f"Amostra ......... {summary.sample_size}", file=stream)
    print(f"Excluídos ....... {summary.excluded_count}", file=stream)
    print(f"Generalizável ... {'sim' if summary.generalizable else 'não'}", file=stream)
    return EXIT_OK


def _cmd_benchmark(args, stream) -> int:
    from pydantic import ValidationError

    from app.modules.risk_engine.historical_schemas import HistoricalBenchmarkRequest
    from app.modules.risk_engine.historical_service import historical_risk_service

    path = Path(args.cases_file)
    if not path.is_file():
        print(f"Erro de entrada: arquivo não encontrado: {path}", file=stream)
        return EXIT_INPUT_ERROR
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        request = HistoricalBenchmarkRequest.model_validate(payload)
    except json.JSONDecodeError:
        print("Erro de entrada: o arquivo não contém JSON válido.", file=stream)
        return EXIT_INPUT_ERROR
    except ValidationError as error:
        # Diz ONDE e O QUE, nunca o valor recusado.
        detail = "; ".join(
            f"{'.'.join(str(part) for part in item.get('loc', ())) or 'payload'}: "
            f"{item.get('msg', 'inválido')}"
            for item in error.errors()[:5]
        )
        print(f"Erro de entrada: requisição de benchmark inválida — {detail}", file=stream)
        return EXIT_INPUT_ERROR

    result = historical_risk_service.benchmark(request)
    if args.json:
        print(
            json.dumps(result.model_dump(mode="json"), ensure_ascii=False, indent=2),
            file=stream,
        )
        return EXIT_OK
    print(f"Projeto ......... {result.project_id}", file=stream)
    print(f"Situação ........ {result.status}", file=stream)
    return EXIT_OK


def _plain(markup: str) -> str:
    """Relatório sem marcação de cor, para pipe e arquivo.

    O mesmo texto que a TUI mostra; o que sai são as tags do Rich, não o
    conteúdo — para que `> arquivo.txt` continue legível.
    """
    from rich.console import Console

    console = Console(width=100, no_color=True, force_terminal=False, highlight=False)
    with console.capture() as capture:
        console.print(markup)
    return capture.get()


_ACTIONS = {
    "analyze": _cmd_analyze,
    "contract": _cmd_contract,
    "inspect": _cmd_inspect,
    "validate-contract": _cmd_validate_contract,
    "history": _cmd_history,
    "benchmark": _cmd_benchmark,
}


def main(argv: list[str] | None = None, stream=None) -> int:
    """Ponto de entrada. `pedrocore risk` sem subcomando abre a TUI."""
    if stream is None:
        # Sem isto, `--json > arquivo.json` sai no codepage do console (cp1252
        # no Windows) e produz bytes que nao sao UTF-8 validos — quem le do
        # outro lado do pipe recebe JSON quebrado em qualquer acento. A saida
        # do produto e UTF-8 independentemente do terminal que a hospeda.
        _force_utf8(sys.stdout)
        stream = sys.stdout
    parser = build_parser()
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])

    if args.group != CONSOLE_SUBCOMMAND:
        parser.error("comando desconhecido")

    if not args.action:
        return _open_console(stream)

    return _ACTIONS[args.action](args, stream)


def _force_utf8(stream) -> None:
    """Garante UTF-8 na saida, sem quebrar quem nao suporta reconfigurar."""
    reconfigure = getattr(stream, "reconfigure", None)
    if reconfigure is None:
        return
    try:
        reconfigure(encoding="utf-8")
    except (OSError, ValueError):
        # Stream substituido ou sem suporte: seguir e melhor que abortar a
        # analise por causa do encoding do terminal.
        pass


def _open_console(stream) -> int:
    """Abre o Risk Console, com mensagem acionável se faltar a dependência."""
    try:
        from app.modules.risk_console.app import run
    except ModuleNotFoundError:
        print(
            "O Risk Console precisa do pacote 'textual'.\n"
            "Instale com:  uv sync --extra console",
            file=stream,
        )
        return EXIT_OPERATIONAL_ERROR
    run()
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
