"""Ponte entre o console e o core do Risk Engine.

Por que em processo, e nao por HTTP
-----------------------------------

O console e local e roda na mesma maquina que o core. Falar HTTP consigo
mesmo custaria um servidor para subir, uma porta para escolher, uma
credencial para gerenciar e um modo de falha novo — tudo isso para chegar aos
mesmos objetos que um `import` alcanca.

O que NAO muda por ser em processo: quem decide. A analise vem de
`pre_execution_risk_service` e o gate de `execution_contract_service`, que sao
exatamente os que o router HTTP chama. O console nao tem regra de risco.

    Console  ->  Risk Service  ->  Policy/Gate  ->  resultado  ->  Console

A porta HTTP continua existindo e e o caminho de consumidor externo. Este
modulo e o caminho do humano no terminal.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.modules.risk_console.domain import ConsoleRequestInput, build_request
from app.modules.risk_console.presentation import Recommendation, derive_recommendations
from app.modules.risk_engine.execution_contract_schemas import ExecutionContract, RiskGate
from app.modules.risk_engine.execution_contract_service import (
    ContractConfigurationError,
    context_signature,
    execution_contract_service,
)
from app.modules.risk_engine.pre_execution_schemas import PreExecutionRiskAnalysis
from app.modules.risk_engine.pre_execution_service import pre_execution_risk_service
from app.modules.risk_engine.schemas import RiskRequest


# `request_id` e novo a cada analise. Compara-lo faria toda requisicao
# parecer diferente de si mesma, e o vinculo nunca validaria. O que precisa
# ser comparado e o CONTEUDO analisado: prompt, escopo, permissao, ambiente.
_BINDING_REQUEST_ID = "console-binding"


def binding_signature(request: RiskRequest) -> str:
    """Assinatura do conteudo analisado, neutra quanto ao identificador."""
    return context_signature(request.model_copy(update={"request_id": _BINDING_REQUEST_ID}))


class ConsoleOperationError(RuntimeError):
    """Falha operacional ja sanitizada para exibicao.

    Mensagem de erro e superficie de vazamento: string de conexao, caminho
    interno e stack trace nao ajudam quem esta no terminal e ajudam quem esta
    olhando por cima do ombro. O detalhe tecnico fica no log do processo; a
    tela recebe o que da para agir.
    """


@dataclass(slots=True)
class ConsoleAnalysis:
    """Resultado completo de uma analise, pronto para apresentar."""

    request: RiskRequest
    analysis: PreExecutionRiskAnalysis
    gate: RiskGate
    gate_reasons: list[str]
    signature: str
    recommendations: list[Recommendation] = field(default_factory=list)

    @property
    def blocked(self) -> bool:
        return self.gate is RiskGate.BLOCK

    def matches(self, request: RiskRequest) -> bool:
        """A requisicao atual ainda e a que foi analisada?

        Usada para invalidar 'copiar prompt aprovado' depois de uma edicao.
        Compara a assinatura selada, e nao apenas o texto: mudar permissao ou
        escopo tambem muda o que foi aprovado, ainda que o prompt continue
        igual.
        """
        return binding_signature(request) == self.signature


def analyze(entry: ConsoleRequestInput) -> ConsoleAnalysis:
    """Analisa uma entrada do console. NUNCA executa a operacao alvo."""
    request = build_request(entry)
    return analyze_request(request)


def analyze_request(request: RiskRequest) -> ConsoleAnalysis:
    try:
        analysis = pre_execution_risk_service.analyze(request)
    except Exception as error:  # noqa: BLE001 - sanitizado de proposito
        raise ConsoleOperationError(_sanitize(error)) from error

    gate, reasons = execution_contract_service.gate_for(analysis, request)
    return ConsoleAnalysis(
        request=request,
        analysis=analysis,
        gate=gate,
        gate_reasons=list(reasons),
        signature=binding_signature(request),
        recommendations=derive_recommendations(analysis, gate, list(reasons)),
    )


def issue_contract(result: ConsoleAnalysis) -> ExecutionContract:
    """Emite o Execution Contract da analise corrente.

    A recusa em BLOCK e verificada AQUI e tambem no core. A tela desabilita o
    botao, mas desabilitar botao e conveniencia, nao seguranca: quem chamar a
    funcao direto recebe a mesma recusa.
    """
    if result.blocked:
        raise ConsoleOperationError(
            "Execução bloqueada: contrato não pode ser emitido enquanto o gate for BLOQUEADO."
        )
    try:
        return execution_contract_service.issue(result.request)
    except ContractConfigurationError:
        raise ConsoleOperationError(
            "Assinatura de contratos não configurada. "
            "Defina PEDROCORE_RISK_CONTRACT_SIGNING_KEY com pelo menos 32 caracteres."
        ) from None
    except Exception as error:  # noqa: BLE001 - sanitizado de proposito
        raise ConsoleOperationError(_sanitize(error)) from error


def approved_prompt(result: ConsoleAnalysis, current: RiskRequest | None = None) -> str:
    """Devolve o prompt correspondente a analise vigente.

    Se a requisicao atual ja divergiu da analisada, recusa. O caminho que isto
    impede e concreto: analisa A, edita para B, copia B como se A tivesse
    aprovado. O vinculo tem que continuar valendo para o texto que sai daqui.
    """
    if result.blocked:
        raise ConsoleOperationError(
            "Execução bloqueada: não há prompt aprovado para copiar."
        )
    if current is not None and not result.matches(current):
        raise ConsoleOperationError(
            "O formulário mudou desde a última análise. "
            "Execute 'Reanalisar' antes de copiar o prompt aprovado."
        )
    return result.request.request_text


def _sanitize(error: Exception) -> str:
    """Mensagem operacional sem segredo, sem caminho interno, sem stack.

    O tipo da excecao e informacao util e nao sensivel; o texto dela pode
    conter string de conexao, e por isso nao e propagado.
    """
    return (
        "Falha operacional ao analisar risco "
        f"({type(error).__name__}). Nenhum dado sensível é exibido; "
        "consulte o log do processo para o detalhe técnico."
    )
