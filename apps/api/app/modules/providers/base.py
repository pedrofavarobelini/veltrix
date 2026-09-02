from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum


class TransportClose(str, Enum):
    """Resultado observado do fechamento do transporte local.

    Distingue explicitamente TENTATIVA de CONFIRMAÇÃO. `UNKNOWN` é o valor
    honesto quando o fechamento foi solicitado mas o resultado não é
    observável pelo chamador — por exemplo, quando `asyncio.wait_for` cancela
    a coroutine e a exceção que chega ao pipeline é gerada pelo próprio
    `wait_for`, não pelo adapter.

    Nenhum destes valores é prova de cancelamento REMOTO. Mesmo `CONFIRMED`
    significa apenas que o cliente HTTP local foi encerrado.
    """

    NOT_ATTEMPTED = "not_attempted"
    CONFIRMED = "confirmed"
    FAILED = "failed"
    UNKNOWN = "unknown"


def normalize_token_count(value: object) -> int | None:
    """Aceita somente contagem de token real e não negativa.

    Métrica de token NUNCA é estimada nesta base de código: se o provider não
    devolveu o valor, o campo permanece `None`. `bool` é subclasse de `int` e
    nunca é uma contagem legítima.
    """
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value if value >= 0 else None


@dataclass
class ProviderResponse:
    """Resposta normalizada de um adapter.

    Os campos além de `answer`/`provider`/`model` são aditivos e opcionais:
    adapters que não os produzem (Mock, local_qa, local_model) continuam
    válidos e mantêm os defaults seguros. Nenhum destes campos é exposto à SPA
    do FinGuard — eles vivem em auditoria e observabilidade internas.
    """

    answer: str
    provider: str
    model: str
    # Motivo de parada informado pelo provider (ex.: "STOP", "MAX_TOKENS").
    finish_reason: str | None = None
    # Contagens reais de `usage_metadata`; nunca calculadas por aproximação.
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None
    # True somente com evidência explícita do provider, nunca por heurística
    # de tamanho próximo ao orçamento.
    truncated: bool = False
    # Orçamento efetivo aplicado pelo Veltrix nesta chamada.
    output_budget: int | None = None
    # Timeout de transporte efetivamente configurado no cliente.
    transport_timeout_ms: int | None = None
    # Resultado OBSERVADO do fechamento do transporte local.
    transport_close: TransportClose = TransportClose.NOT_ATTEMPTED


class ProviderConfigError(Exception):
    """Erro de configuração de provider, como chave ausente."""


class ProviderExecutionError(Exception):
    """Erro de execução da API do provider.

    `transport_close` carrega o resultado observado do fechamento do
    transporte, quando o adapter conseguiu observá-lo.
    """

    transport_close: TransportClose = TransportClose.NOT_ATTEMPTED


class ProviderTransportTimeoutError(ProviderExecutionError):
    """Timeout do transporte HTTP após o dispatch externo.

    O transporte local expirou e o fechamento foi solicitado. Isso NÃO prova
    que a geração remota parou: a certeza de conclusão permanece ambígua e
    nenhum retry ou provider secundário é liberado por causa disso — nem
    mesmo quando `transport_close` é `CONFIRMED`.
    """


class ProviderOutputRejectedError(ProviderExecutionError):
    """Resposta recebida, porém não utilizável como conclusão normal.

    A chamada externa terminou (`completion` é fato, não suposição), mas o
    `finish_reason` indica que o texto não é uma resposta completa — o caso
    mais importante é `MAX_TOKENS`, que sinaliza truncamento pelo orçamento de
    saída. Não existe chamada de continuação, retry nem provider secundário:
    o encerramento seguro existente (Mock) é aplicado.

    Os metadados de uso são preservados: o custo já foi incorrido, então
    descartá-los tornaria a contabilidade de tokens silenciosamente incompleta
    justamente nos casos mais caros.
    """

    def __init__(
        self,
        message: str,
        *,
        finish_reason: str | None = None,
        truncated: bool = False,
        input_tokens: int | None = None,
        output_tokens: int | None = None,
        total_tokens: int | None = None,
        output_budget: int | None = None,
        transport_timeout_ms: int | None = None,
    ) -> None:
        super().__init__(message)
        self.finish_reason = finish_reason
        self.truncated = truncated
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.total_tokens = total_tokens
        self.output_budget = output_budget
        self.transport_timeout_ms = transport_timeout_ms


class BaseAIProvider(ABC):
    name: str
    label: str
    default_model: str
    real_provider: bool = True
    # Adapter aceita `output_budget`/`transport_timeout_ms` em
    # `generate_response`. Default False mantém Mock, local_qa, local_model e
    # os adapters ainda não migrados intocados.
    supports_generation_budget: bool = False
    # Adapter fecha o transporte local quando a task é cancelada. Isso é um
    # fato de transporte local; nunca é prova de cancelamento remoto.
    supports_transport_cancellation: bool = False

    @property
    @abstractmethod
    def is_configured(self) -> bool:
        pass

    @abstractmethod
    async def generate_response(
        self,
        message: str,
        mode: str,
        model: str,
        system_prompt: str | None = None,
    ) -> ProviderResponse:
        pass

    def build_prompt(
        self,
        message: str,
        mode: str,
        system_prompt: str | None = None,
    ) -> str:
        base_prompt = system_prompt or (
            "Você é o Veltrix, um assistente pessoal técnico, claro, direto e útil."
        )

        mode_instruction = {
            "normal": "Responda de forma natural, clara e útil.",
            "tecnico": "Responda de forma técnica, organizada, objetiva e sem enrolação.",
            "resumido": "Responda de forma curta, direta e prática.",
            "codigo": "Priorize explicação técnica, exemplos de código e passos de implementação.",
        }.get(mode, "Responda de forma clara e útil.")

        return f"""
{base_prompt}

Modo de resposta:
{mode_instruction}

Mensagem do usuário:
{message}
""".strip()
