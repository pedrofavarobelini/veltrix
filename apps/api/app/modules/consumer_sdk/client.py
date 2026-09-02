"""E1 — Consumer SDK oficial do PedroCore.

O problema
----------

Cada consumidor montava o proprio cliente HTTP: cabecalho de credencial na
mao, retry ad hoc, tratamento de erro que as vezes vazava a mensagem inteira
do servidor, e nenhuma nocao compartilhada de correlacao. Cinco consumidores,
cinco jeitos de errar a mesma coisa.

O que o SDK e
-------------

Uma camada fina e TIPADA sobre os contratos que ja existem. Ele nao inventa
protocolo, nao acrescenta semantica e nao decide nada: monta a requisicao,
carrega a identidade e a correlacao, aplica timeout e retry, e devolve tipos.

Neutralidade e obrigatoria
--------------------------

Nao existe `if project == "..."` aqui, e nao pode existir. O SDK e o mesmo
para todo consumidor; o que muda entre eles e o que cada um DECLARA no
Capability Manifest. Um cliente que soubesse o nome dos projetos seria um
cliente que precisa ser reeditado a cada consumidor novo.

Idempotencia e retry
--------------------

Retry so acontece onde repetir e seguro: erro de transporte e 5xx, nunca 4xx.
Um 4xx repetido nao vira sucesso — vira o mesmo erro tres vezes e um log
maior. Toda escrita carrega uma chave de idempotencia derivada do conteudo,
para que o retry que o servidor ja processou nao vire um segundo registro.

Erro sanitizado
---------------

O SDK nunca propaga corpo bruto de erro. Ele devolve o codigo, o status e uma
mensagem curta — porque corpo de erro e onde string de conexao costuma
aparecer, e o consumidor tipicamente registra a excecao inteira em log.
"""

from __future__ import annotations

import hashlib
import json
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from app.modules.consumer_sdk.version import SDK_VERSION

DEFAULT_TIMEOUT_SECONDS = 15.0
DEFAULT_MAX_ATTEMPTS = 3
API_KEY_HEADER = "X-PedroCore-Api-Key"
CORRELATION_HEADER = "X-PedroCore-Correlation-Id"
SDK_HEADER = "X-PedroCore-SDK"
IDEMPOTENCY_HEADER = "X-PedroCore-Idempotency-Key"

# Repetir so onde repetir pode dar certo. 4xx e o servidor dizendo que o
# PEDIDO esta errado; insistir nao conserta o pedido.
_RETRYABLE_STATUS = frozenset({429, 500, 502, 503, 504})


class PedroCoreError(RuntimeError):
    """Erro do SDK, ja sanitizado.

    Carrega o que da para agir — status e codigo — e nunca o corpo bruto da
    resposta.
    """

    def __init__(self, message: str, *, status: int | None = None, code: str | None = None):
        super().__init__(message)
        self.status = status
        self.code = code


class PedroCoreConfigError(PedroCoreError):
    """Configuracao ausente ou invalida. Falha na construcao, nao no uso."""


@dataclass(frozen=True, slots=True)
class PedroCoreConfig:
    """Configuracao explicita. Nao ha leitura silenciosa de ambiente.

    Ler `os.environ` por conta propria faria o SDK se comportar diferente em
    duas maquinas sem que o codigo mudasse — e o consumidor descobriria isso
    em producao.
    """

    base_url: str
    api_key: str
    project_id: str
    producer: str
    environment: str = "development"
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS
    max_attempts: int = DEFAULT_MAX_ATTEMPTS
    backoff_seconds: float = 0.2

    def __post_init__(self) -> None:
        if not self.base_url.strip():
            raise PedroCoreConfigError("base_url é obrigatória.")
        if not self.api_key.strip():
            raise PedroCoreConfigError("api_key é obrigatória.")
        if not self.project_id.strip():
            raise PedroCoreConfigError("project_id é obrigatório.")
        if self.max_attempts < 1:
            raise PedroCoreConfigError("max_attempts deve ser pelo menos 1.")
        if self.timeout_seconds <= 0:
            raise PedroCoreConfigError("timeout_seconds deve ser positivo.")


@dataclass(slots=True)
class Response:
    """Resposta ja decodificada, sem o objeto de transporte."""

    status: int
    payload: dict[str, Any] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return 200 <= self.status < 300


# Transporte injetavel: recebe (metodo, url, headers, corpo) e devolve
# `Response`. Injetar em vez de fixar `httpx` permite testar o SDK inteiro sem
# rede — e sem duble de biblioteca, que testaria o duble.
Transport = Callable[[str, str, dict[str, str], dict[str, Any] | None], Response]


def idempotency_key(payload: dict[str, Any]) -> str:
    """Chave derivada do conteudo.

    Derivada, e nao sorteada: um retry precisa carregar a MESMA chave, senao
    o servidor ve dois pedidos diferentes e a idempotencia nao acontece.
    """
    canonico = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonico.encode()).hexdigest()[:32]


class PedroCoreClient:
    """Cliente oficial. Fino, tipado e neutro em relacao ao projeto."""

    def __init__(
        self,
        config: PedroCoreConfig,
        transport: Transport,
        *,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._config = config
        self._transport = transport
        self._sleep = sleep

    # --- identidade e capabilities ---------------------------------------

    @property
    def sdk_version(self) -> str:
        return SDK_VERSION

    @property
    def project_id(self) -> str:
        return self._config.project_id

    def health(self) -> Response:
        return self._request("GET", "/api/health")

    def capabilities(self) -> Response:
        """O que ESTE projeto declara. A resposta vem do servidor."""
        return self._request("GET", f"/api/projects/{self._config.project_id}/capabilities")

    def compatibility(self, capability: str, **versions: Any) -> Response:
        payload = {
            "project_id": self._config.project_id,
            "capability": capability,
            "sdk_version": SDK_VERSION,
            **versions,
        }
        return self._request("POST", "/api/compatibility/check", payload)

    # --- risco ------------------------------------------------------------

    def analyze_risk(self, contract: dict[str, Any]) -> Response:
        """Submete o contrato universal de risco.

        `producer` e `project_id` vao no envelope e sao conferidos pelo
        servidor contra a credencial — o SDK declara, ele nao decide.
        """
        return self._request(
            "POST",
            "/api/risk/universal/analyze",
            {
                "producer": self._config.producer,
                "project_id": self._config.project_id,
                "contract": contract,
            },
        )

    # --- evidencia --------------------------------------------------------

    def submit_evidence(self, payload: dict[str, Any]) -> Response:
        return self._request("POST", "/api/evidence/records", payload)

    def submit_outcome(self, payload: dict[str, Any]) -> Response:
        return self._request("POST", "/api/risk/execution-outcomes", payload)

    # --- assistente -------------------------------------------------------

    def chat(self, payload: dict[str, Any]) -> Response:
        return self._request("POST", "/api/chat", payload)

    # --- transporte -------------------------------------------------------

    def _headers(self, correlation_id: str | None, body: dict[str, Any] | None) -> dict[str, str]:
        headers = {
            API_KEY_HEADER: self._config.api_key,
            SDK_HEADER: f"pedrocore-python/{SDK_VERSION}",
        }
        if correlation_id:
            headers[CORRELATION_HEADER] = correlation_id
        if body is not None:
            headers[IDEMPOTENCY_HEADER] = idempotency_key(body)
        return headers

    def _request(
        self,
        method: str,
        path: str,
        body: dict[str, Any] | None = None,
        *,
        correlation_id: str | None = None,
    ) -> Response:
        url = self._config.base_url.rstrip("/") + path
        headers = self._headers(correlation_id, body)

        ultimo: Exception | None = None
        for tentativa in range(1, self._config.max_attempts + 1):
            try:
                resposta = self._transport(method, url, headers, body)
            except Exception as error:  # noqa: BLE001 - sanitizado abaixo
                ultimo = error
                if tentativa >= self._config.max_attempts:
                    raise PedroCoreError(
                        "Falha de transporte ao chamar o PedroCore "
                        f"({type(error).__name__}) após {tentativa} tentativa(s)."
                    ) from error
                self._sleep(self._config.backoff_seconds * tentativa)
                continue

            if resposta.ok:
                return resposta

            if resposta.status in _RETRYABLE_STATUS and tentativa < self._config.max_attempts:
                self._sleep(self._config.backoff_seconds * tentativa)
                continue

            raise self._error_for(resposta)

        # Inalcancavel: o laco sempre retorna ou levanta. Mantido para que uma
        # mudanca futura no laco falhe alto em vez de devolver `None`.
        raise PedroCoreError(
            f"Requisição não concluída ({type(ultimo).__name__ if ultimo else 'desconhecido'})."
        )

    @staticmethod
    def _error_for(response: Response) -> PedroCoreError:
        """Erro sem corpo bruto.

        `error_code` e `blocked_reason` sao campos que o servidor emite de
        propria vontade e ja sao sanitizados; o resto do corpo nao viaja.
        """
        codigo = response.payload.get("error_code")
        motivo = response.payload.get("blocked_reason")
        mensagem = f"PedroCore respondeu {response.status}"
        if codigo:
            mensagem += f" [{codigo}]"
        if motivo and len(str(motivo)) <= 300:
            mensagem += f": {motivo}"
        return PedroCoreError(mensagem, status=response.status, code=codigo)
